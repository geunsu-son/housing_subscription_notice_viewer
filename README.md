# 청약 공고 뷰어

HUG, LH, SH 청약 공고를 필터로 조회하고 네이버 지도로 열어보는 정적 사이트입니다. Cloudflare 무료 플랜에 올리도록 만들어 두었습니다.

## 로컬에서 보기

```bash
python -m pip install -r scripts/requirements.txt
python scripts/build_data.py
python -m http.server 8000 --directory web
```

브라우저에서 http://localhost:8000 을 엽니다. `web/index.html`을 파일로 직접 열면 데이터 `fetch`가 실패합니다.

## 공고 추가·수정

수동으로 넣을 때는 아래처럼 합니다.

1. `source/`에 엑셀을 넣습니다. 파일명: `{날짜} {주택공사} {공고명}.xlsx`  
   예: `2025.12.10 SH 25년 3차 장기매임대 매입임대주택.xlsx`
2. `python scripts/build_data.py`
3. 생성된 `web/data/`를 커밋하고 푸시합니다. Cloudflare가 연결되어 있으면 다시 배포됩니다.

엑셀 컬럼 분기는 예전 Streamlit 앱과 같습니다.

- `공급계` 있음: SH 행복주택형
- `매입유형` 있음: HUG형
- 그 외: `주택구조(방수)` 또는 `공급형` 필요

JSON은 저장소의 `web/data/`에 들어 있습니다. Cloudflare에서 엑셀을 다시 변환할 필요는 없습니다.

### LH 매입임대 자동 수집

LH 청약플러스 [임대주택 공고문](https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026)에서 **매입임대** 공고의 게시용 주택목록만 가져옵니다.

```bash
python -m pip install -r scripts/requirements.txt
python scripts/crawl_lh.py --lookback-days 90 --max-new 20
```

- 목록은 사이트 HTML, 첨부 목록은 `wrtFileDownl.do` JSON을 사용합니다.
- 공고문 PDF/HWP는 받지 않고, 파일명에 `주택목록`·`주택내역`이 있는 엑셀만 받습니다.
- 이미 `scripts/lh-crawl-state.json`에 있는 공고는 건너뜁니다.
- GitHub Actions `Crawl LH rental notices`가 매일 07:00 KST에 같은 명령을 돌리고, 새 데이터가 있으면 커밋합니다.

SH 자동 수집은 아직 넣지 않았습니다.

## Cloudflare 배포

`wrangler.toml`이 `web/`을 정적 에셋으로 올립니다. 배포 명령은 `npx wrangler deploy`입니다.

대시보드에서 아래처럼 두면 됩니다.

- Build command: 비움
- Deploy command: `npx wrangler deploy`
- Python/`pip install`은 쓰지 않음 (루트에 `requirements.txt`를 두지 않음)

Pages만 쓰는 경우에는 배포 명령을 `npx wrangler pages deploy web`으로 바꾸면 됩니다.

## 구성

| 경로 | 역할 |
|---|---|
| `source/` | 원본 엑셀 |
| `scripts/build_data.py` | 엑셀 → `web/data/*.json` |
| `scripts/requirements.txt` | 로컬 데이터 변환용 Python 패키지 |
| `web/` | 정적 사이트 (배포 대상) |
| `scripts/crawl_lh.py` | LH 매입임대 주택목록 수집 |
| `scripts/lh-crawl-state.json` | 이미 가져온 LH 공고 ID |
| `crawling_rent_house_list.ipynb` | 공고 수집 노트북 (사이트와 별개) |
