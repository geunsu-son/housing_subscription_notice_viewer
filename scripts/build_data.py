#!/usr/bin/env python3
"""Convert source Excel/CSV files into static JSON for the web viewer."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source"
OUTPUT_DIR = ROOT / "web" / "data"
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))
from schedule_meta import load_schedule_by_source_file, merge_notice_schedule, sort_notices

EXTENSIONS = (".xlsx", ".xls", ".csv")

SIDO_SUFFIXES = ("특별시", "광역시", "특별자치시", "도")


def is_valid_sido(name: str) -> bool:
    text = str(name or "").strip()
    if not text or text.startswith("매입"):
        return False
    return any(text.endswith(suffix) for suffix in SIDO_SUFFIXES)


def extract_regions(df: pd.DataFrame) -> str:
    if "시도" not in df.columns:
        return ""
    seen: set[str] = set()
    values: list[str] = []
    for value in df["시도"].dropna().tolist():
        text = str(value).strip()
        if not is_valid_sido(text) or text in seen:
            continue
        seen.add(text)
        values.append(text)
    return ", ".join(sorted(values))


def parse_filename(filename: str) -> tuple[str, str, str]:
    """Parse '{date} {company} {title}.xlsx', using the leading year token before the first dot."""
    year = filename.split(".")[0]
    parts = filename.split(" ")
    if len(parts) < 3:
        raise ValueError(f"파일명이 '날짜 주택공사 공고명' 형식이 아닙니다: {filename}")
    company = parts[1]
    title = " ".join(parts[2:])
    title = re.sub(r"\.(xlsx|xls|csv)$", "", title, flags=re.IGNORECASE)
    return year, company, title


def notice_id(filename: str) -> str:
    return re.sub(r"\s+", "-", Path(filename).stem.strip())


def to_int_money(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace('"', "", regex=False)
    )
    return cleaned.astype(np.int64)


def json_ready(value, *, as_float: bool = False, as_int: bool = False):
    if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
        return None
    if as_int:
        return int(value)
    if as_float:
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    return value


def load_table(path: Path) -> pd.DataFrame:
    name = path.name
    if name.lower().endswith(".csv"):
        return pd.read_csv(path)
    if name.lower().endswith(".xls") or name.lower().endswith(".xlsx"):
        return pd.read_excel(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {name}")


def classify_and_columns(df: pd.DataFrame) -> tuple[str, list[str], list[str]]:
    if "공급계" in df.columns:
        kind = "sh_supply"
        show_cols = [
            "공급구분",
            "시도",
            "시군구",
            "주소",
            "단지명",
            "공급구분1",
            "공급구분2",
            "공급계",
            "공급_우선",
            "공급_일반",
            "공급_예비",
        ]
        filter_cols = ["공급구분1", "공급구분2"]
    elif "매입유형" in df.columns:
        kind = "hug"
        show_cols = [
            col
            for col in ["시도", "시군구", "주택명", "주소", "주택유형", "매입유형", "안심전세포털"]
            if col in df.columns
        ]
        filter_cols = ["주택유형", "매입유형"]
    else:
        kind = "standard"
        show_cols = [
            col
            for col in ["시도", "시군구", "주택명", "주택군", "주소", "주택유형", "주택구조(방수)"]
            if col in df.columns
        ]
        if "주택구조(방수)" in df.columns:
            filter_cols = ["주택구조(방수)"]
            if "주택유형" in df.columns:
                filter_cols = ["주택유형", "주택구조(방수)"]
        elif "공급형" in df.columns:
            filter_cols = ["공급형"]
            if "주택유형" in df.columns:
                filter_cols = ["주택유형", "공급형"]
        else:
            raise ValueError("주택구조(방수) 또는 공급형이 없습니다.")

    show_cols = show_cols + [
        col for col in ["전용면적", "보증금", "월임대료", "네이버지도"] if col in df.columns
    ]
    return kind, show_cols, filter_cols


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["주소"] = df["주소"].astype(str).str.strip()
    df["보증금"] = to_int_money(df["보증금"])
    if "월임대료" in df.columns:
        df["월임대료"] = to_int_money(df["월임대료"])
    df["전용면적"] = df["전용면적"].astype(float)
    df["네이버지도"] = df["주소"].map(lambda x: f"https://map.naver.com/p/search/{x}")
    return df.sort_values(by=["시도", "시군구", "주소"])


def row_to_dict(row: pd.Series, columns: list[str]) -> dict:
    out = {}
    for col in columns:
        if col == "전용면적":
            out[col] = json_ready(row[col], as_float=True)
        elif col in ("보증금", "월임대료"):
            out[col] = json_ready(row[col], as_int=True)
        else:
            out[col] = json_ready(row[col])
    return out


def convert_file(path: Path) -> dict:
    df = load_table(path)
    df = preprocess(df)
    kind, show_cols, filter_cols = classify_and_columns(df)

    missing = [col for col in show_cols + filter_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: 필요한 컬럼이 없습니다: {missing}")

    export_cols = list(dict.fromkeys(show_cols + filter_cols))
    rows = [row_to_dict(row, export_cols) for _, row in df.iterrows()]
    year, company, title = parse_filename(path.name)
    nid = notice_id(path.name)
    regions = extract_regions(df)
    payload = {
        "id": nid,
        "kind": kind,
        "showCols": show_cols,
        "filterCols": filter_cols,
        "rows": rows,
    }
    return {
        "notice": {
            "id": nid,
            "year": year,
            "company": company,
            "title": title,
            "sourceFile": path.name,
            "dataFile": f"data/{nid}.json",
            "kind": kind,
            "rowCount": len(rows),
            "regions": regions,
        },
        "payload": payload,
    }


def main() -> int:
    if not SOURCE_DIR.is_dir():
        print(f"source 폴더가 없습니다: {SOURCE_DIR}", file=sys.stderr)
        return 1

    files = sorted(
        p
        for p in SOURCE_DIR.iterdir()
        if p.is_file() and p.name.lower().endswith(EXTENSIONS) and not p.name.startswith("~$")
    )
    if not files:
        print("source/ 에 변환할 엑셀/CSV가 없습니다.", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    notices = []
    written_ids = set()
    for path in files:
        try:
            converted = convert_file(path)
        except Exception as exc:  # noqa: BLE001 — 파일별 원인을 그대로 보여준다
            print(f"[실패] {path.name}: {exc}", file=sys.stderr)
            return 1
        notice = converted["notice"]
        out_path = OUTPUT_DIR / f"{notice['id']}.json"
        out_path.write_text(
            json.dumps(converted["payload"], ensure_ascii=False, indent=None, separators=(",", ":")),
            encoding="utf-8",
        )
        notices.append(notice)
        written_ids.add(notice["id"])
        print(
            f"[확인] {path.name} → {notice['dataFile']} "
            f"kind={notice['kind']} rows={notice['rowCount']} "
            f"{notice['year']} / {notice['company']} / {notice['title']}"
        )

    stale = [
        p
        for p in OUTPUT_DIR.glob("*.json")
        if p.name != "index.json" and p.stem not in written_ids
    ]
    for path in stale:
        path.unlink()
        print(f"[삭제] 오래된 데이터 파일 {path.name}")

    index_path = OUTPUT_DIR / "index.json"
    schedules = load_schedule_by_source_file()
    enriched_notices = [merge_notice_schedule(notice, schedules) for notice in notices]
    enriched_notices = sort_notices(enriched_notices)
    index_path.write_text(
        json.dumps({"notices": enriched_notices}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[완료] 공고 {len(notices)}개 → {index_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
