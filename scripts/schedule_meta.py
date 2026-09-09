"""Shared helpers for notice schedule metadata."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LH_STATE_PATH = ROOT / "scripts" / "lh-crawl-state.json"
SH_STATE_PATH = ROOT / "scripts" / "sh-crawl-state.json"

DATE_TOKEN_RE = re.compile(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")
TITLE_DATE_RE = re.compile(r"\((\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\)")
SH_APPLY_RE = re.compile(
    r"청약신청\s*:\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2}).*?~\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})",
    re.S,
)
SH_POSTED_RE = re.compile(r"모집공고일\s*:\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")


def iso_date(year: str | int, month: str | int, day: str | int) -> str:
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def parse_date_token(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    match = DATE_TOKEN_RE.match(text.replace("/", "."))
    if not match:
        return None
    return iso_date(*match.groups())


def parse_date_obj(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    token = parse_date_token(value)
    if not token:
        return None
    return datetime.strptime(token, "%Y-%m-%d").date()


def posted_on_from_filename(filename: str) -> str | None:
    token = filename.split(" ", 1)[0] if filename else ""
    return parse_date_token(token)


def parse_title_announcement_date(title: str) -> str | None:
    matches = TITLE_DATE_RE.findall(title)
    if not matches:
        return None
    year, month, day = matches[-1]
    return iso_date(year, month, day)


def parse_sh_schedule_text(text: str) -> dict[str, str | None]:
    posted_on = None
    apply_start = None
    apply_end = None

    posted_match = SH_POSTED_RE.search(text)
    if posted_match:
        posted_on = iso_date(*posted_match.groups())

    apply_match = SH_APPLY_RE.search(text)
    if apply_match:
        apply_start = iso_date(apply_match.group(1), apply_match.group(2), apply_match.group(3))
        apply_end = iso_date(apply_match.group(4), apply_match.group(5), apply_match.group(6))

    return {
        "postedOn": posted_on,
        "applyStart": apply_start,
        "applyEnd": apply_end,
    }


def schedule_status(
    reference: date,
    *,
    posted_on: str | None = None,
    apply_start: str | None = None,
    apply_end: str | None = None,
    notice_status: str | None = None,
) -> str:
    start = parse_date_obj(apply_start or posted_on)
    end = parse_date_obj(apply_end)

    if notice_status:
        normalized = notice_status.strip()
        if "마감" in normalized or normalized in {"접수마감", "공고마감", "모집마감"}:
            return "마감"
        if normalized == "공고중" or normalized == "접수중":
            if start and reference < start:
                return "신청전"
            if end and reference > end:
                return "마감"
            return "진행중"

    if start and reference < start:
        return "신청전"
    if end and reference > end:
        return "마감"
    if start or end:
        return "진행중"

    posted = parse_date_obj(posted_on)
    if posted and (reference - posted).days > 90:
        return "마감"
    if posted and reference < posted:
        return "신청전"
    return "진행중"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    notices = payload.get("notices")
    return notices if isinstance(notices, dict) else {}


def _lh_schedule_entry(entry: dict[str, Any]) -> dict[str, Any]:
    posted_on = parse_date_token(entry.get("posted_on"))
    apply_end = parse_date_token(entry.get("closes_on"))
    notice_status = entry.get("notice_status") or entry.get("status")
    if notice_status in {"no-housing-list", "pdf-parse-failed"}:
        notice_status = None
    return {
        "postedOn": posted_on,
        "applyStart": posted_on,
        "applyEnd": apply_end,
        "noticeStatus": notice_status,
        "detailUrl": entry.get("detail_url"),
    }


def load_schedule_by_source_file() -> dict[str, dict[str, Any]]:
    schedules: dict[str, dict[str, Any]] = {}

    lh_payload = {}
    if LH_STATE_PATH.is_file():
        lh_payload = json.loads(LH_STATE_PATH.read_text(encoding="utf-8"))
    for source_file, entry in (lh_payload.get("schedules_by_source_file") or {}).items():
        if isinstance(entry, dict):
            schedules[str(source_file)] = _lh_schedule_entry(entry)

    for entry in (lh_payload.get("notices") or {}).values():
        source_file = entry.get("source_file")
        if not source_file:
            continue
        schedules[str(source_file)] = _lh_schedule_entry(entry)

    for entry in _load_state(SH_STATE_PATH).values():
        source_file = entry.get("source_file")
        if not source_file:
            continue
        posted_on = parse_date_token(entry.get("posted_on"))
        apply_start = parse_date_token(entry.get("apply_start"))
        apply_end = parse_date_token(entry.get("apply_end"))
        schedules[str(source_file)] = {
            "postedOn": parse_date_token(entry.get("posted_on_announcement")) or posted_on,
            "applyStart": apply_start or posted_on,
            "applyEnd": apply_end,
            "noticeStatus": entry.get("recruit_status"),
            "detailUrl": entry.get("detail_url"),
        }

    return schedules


def merge_notice_schedule(notice: dict[str, Any], schedules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_file = str(notice.get("sourceFile") or "")
    meta = schedules.get(source_file, {})
    posted_on = meta.get("postedOn") or posted_on_from_filename(source_file)
    apply_start = meta.get("applyStart") or posted_on
    apply_end = meta.get("applyEnd")
    notice_status = meta.get("noticeStatus")

    if notice.get("company") == "SH" and not apply_end:
        title_date = parse_title_announcement_date(str(notice.get("title") or source_file))
        if title_date:
            posted_on = posted_on or title_date
            apply_start = apply_start or title_date

    enriched = dict(notice)
    if posted_on:
        enriched["postedOn"] = posted_on
    if apply_start:
        enriched["applyStart"] = apply_start
    if apply_end:
        enriched["applyEnd"] = apply_end
    if notice_status:
        enriched["noticeStatus"] = notice_status
    if meta.get("detailUrl"):
        enriched["detailUrl"] = meta["detailUrl"]

    enriched["scheduleStatus"] = schedule_status(
        date.today(),
        posted_on=posted_on,
        apply_start=apply_start,
        apply_end=apply_end,
        notice_status=notice_status,
    )
    return enriched


def sort_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
        year = str(item.get("year") or "")
        posted = str(item.get("postedOn") or posted_on_from_filename(str(item.get("sourceFile") or "")) or "")
        return (year, posted, str(item.get("id") or ""))

    return sorted(notices, key=sort_key, reverse=True)
