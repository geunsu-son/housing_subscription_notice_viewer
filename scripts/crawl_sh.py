#!/usr/bin/env python3
"""SH 주택임대 게시판에서 매입임대 주택목록 엑셀을 수집해 source/에 추가한다.

수집 경로: 목록 HTML POST → 상세 HTML의 downList → xlsx/xls 또는 웹하드 링크 txt.
공고문 PDF/HWP와 도면·사진 파일은 받지 않는다.
최근 공고는 주택목록을 PDF만 올리는 경우가 있어, 엑셀이 없으면 건너뛴다.
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
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawl_lh import (  # noqa: E402
    BUILD_SCRIPT,
    SOURCE_DIR,
    normalize_housing_excel,
    write_source_excel,
)

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "scripts" / "sh-crawl-state.json"

BASE = "https://www.i-sh.co.kr"
BOARD_PATH = "/main/lay2/program/S1T297C4476/www/brd/m_247"
LIST_URL = f"{BASE}{BOARD_PATH}/list.do"
VIEW_URL = f"{BASE}{BOARD_PATH}/view.do"
FILE_URL = f"{BASE}/main/com/file/innoFD.do"
LIST_PAGE = f"{LIST_URL}?multi_itm_seq=2"
WEBHARD_HOST = "webhard.i-sh.co.kr"

USER_AGENT = (
    "housing-notice-viewer/0.1 "
    "(+https://github.com/geunsu-son/housing_subscription_notice_viewer)"
)
REQUEST_GAP_SEC = 1.2
TIMEOUT_SEC = 30
PAGE_SIZE = 10
DEFAULT_LOOKBACK_DAYS = 90
BRD_ID = "GS0401"

HOUSING_NAME_RE = re.compile(
    r"(주택목록|주택내역|공급대상|공급주택|주택보유|공개용|주택안내)",
    re.I,
)
SKIP_FILE_RE = re.compile(r"(도면|사진|팸플릿|위임장|공고문|동의서|신청서|평면도)")
SKIP_TITLE_RE = re.compile(
    r"(당첨자|서류심사대상자|경쟁률|동호배정|계약안내|사전방문|최종접수현황|청약접수 결과)"
)
KEEP_TITLE_RE = re.compile(r"(매입임대|미리내집|장기미임대|장기매임대)")
WEBHARD_RE = re.compile(r"https?://webhard\.i-sh\.co\.kr[^\s<>\"']+", re.I)


def notice_filename(posted_on: str, title: str) -> str:
    date_token = posted_on.replace("-", ".")
    cleaned = title.replace("[", " ").replace("]", " ")
    cleaned = re.sub(r"[\\/:*?\"<>|]", " ", cleaned)
    cleaned = re.sub(r"^NEW\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if len(cleaned) > 80:
        cleaned = cleaned[:80].rstrip()
    return f"{date_token} SH {cleaned}.xlsx"


def parse_list_html(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return []
    notices: list[dict[str, str]] = []
    for tr in tables[1].select("tr"):
        link = None
        for anchor in tr.find_all("a"):
            onclick = anchor.get("onclick") or ""
            if "getDetailView" in onclick:
                link = anchor
                break
        if link is None:
            continue
        match = re.search(r"getDetailView\('(\d+)'\)", link.get("onclick") or "")
        if match is None:
            continue
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        title = re.sub(r"^NEW\s+", "", link.get_text(" ", strip=True)).strip()
        notices.append(
            {
                "seq": match.group(1),
                "title": title,
                "dept": tds[2] if len(tds) > 2 else "",
                "posted_on": tds[3] if len(tds) > 3 else "",
            }
        )
    return notices


def parse_down_list(html: str) -> list[dict[str, Any]]:
    marker = "initParam.downList"
    start = html.find(marker)
    if start < 0:
        return []
    eq = html.find("=", start)
    if eq < 0:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html[eq + 1 :].lstrip())
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def is_housing_excel(name: str) -> bool:
    lowered = name.lower()
    if not lowered.endswith((".xlsx", ".xls")):
        return False
    if SKIP_FILE_RE.search(name) and "주택목록" not in name:
        return False
    return bool(HOUSING_NAME_RE.search(name))


def is_excel_link_note(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(".txt") and "엑셀" in name and "링크" in name


def pick_housing_attachment(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    excel = [item for item in files if is_housing_excel(str(item.get("oriFileNm") or ""))]
    if excel:
        posted = [item for item in excel if "공개용" in str(item.get("oriFileNm") or "")]
        return (posted or excel)[0]
    notes = [item for item in files if is_excel_link_note(str(item.get("oriFileNm") or ""))]
    return notes[0] if notes else None


def parse_webhard_url(text: str) -> str | None:
    match = WEBHARD_RE.search(text or "")
    return match.group(0).rstrip(").,;") if match else None


def is_recruit_housing_notice(title: str) -> bool:
    if SKIP_TITLE_RE.search(title):
        return False
    if "장기전세" in title and "매입" not in title and "미리내집" not in title:
        return False
    return bool(KEEP_TITLE_RE.search(title) and "모집" in title)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"notices": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ShClient:
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

    def _list_payload(self, page: int, extra: dict[str, str]) -> dict[str, str]:
        payload = {
            "page": str(page),
            "seq": "",
            "itm_seq_1": "0",
            "multi_itm_seq": "2",
            "multi_itm_seqsStr": "",
            "isRecrnoti": "",
            "notType1": "0",
            "splyTy": "",
            "recrnotiState": "",
            "srchFr": "",
            "srchTo": "",
            "recSrchFr": "",
            "recSrchTo": "",
            "srchTp": "0",
            "srchWord": "",
        }
        payload.update(extra)
        return payload

    def fetch_list_page(self, page: int, extra: dict[str, str]) -> str:
        response = self.request(
            "POST",
            LIST_URL,
            data=self._list_payload(page, extra),
            headers={"Referer": LIST_PAGE},
        )
        return response.text

    def fetch_detail(self, seq: str) -> str:
        response = self.request(
            "POST",
            VIEW_URL,
            data={"page": "1", "seq": seq, "multi_itm_seq": "2"},
            headers={"Referer": LIST_PAGE},
        )
        return response.text

    def download_attachment(self, seq: str, file_seq: Any, dest: Path) -> None:
        response = self.request(
            "GET",
            FILE_URL,
            params={"brdId": BRD_ID, "seq": seq, "fileTp": "A", "fileSeq": str(file_seq)},
            headers={"Referer": VIEW_URL},
        )
        dest.write_bytes(response.content)

    def download_webhard(self, page_url: str, dest: Path) -> None:
        parsed = urlparse(page_url)
        if parsed.hostname != WEBHARD_HOST:
            raise ValueError(f"허용하지 않는 웹하드 호스트: {parsed.hostname}")
        self.request("GET", page_url, headers={"Referer": LIST_PAGE})
        lid = ""
        match = re.search(r"[?&]lid=([0-9a-fA-F]+)", page_url)
        if match:
            lid = match.group(1)
        if not lid:
            raise ValueError("웹하드 lid가 없습니다.")
        response = self.request(
            "POST",
            f"{parsed.scheme}://{parsed.hostname}{parsed.path}",
            data={"lid": lid, "act": "down", "linkpwd": ""},
            headers={"Referer": page_url},
        )
        dest.write_bytes(response.content)


def paginate_notices(client: ShClient, extra: dict[str, str], max_pages: int = 20) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for page in range(1, max_pages + 1):
        html = client.fetch_list_page(page, extra)
        items = parse_list_html(html)
        new_items = [item for item in items if item["seq"] and item["seq"] not in found]
        if not new_items:
            break
        for item in new_items:
            found[item["seq"]] = item
        if len(items) < PAGE_SIZE:
            break
    return list(found.values())


def collect_notices(client: ShClient, start: date, end: date) -> list[dict[str, str]]:
    start_s = start.isoformat()
    end_s = end.isoformat()
    buckets = [
        paginate_notices(
            client,
            {
                "itm_seq_1": "1",
                "isRecrnoti": "Y",
                "recrnotiState": "now",
            },
        ),
        paginate_notices(
            client,
            {
                "srchTp": "0",
                "srchWord": "매입임대",
                "srchFr": start_s,
                "srchTo": end_s,
            },
        ),
        paginate_notices(
            client,
            {
                "srchTp": "0",
                "srchWord": "미리내집",
                "srchFr": start_s,
                "srchTo": end_s,
            },
        ),
    ]
    unique: dict[str, dict[str, str]] = {}
    for bucket in buckets:
        for notice in bucket:
            unique[notice["seq"]] = notice
    return [item for item in unique.values() if is_recruit_housing_notice(item["title"])]


def finish_seoul(frame):
    if "시도" in frame.columns:
        empty = frame["시도"].isna() | (frame["시도"].astype(str).str.strip() == "")
        frame.loc[empty, "시도"] = "서울특별시"
    return frame


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SH 매입임대 주택목록 수집")
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--max-new", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)

    end = date.today()
    start = end - timedelta(days=args.lookback_days)
    state = load_state()
    seen = state.setdefault("notices", {})

    client = ShClient()
    print(f"[시작] SH 매입임대 목록 {start.isoformat()} ~ {end.isoformat()}")
    client.warmup()
    notices = collect_notices(client, start, end)
    print(f"[목록] {len(notices)}건")

    added = 0
    skipped = 0
    failed = 0
    for notice in notices:
        seq = notice["seq"]
        if seq in seen:
            skipped += 1
            continue
        if added >= args.max_new:
            print(f"[중단] --max-new {args.max_new} 도달")
            break
        try:
            html = client.fetch_detail(seq)
            files = parse_down_list(html)
            attachment = pick_housing_attachment(files)
            if attachment is None:
                names = [str(item.get("oriFileNm") or "") for item in files]
                print(f"[건너뜀] 주택목록 엑셀 없음 {notice['title'][:60]} files={names[:5]}")
                seen[seq] = {
                    "title": notice["title"],
                    "posted_on": notice["posted_on"],
                    "status": "no-housing-excel",
                    "files": names[:8],
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
                skipped += 1
                continue
            filename_orig = str(attachment.get("oriFileNm") or "")
            if args.dry_run:
                print(f"[dry-run] {notice['posted_on']} {notice['title'][:60]} → {filename_orig}")
                added += 1
                continue

            tmp_path = Path("/tmp") / f"sh-{seq}.bin"
            excel_path = Path("/tmp") / f"sh-{seq}.xlsx"
            if not excel_path.is_file() or excel_path.stat().st_size < 100:
                client.download_attachment(seq, attachment.get("fileSeq"), tmp_path)
                if is_excel_link_note(filename_orig):
                    link = parse_webhard_url(tmp_path.read_text(encoding="utf-8", errors="replace"))
                    if not link:
                        raise ValueError("엑셀 링크 txt에서 웹하드 URL을 찾지 못했습니다.")
                    client.download_webhard(link, excel_path)
                else:
                    tmp_path.replace(excel_path)
            if excel_path.stat().st_size < 100:
                raise ValueError("다운로드한 파일이 비어 있습니다.")
            magic = excel_path.read_bytes()[:8]
            if magic[:2] != b"PK" and magic[:4] != b"\xd0\xcf\x11\xe0":
                raise ValueError("엑셀이 아닌 파일을 받았습니다.")
            frame = normalize_housing_excel(excel_path)
            frame = finish_seoul(frame)
            filename = notice_filename(notice["posted_on"], notice["title"])
            dest = SOURCE_DIR / filename
            write_source_excel(dest, frame)
            seen[seq] = {
                "title": notice["title"],
                "posted_on": notice["posted_on"],
                "source_file": filename,
                "row_count": int(len(frame)),
                "detail_url": f"{VIEW_URL}?multi_itm_seq=2&seq={seq}",
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
