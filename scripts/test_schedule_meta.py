#!/usr/bin/env python3
"""Unit tests for notice schedule metadata helpers."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schedule_meta import (
    merge_notice_schedule,
    parse_date_token,
    parse_sh_schedule_text,
    posted_on_from_filename,
    schedule_status,
    sort_notices,
)


class ScheduleMetaTests(unittest.TestCase):
    def test_parse_date_token(self) -> None:
        self.assertEqual(parse_date_token("2026.09.07"), "2026-09-07")
        self.assertEqual(parse_date_token("2026-09-07"), "2026-09-07")

    def test_posted_on_from_filename(self) -> None:
        self.assertEqual(
            posted_on_from_filename("2026.09.07 LH 경기남부 용인시 청년 매입임대주택.xlsx"),
            "2026-09-07",
        )

    def test_parse_sh_schedule_text(self) -> None:
        text = (
            "모집공고일 : 2026. 8. 28.(금) "
            "청약신청 : 2026. 9. 28.(월) 10:00 ~ 2026. 9. 30.(수) 17:00"
        )
        schedule = parse_sh_schedule_text(text)
        self.assertEqual(schedule["postedOn"], "2026-08-28")
        self.assertEqual(schedule["applyStart"], "2026-09-28")
        self.assertEqual(schedule["applyEnd"], "2026-09-30")

    def test_schedule_status(self) -> None:
        ref = date(2026, 9, 9)
        self.assertEqual(
            schedule_status(
                ref,
                posted_on="2026-09-07",
                apply_start="2026-09-10",
                apply_end="2026-09-21",
            ),
            "신청전",
        )
        self.assertEqual(
            schedule_status(
                ref,
                posted_on="2026-09-07",
                apply_start="2026-09-08",
                apply_end="2026-09-21",
            ),
            "진행중",
        )
        self.assertEqual(
            schedule_status(
                ref,
                posted_on="2026-08-01",
                apply_start="2026-08-01",
                apply_end="2026-08-20",
            ),
            "마감",
        )
        self.assertEqual(
            schedule_status(ref, posted_on="2026-09-07", notice_status="공고중"),
            "진행중",
        )

    def test_sort_notices(self) -> None:
        notices = [
            {"id": "a", "year": "2025", "postedOn": "2025-07-01", "sourceFile": "2025.07.01 LH a"},
            {"id": "b", "year": "2026", "postedOn": "2026-09-07", "sourceFile": "2026.09.07 LH b"},
            {"id": "c", "year": "2026", "postedOn": "2026-08-01", "sourceFile": "2026.08.01 LH c"},
        ]
        sorted_notices = sort_notices(notices)
        self.assertEqual([item["id"] for item in sorted_notices], ["b", "c", "a"])

    def test_merge_notice_schedule(self) -> None:
        notice = {
            "id": "sample",
            "year": "2026",
            "company": "LH",
            "title": "용인시 청년 매입임대",
            "sourceFile": "2026.09.07 LH 용인시.xlsx",
        }
        schedules = {
            "2026.09.07 LH 용인시.xlsx": {
                "postedOn": "2026-09-07",
                "applyStart": "2026-09-07",
                "applyEnd": "2026-09-21",
                "noticeStatus": "공고중",
            }
        }
        merged = merge_notice_schedule(notice, schedules)
        self.assertEqual(merged["postedOn"], "2026-09-07")
        self.assertEqual(merged["applyEnd"], "2026-09-21")
        self.assertEqual(merged["scheduleStatus"], "진행중")


if __name__ == "__main__":
    unittest.main()
