#!/usr/bin/env python3
"""Unit tests for SH housing-list parsing helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from openpyxl import Workbook

from crawl_lh import normalize_housing_excel
from crawl_sh import (
    is_excel_link_note,
    is_housing_excel,
    is_recruit_housing_notice,
    notice_filename,
    parse_down_list,
    parse_list_html,
    parse_webhard_url,
    pick_housing_attachment,
)

LIST_HTML = """
<table></table>
<table>
<tbody>
<tr>
<td>10</td>
<td class="title">
<a href="#" onclick="getDetailView('306214');return false;">
2026년 1차 청년 매입임대주택 입주자 모집공고(2026. 6. 26.)
</a>
</td>
<td>매입주택공급부</td>
<td>2026-06-26</td>
<td>100</td>
</tr>
<tr>
<td>9</td>
<td>
<a href="#" onclick="getDetailView('309497');return false;">
[당첨자발표] 2026년 다자녀 매입임대주택 입주자모집공고
</a>
</td>
<td>매입주택공급부</td>
<td>2026-09-02</td>
<td>10</td>
</tr>
</tbody>
</table>
"""

DOWN_HTML = """
<script>
initParam = {"downList":""};
initParam.downList = [{"brdId":"GS0401","seq":"296598","fileSeq":"2","fileSize":"14755","oriFileNm":"2_ [주택목록] 2025년 하반기 청년 매입임대주택 우선공급 주택목록(홈페이지 공개용).xlsx","fileTp":"A"},{"brdId":"GS0401","seq":"296598","fileSeq":"1","oriFileNm":"1_ [공고문] 모집공고문.pdf","fileTp":"A"},{"brdId":"GS0401","seq":"296598","fileSeq":"6","oriFileNm":"[첨부] 도면 및 사진(링크).xlsx","fileTp":"A"}];
</script>
"""


class ListParseTests(unittest.TestCase):
    def test_parse_list_html(self) -> None:
        notices = parse_list_html(LIST_HTML)
        self.assertEqual(len(notices), 2)
        self.assertEqual(notices[0]["seq"], "306214")
        self.assertIn("청년 매입임대주택", notices[0]["title"])
        self.assertEqual(notices[0]["posted_on"], "2026-06-26")
        self.assertEqual(notices[0]["dept"], "매입주택공급부")


class TitleFilterTests(unittest.TestCase):
    def test_keep_recruit_skip_announcement(self) -> None:
        self.assertTrue(is_recruit_housing_notice("2026년 1차 청년 매입임대주택 입주자 모집공고"))
        self.assertTrue(is_recruit_housing_notice("제8차 장기전세주택2(미리내집) 입주자 모집 공고"))
        self.assertFalse(is_recruit_housing_notice("[당첨자발표] 2026년 다자녀 매입임대주택 입주자모집공고"))
        self.assertFalse(is_recruit_housing_notice("제51차 장기전세주택 입주자 모집공고"))
        self.assertFalse(is_recruit_housing_notice("[청약접수 결과] 2026년 1차 청년 매입임대주택"))


class AttachmentTests(unittest.TestCase):
    def test_pick_public_housing_xlsx(self) -> None:
        files = parse_down_list(DOWN_HTML)
        chosen = pick_housing_attachment(files)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen["fileSeq"], "2")
        self.assertTrue(is_housing_excel(chosen["oriFileNm"]))
        self.assertFalse(is_housing_excel("[첨부] 도면 및 사진(링크).xlsx"))

    def test_excel_link_txt(self) -> None:
        self.assertTrue(is_excel_link_note("[주택목록] 엑셀파일 (링크)_수정.txt"))
        url = parse_webhard_url(
            "[주택목록] 엑셀파일 (링크)\n\nhttps://webhard.i-sh.co.kr/pm/linkdown.htm?lid=69c32ad53bd992124201\n"
        )
        self.assertEqual(
            url,
            "https://webhard.i-sh.co.kr/pm/linkdown.htm?lid=69c32ad53bd992124201",
        )
        files = [
            {"oriFileNm": "공고문.pdf", "fileSeq": "1"},
            {"oriFileNm": "[주택목록] 엑셀파일 (링크).txt", "fileSeq": "5"},
        ]
        chosen = pick_housing_attachment(files)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen["fileSeq"], "5")


class NormalizeExcelTests(unittest.TestCase):
    def test_notice_filename(self) -> None:
        name = notice_filename("2026-06-26", "[수정] 청년 매입임대/입주자 모집공고")
        self.assertTrue(name.startswith("2026.06.26 SH "))
        self.assertNotIn("/", name)
        self.assertTrue(name.endswith(".xlsx"))

    def test_sh_youth_layout(self) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([None, "제목"])
        sheet.append([None, "연번", "구분", "자치구", "주택명", "소재지 주소", "주택구조", "전용면적(㎡)", "임대보증금(원)", "월임대료(원)"])
        sheet.append(
            [
                None,
                1,
                "신규공급",
                "강동구",
                "희망",
                "서울특별시 강동구 풍성로42길 12",
                "개방형원룸",
                29.22,
                1_000_000,
                277700,
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sh.xlsx"
            workbook.save(path)
            frame = normalize_housing_excel(path)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["시도"], "서울특별시")
        self.assertEqual(frame.iloc[0]["시군구"], "강동구")
        self.assertEqual(frame.iloc[0]["주소"], "서울특별시 강동구 풍성로42길 12")
        self.assertEqual(frame.iloc[0]["보증금"], 1_000_000)
        self.assertEqual(frame.iloc[0]["주택명"], "희망")
        self.assertEqual(frame.iloc[0]["주택구조(방수)"], "개방형원룸")


if __name__ == "__main__":
    unittest.main()
