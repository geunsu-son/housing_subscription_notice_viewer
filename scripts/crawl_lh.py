#!/usr/bin/env python3
"""LH 청약플러스 매입임대 공고의 게시용 주택목록을 수집해 source/에 추가한다.

수집 경로: 목록 HTML POST → 첨부 메타데이터 JSON → 주택목록 xlsx만 다운로드.
상세 페이지 브라우저 자동화와 공고문 PDF/HWP 다운로드는 하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source"
STATE_PATH = ROOT / "scripts" / "lh-crawl-state.json"
BUILD_SCRIPT = ROOT / "scripts" / "build_data.py"

BASE = "https://apply.lh.or.kr"
LIST_URL = f"{BASE}/lhapply/apply/wt/wrtanc/selectWrtancList.do"
FILE_LIST_URL = f"{BASE}/lhapply/wt/wrtanc/wrtFileDownl.do"
FILE_URL = f"{BASE}/lhapply/lhFile.do"
LIST_PAGE = f"{LIST_URL}?mi=1026"

USER_AGENT = (
    "housing-notice-viewer/0.1 "
    "(+https://github.com/geunsu-son/housing_subscription_notice_viewer)"
)
REQUEST_GAP_SEC = 1.2
TIMEOUT_SEC = 30
LIST_PAGE_SIZE = 50
DEFAULT_LOOKBACK_DAYS = 90
HOUSING_NAME_RE = re.compile(
    r"(주택목록|주택내역|공급대상|공급주택|주택보유|공급대상주택)",
    re.I,
)

SIDO_NAMES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전남광주통합특별시",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
    "제주도",
]

HEADER_ALIASES = {
    "주소": "주소",
    "도로명주소": "주소",
    "소재지주소": "주소",
    "소재지": "주소",
    "동": "동",
    "동번호": "동",
    "호": "호",
    "전용": "전용면적",
    "전용면적": "전용면적",
    "실사용면적": "전용면적",
    "방수": "주택구조(방수)",
    "주택구조(방수)": "주택구조(방수)",
    "주택구조방수": "주택구조(방수)",
    "주택구조": "주택구조(방수)",
    "주택명": "주택명",
    "층수": "층수",
    "주택유형": "주택유형",
    "주택군": "주택군",
    "주택군명": "주택군",
    "모집단위(주택군)": "주택군",
    "모집단위주택군": "주택군",
    "시도": "시도",
    "광역지자체": "시도",
    "시군구": "시군구",
    "자치구": "시군구",
    "기초지자체": "시군구",
    "지자체": "시군구",
    "지자체명": "시군구",
    "공급형": "공급형",
    "주택형": "공급형",
    "임대보증금": "보증금",
    "기본임대보증금": "보증금",
    "보증금": "보증금",
    "월임대료": "월임대료",
    "기본월임대료": "월임대료",
    "임대료": "월임대료",
}


def norm_header(value: Any) -> str:
    text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
    text = text.replace("\n", "").replace("\r", "")
    return re.sub(r"\s+", "", text).strip()


def split_sido_sigungu(address: str, fallback_sigungu: str | None = None) -> tuple[str, str]:
    text = str(address or "").strip()
    if fallback_sigungu and str(fallback_sigungu).startswith("매입"):
        fallback_sigungu = None
    if text.startswith("제주시"):
        return "제주특별자치도", "제주시"
    if text.startswith("서귀포시"):
        return "제주특별자치도", "서귀포시"
    sido = ""
    rest = text
    for name in SIDO_NAMES:
        if text.startswith(name):
            sido = name
            rest = text[len(name) :].strip()
            break
    tokens = rest.split()
    sigungu = tokens[0] if tokens else (fallback_sigungu or "")
    if not sido:
        sido = fallback_sigungu or ""
        sigungu = tokens[0] if tokens else (fallback_sigungu or "")
    return sido, sigungu


def parse_list_html(html: str) -> tuple[int, list[dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    total = 0
    total_el = soup.select_one("p.bbs_total strong")
    if total_el:
        total = int(re.sub(r"[^\d]", "", total_el.get_text()) or "0")

    notices: list[dict[str, str]] = []
    table = soup.select_one("div.bbs_ListA table")
    if table is None:
        return total, notices

    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        link = tr.select_one("a.wrtancInfoBtn")
        if link is None or len(tds) < 8:
            continue
        title = link.get_text(" ", strip=True)
        title = re.sub(r"\s+\d+일전$", "", title).strip()
        notices.append(
            {
                "pan_id": str(link.get("data-id1") or ""),
                "ccr_cnnt_sys_ds_cd": str(link.get("data-id2") or ""),
                "upp_ais_tp_cd": str(link.get("data-id3") or ""),
                "ais_tp_cd": str(link.get("data-id4") or ""),
                "type": tds[1].get_text(strip=True),
                "title": title,
                "region": tds[3].get_text(strip=True),
                "posted_on": tds[5].get_text(strip=True),
                "closes_on": tds[6].get_text(strip=True),
                "status": tds[7].get_text(strip=True),
            }
        )
    return total, notices


def is_housing_list_file(name: str) -> bool:
    lowered = name.lower()
    if not lowered.endswith((".xlsx", ".xls")):
        return False
    return bool(HOUSING_NAME_RE.search(name))


def pick_housing_attachment(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [item for item in files if is_housing_list_file(str(item.get("cmnAhflNm") or ""))]
    if not matches:
        return None
    posted = [item for item in matches if "게시용" in str(item.get("cmnAhflNm") or "")]
    return (posted or matches)[0]


def is_addr_header(name: str) -> bool:
    return name in {"주소", "도로명주소"} or (name.endswith("주소") and "지번" not in name)


def is_area_header(name: str) -> bool:
    return name == "전용" or "전용면적" in name or name.startswith("실사용")


def find_header_row(rows: list[list[Any]]) -> int | None:
    addr_idx = None
    area_idx = None
    for index, row in enumerate(rows[:30]):
        cells = [norm_header(cell) for cell in row]
        if any(is_addr_header(cell) for cell in cells):
            addr_idx = index
        if any(is_area_header(cell) for cell in cells):
            area_idx = index
        if addr_idx is not None and area_idx is not None and abs(addr_idx - area_idx) <= 2:
            header_at = max(addr_idx, area_idx)
            nxt_index = header_at + 1
            if nxt_index < len(rows):
                nxt = [norm_header(cell) for cell in rows[nxt_index]]
                if any("보증금" in cell or "임대료" in cell for cell in nxt) and not any(
                    is_addr_header(cell) for cell in nxt
                ):
                    header_at = nxt_index
            return header_at
    return None


def fill_headers(rows: list[list[Any]], header_index: int) -> list[str]:
    width = max((len(row) for row in rows[: header_index + 1]), default=0)
    filled = [""] * width
    start = max(0, header_index - 3)
    for row in rows[start : header_index + 1]:
        for col, value in enumerate(row):
            if col >= width:
                continue
            text = norm_header(value)
            if text:
                filled[col] = text
    return filled


def map_header(name: str) -> str | None:
    if name in HEADER_ALIASES:
        return HEADER_ALIASES[name]
    if "전용" in name and "면적" in name:
        return "전용면적"
    if "보증금" in name and "상한" not in name and "최대" not in name:
        return "보증금"
    if ("월임대료" in name or name.endswith("임대료")) and "하한" not in name and "최대" not in name:
        return "월임대료"
    return None


def first_mapped_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, raw in enumerate(headers):
        mapped = map_header(raw)
        if mapped and mapped not in mapping:
            mapping[mapped] = index
    return mapping


def to_number(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return value
    text = re.sub(r"\s+", "", str(value).replace(",", "").replace("원", ""))
    if not text or text.lower() == "nan":
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return None


def normalize_housing_table(rows: list[list[Any]]) -> pd.DataFrame:
    header_index = find_header_row(rows)
    if header_index is None:
        raise ValueError("주소·전용면적 헤더를 찾지 못했습니다.")
    headers = fill_headers(rows, header_index)
    mapping = first_mapped_columns(headers)
    if "주소" not in mapping or "전용면적" not in mapping:
        raise ValueError(f"필수 컬럼이 없습니다: {headers}")
    if "보증금" not in mapping:
        raise ValueError(f"보증금 컬럼이 없습니다: {headers}")

    records: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        address_raw = row[mapping["주소"]] if mapping["주소"] < len(row) else None
        address = "" if address_raw is None or pd.isna(address_raw) else str(address_raw).strip()
        if not address or address in {"합계", "주소"}:
            continue
        area = to_number(row[mapping["전용면적"]] if mapping["전용면적"] < len(row) else None)
        deposit = to_number(row[mapping["보증금"]] if mapping["보증금"] < len(row) else None)
        if area is None or deposit is None:
            continue

        fallback = None
        if "시군구" in mapping and mapping["시군구"] < len(row):
            raw = row[mapping["시군구"]]
            fallback = None if raw is None or pd.isna(raw) else str(raw).strip()
        sido, sigungu = split_sido_sigungu(address, fallback)
        if "시도" in mapping and mapping["시도"] < len(row):
            raw = row[mapping["시도"]]
            if raw is not None and not pd.isna(raw) and str(raw).strip():
                sido = str(raw).strip()

        item: dict[str, Any] = {
            "시도": sido,
            "시군구": sigungu,
            "주소": address,
            "전용면적": float(area),
            "보증금": int(deposit),
        }
        optional = {
            "주택명": "주택명",
            "주택군": "주택군",
            "주택유형": "주택유형",
            "주택구조(방수)": "주택구조(방수)",
            "공급형": "공급형",
            "월임대료": "월임대료",
        }
        for dest, src in optional.items():
            if src not in mapping or mapping[src] >= len(row):
                continue
            value = row[mapping[src]]
            if dest == "월임대료":
                number = to_number(value)
                if number is not None:
                    item[dest] = int(number)
            elif dest == "주택구조(방수)":
                number = to_number(value)
                item[dest] = int(number) if number is not None else (None if value is None else str(value).strip())
            elif value is not None and not pd.isna(value) and str(value).strip():
                item[dest] = str(value).strip()
        records.append(item)

    if not records:
        raise ValueError("헤더는 찾았지만 주택 행이 없습니다.")
    frame = pd.DataFrame.from_records(records)
    if "월임대료" in frame.columns and frame["월임대료"].isna().any():
        frame = frame.drop(columns=["월임대료"])
    if "주택구조(방수)" not in frame.columns and "공급형" not in frame.columns:
        frame["주택구조(방수)"] = None
    return frame


def normalize_housing_excel(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, header=None, dtype=object, sheet_name=0)
    rows = frame.where(pd.notna(frame), None).values.tolist()
    return normalize_housing_table(rows)


def notice_filename(posted_on: str, title: str) -> str:
    date_token = posted_on.replace("-", ".")
    cleaned = title.replace("[", " ").replace("]", " ")
    cleaned = re.sub(r"[\\/:*?\"<>|]", " ", cleaned)
    cleaned = re.sub(r"(?:정정공고\s+)+", "정정공고 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if len(cleaned) > 80:
        cleaned = cleaned[:80].rstrip()
    return f"{date_token} LH {cleaned}.xlsx"


def write_source_excel(path: Path, frame: pd.DataFrame) -> None:
    workbook = Workbook()
    sheet = workbook.active
    columns = list(frame.columns)
    sheet.append(columns)
    for row in frame.itertuples(index=False, name=None):
        sheet.append(list(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"notices": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class LhClient:
    def __init__(self, gap_sec: float = REQUEST_GAP_SEC) -> None:
        self.gap_sec = gap_sec
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "ko-KR,ko;q=0.9",
            }
        )

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < self.gap_sec:
            time.sleep(self.gap_sec - elapsed)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", TIMEOUT_SEC)
        last_error: Exception | None = None
        for attempt in range(3):
            self._wait()
            try:
                response = self.session.request(method, url, **kwargs)
                self._last = time.monotonic()
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(2 ** attempt)
                last_error = RuntimeError(f"HTTP {response.status_code} {url}")
                continue
            if response.status_code in {401, 403}:
                raise RuntimeError(f"차단 또는 권한 오류 HTTP {response.status_code}: {url}")
            response.raise_for_status()
            return response
        raise RuntimeError(f"요청 실패: {url} ({last_error})")

    def warmup(self) -> None:
        self.request("GET", LIST_PAGE)

    def fetch_list_page(
        self,
        *,
        page: int,
        start: date,
        end: date,
        status: str,
    ) -> str:
        payload = {
            "mi": "1026",
            "currPage": str(page),
            "listCo": str(LIST_PAGE_SIZE),
            "prevListCo": str(LIST_PAGE_SIZE),
            "panSs": status,
            "uppAisTpCd": "13",
            "aisTpCd": "26",
            "srchUppAisTpCd": "13",
            "srchAisTpCd": "26",
            "srchY": "Y" if page == 1 else "N",
            "startDt": start.isoformat(),
            "endDt": end.isoformat(),
            "panStDt": start.strftime("%Y%m%d"),
            "panEdDt": end.strftime("%Y%m%d"),
            "cnpCd": "",
            "xssChk": "N",
        }
        response = self.request(
            "POST",
            LIST_URL,
            data=payload,
            headers={"Referer": LIST_PAGE},
        )
        return response.text

    def fetch_attachments(self, notice: dict[str, str]) -> list[dict[str, Any]]:
        payload = {
            "uppAisTpCd1": notice["upp_ais_tp_cd"],
            "aisTpCd1": notice["ais_tp_cd"],
            "ccrCnntSysDsCd1": notice["ccr_cnnt_sys_ds_cd"],
            "lsSst1": "",
            "panId1": notice["pan_id"],
        }
        response = self.request(
            "POST",
            FILE_LIST_URL,
            data=payload,
            headers={
                "Referer": LIST_PAGE,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/plain, */*",
            },
        )
        response.encoding = "utf-8"
        data = json.loads(response.content.decode("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            files = data.get("list") or data.get("files") or []
            return files if isinstance(files, list) else []
        return []

    def download_file(self, file_id: Any, dest: Path) -> None:
        response = self.request(
            "GET",
            FILE_URL,
            params={"fileid": str(file_id)},
            headers={"Referer": LIST_PAGE},
        )
        dest.write_bytes(response.content)


def collect_notices(client: LhClient, start: date, end: date, status: str) -> list[dict[str, str]]:
    html = client.fetch_list_page(page=1, start=start, end=end, status=status)
    total, notices = parse_list_html(html)
    if not notices and total:
        raise RuntimeError("목록 HTML에서 공고 행을 파싱하지 못했습니다.")
    pages = max(1, (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE) if total else 1
    for page in range(2, pages + 1):
        html = client.fetch_list_page(page=page, start=start, end=end, status=status)
        _, extra = parse_list_html(html)
        notices.extend(extra)
    unique: dict[str, dict[str, str]] = {}
    for notice in notices:
        if notice["pan_id"]:
            unique[notice["pan_id"]] = notice
    return list(unique.values())


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LH 매입임대 주택목록 수집")
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--status", default="공고중", help="공고 상태. 비우면 사이트 기본값을 씀")
    parser.add_argument("--max-new", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)

    end = date.today()
    start = end - timedelta(days=args.lookback_days)
    state = load_state()
    seen = state.setdefault("notices", {})

    client = LhClient()
    print(f"[시작] LH 매입임대 목록 {start.isoformat()} ~ {end.isoformat()} status={args.status!r}")
    client.warmup()
    notices = collect_notices(client, start, end, args.status)
    print(f"[목록] {len(notices)}건")

    added = 0
    skipped = 0
    failed = 0
    for notice in notices:
        pan_id = notice["pan_id"]
        if pan_id in seen:
            skipped += 1
            continue
        if added >= args.max_new:
            print(f"[중단] --max-new {args.max_new} 도달")
            break
        try:
            files = client.fetch_attachments(notice)
            attachment = pick_housing_attachment(files)
            if attachment is None:
                names = [str(item.get("cmnAhflNm") or "") for item in files]
                print(f"[건너뜀] 주택목록 없음 {notice['title'][:60]} files={names[:5]}")
                seen[pan_id] = {
                    "title": notice["title"],
                    "posted_on": notice["posted_on"],
                    "status": "no-housing-list",
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
                skipped += 1
                continue
            if args.dry_run:
                print(
                    f"[dry-run] {notice['posted_on']} {notice['title'][:60]} "
                    f"→ {attachment.get('cmnAhflNm')}"
                )
                added += 1
                continue

            tmp_path = Path("/tmp") / f"lh-{pan_id}.xlsx"
            if not tmp_path.is_file() or tmp_path.stat().st_size < 100:
                client.download_file(attachment.get("cmnAhflSn"), tmp_path)
            if tmp_path.stat().st_size < 100:
                raise ValueError("다운로드한 파일이 비어 있습니다.")
            frame = normalize_housing_excel(tmp_path)
            filename = notice_filename(notice["posted_on"], notice["title"])
            dest = SOURCE_DIR / filename
            write_source_excel(dest, frame)
            seen[pan_id] = {
                "title": notice["title"],
                "posted_on": notice["posted_on"],
                "source_file": filename,
                "row_count": int(len(frame)),
                "detail_url": (
                    f"{LIST_URL.replace('selectWrtancList.do', 'selectWrtancInfo.do')}"
                    f"?panId={pan_id}&ccrCnntSysDsCd={notice['ccr_cnnt_sys_ds_cd']}"
                    f"&uppAisTpCd={notice['upp_ais_tp_cd']}&aisTpCd={notice['ais_tp_cd']}&mi=1026"
                ),
                "source_url": LIST_PAGE,
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            }
            added += 1
            print(f"[추가] {filename} rows={len(frame)}")
        except Exception as exc:  # noqa: BLE001 — 공고별로 원인을 남기고 다음 공고로 진행
            failed += 1
            print(f"[실패] {notice['title'][:60]}: {exc}", file=sys.stderr)
            if "차단" in str(exc):
                save_state(state)
                return 1

    if not args.dry_run:
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_state(state)

    print(f"[요약] added={added} skipped={skipped} failed={failed}")
    if args.dry_run or args.skip_build or added == 0:
        return 0 if failed == 0 or added > 0 else 1

    import subprocess

    print("[변환] scripts/build_data.py")
    built = subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=False)
    if built.returncode != 0:
        return built.returncode
    return 0 if added > 0 or failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
