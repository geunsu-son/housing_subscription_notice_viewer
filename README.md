# 청약 공고 뷰어

HUG, LH, SH 청약 공고를 필터로 조회하고 네이버 지도로 열어보는 정적 사이트입니다.

**배포:** Cloudflare Pages — https://housing-subscription-notice-viewer.pages.dev/

## 로컬에서 보기

```bash
python -m pip install -r scripts/requirements.txt
python scripts/build_data.py
python -m http.server 8000 --directory web
```

브라우저에서 http://localhost:8000 을 엽니다. `web/index.html`을 파일로 직접 열면 데이터 `fetch`가 실패합니다.

## 공고 추가·수정

1. `source/`에 엑셀을 넣습니다. 파일명: `{날짜} {주택공사} {공고명}.xlsx`  
   예: `2025.12.10 SH 25년 3차 장기매임대 매입임대주택.xlsx`
2. `python scripts/build_data.py`
3. 생성된 `web/data/`를 커밋하고 푸시합니다.

엑셀 컬럼 분기:

- `공급계` 있음: SH 행복주택형
- `매입유형` 있음: HUG형
- 그 외: `주택구조(방수)` 또는 `공급형` 필요

### LH 매입임대 자동 수집

```bash
python scripts/crawl_lh.py --lookback-days 90 --max-new 20
```

[LH 임대주택 공고문](https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026)에서 매입임대 주택목록 엑셀을 가져옵니다. GitHub Actions `Crawl LH rental notices`가 매주 월요일 07:00 KST에 실행됩니다.

### SH 매입임대 자동 수집

```bash
python scripts/crawl_sh.py --lookback-days 90 --max-new 20
```

[SH 주택임대 공고](https://www.i-sh.co.kr/main/lay2/program/S1T297C4476/www/brd/m_247/list.do?multi_itm_seq=2)에서 매입임대·미리내집·장기미임대 주택목록을 가져옵니다. GitHub Actions `Crawl SH rental notices`가 매주 월요일 07:30 KST에 실행됩니다.

## 구성

| 경로 | 역할 |
|---|---|
| `source/` | 원본 엑셀 |
| `scripts/build_data.py` | 엑셀 → `web/data/*.json` |
| `scripts/requirements.txt` | 로컬 데이터 변환용 Python 패키지 |
| `web/` | 정적 사이트 (배포 대상) |
| `scripts/crawl_lh.py` | LH 매입임대 주택목록 수집 |
| `scripts/lh-crawl-state.json` | 이미 가져온 LH 공고 ID |
| `scripts/crawl_sh.py` | SH 매입임대 주택목록 수집 |
| `scripts/sh-crawl-state.json` | 이미 가져온 SH 공고 ID |
| `crawling_rent_house_list.ipynb` | 공고 수집 노트북 (사이트와 별개) |
