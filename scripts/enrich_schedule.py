#!/usr/bin/env python3
"""Backfill LH/SH crawl state with schedule metadata."""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from crawl_lh import LhClient, notice_filename, parse_list_html  # noqa: E402
from schedule_meta import parse_date_token, parse_sh_schedule_text  # noqa: E402

LH_STATE_PATH = ROOT / "scripts" / "lh-crawl-state.json"
SH_STATE_PATH = ROOT / "scripts" / "sh-crawl-state.json"
USER_AGENT = (
    "housing-notice-viewer/0.1 "
    "(+https://github.com/geunsu-son/housing_subscription_notice_viewer)"
)


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"notices": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def enrich_lh_state(state: dict) -> int:
    client = LhClient()
    client.warmup()
    end = date.today()
    start = end - timedelta(days=400)
    updated = 0
    page = 1
    seen_filenames: set[str] = set()
    by_source_file: dict[str, dict[str, str]] = {}

    while True:
        html = client.fetch_list_page(page=page, start=start, end=end, status="")
        _, notices = parse_list_html(html)
        if not notices:
            break
        for notice in notices:
            filename = notice_filename(notice["posted_on"], notice["title"])
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)
            pan_id = notice["pan_id"]
            entry = state.setdefault("notices", {}).setdefault(pan_id, {})
            entry["posted_on"] = notice["posted_on"]
            entry["closes_on"] = notice["closes_on"]
            entry["status"] = notice["status"]
            entry["title"] = notice["title"]
            if entry.get("source_file"):
                updated += 1
            by_source_file[filename] = {
                "posted_on": notice["posted_on"],
                "closes_on": notice["closes_on"],
                "status": notice["status"],
            }
        page += 1
        if page > 20:
            break
        time.sleep(1.2)

    state["schedules_by_source_file"] = by_source_file
    return updated


def enrich_sh_state(state: dict) -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    updated = 0

    for entry in state.get("notices", {}).values():
        detail_url = entry.get("detail_url")
        if not detail_url:
            continue
        try:
            response = session.get(detail_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            continue
        schedule = parse_sh_schedule_text(response.text)
        if schedule["postedOn"]:
            entry["posted_on_announcement"] = schedule["postedOn"]
        if schedule["applyStart"]:
            entry["apply_start"] = schedule["applyStart"]
        if schedule["applyEnd"]:
            entry["apply_end"] = schedule["applyEnd"]
        if schedule["applyStart"] or schedule["applyEnd"]:
            entry["recruit_status"] = "진행중"
            updated += 1
        time.sleep(1.0)

    return updated


def main() -> int:
    lh_state = load_state(LH_STATE_PATH)
    sh_state = load_state(SH_STATE_PATH)

    print("[LH] 목록에서 마감일·상태 보강")
    lh_updated = enrich_lh_state(lh_state)
    save_state(LH_STATE_PATH, lh_state)
    print(f"[LH] source_file이 있는 공고 {lh_updated}건 보강")

    print("[SH] 상세 페이지에서 신청기간 보강")
    sh_updated = enrich_sh_state(sh_state)
    save_state(SH_STATE_PATH, sh_state)
    print(f"[SH] 신청기간 {sh_updated}건 보강")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
