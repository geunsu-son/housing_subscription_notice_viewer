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
- GitHub Actions `Crawl LH rental notices`가 매주 월요일 07:00 KST에 같은 명령을 돌리고, 새 데이터가 있으면 커밋합니다.

### SH 매입임대 자동 수집

SH [주택임대 공고](https://www.i-sh.co.kr/main/lay2/program/S1T297C4476/www/brd/m_247/list.do?multi_itm_seq=2)에서 **매입임대·미리내집·장기미임대** 모집공고의 주택목록 엑셀만 가져옵니다.

```bash
python -m pip install -r scripts/requirements.txt
python scripts/crawl_sh.py --lookback-days 90 --max-new 20
```

- 목록·상세는 게시판 HTML, 첨부는 상세 페이지의 `downList`와 `innoFD.do`를 사용합니다.
- 주택목록은 엑셀(`xlsx`/`xls`), `[주택목록] 엑셀파일 (링크).txt` 웹하드 링크, 또는 **텍스트 표가 들어 있는 주택목록 PDF**에서 가져옵니다.
- 2026년 공고처럼 엑셀 없이 PDF만 있는 경우가 있습니다. 표에서 주소·전용면적·보증금을 읽습니다.
- 한글 CID 폰트로 글자가 깨지는 PDF, 팸플릿·단지 집계표, 공고문 PDF/HWP, 도면·사진 파일은 건너뜁니다.
- 이미 `scripts/sh-crawl-state.json`에 있는 공고는 건너뜁니다.
- GitHub Actions `Crawl SH rental notices`가 매주 월요일 07:30 KST에 같은 명령을 돌리고, 새 데이터가 있으면 커밋합니다.

## Cloudflare Pages 배포

정적 사이트 파일은 `web/` 아래에만 있습니다. 저장소 루트(`/`)에는 `index.html`이 없습니다.

### 루트 404 증상 (현재 상태)

배포는 됐는데 `https://housing-subscription-notice-viewer.pages.dev/`만 404이고,  
`https://housing-subscription-notice-viewer.pages.dev/web/index.html`은 열리면 **출력 디렉터리 설정 문제**입니다.

저장소 전체가 사이트 루트로 올라가서, 페이지가 `/web/` 경로 아래에 붙은 상태입니다.

Cloudflare Pages **Settings → Builds**에서 아래 **둘 중 하나**로 맞춘 뒤 **Retry deployment** 하세요.

| | Root directory | Build output directory |
|---|---|---|
| **A** | `web` | `/` (또는 비움) |
| **B** | `/` (또는 비움) | `web` |

- Build command: 비움
- Framework preset: None

### 방법 A: GitHub Actions (권장)

`.github/workflows/deploy-pages.yml`이 `web/` **폴더 내용만** Pages 루트에 올립니다 (`npx wrangler pages deploy web`). 대시보드 디렉터리 설정과 무관하게 올바른 경로로 배포됩니다.

GitHub 저장소 **Settings → Secrets and variables → Actions**에 아래 시크릿을 등록합니다.

| 시크릿 | 값 |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API 토큰 (`Account` → `Cloudflare Pages` → `Edit` 권한) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 대시보드 URL의 Account ID |

시크릿 등록 후 Actions 탭에서 **Deploy to Cloudflare Pages** 워크플로를 `workflow_dispatch`로 한 번 실행하거나, `main`에 푸시하면 배포됩니다.

배포 URL: `https://housing-subscription-notice-viewer.pages.dev/`

### 방법 B: 로컬에서 수동 배포

```bash
npx wrangler login
npx wrangler pages deploy web --project-name=housing-subscription-notice-viewer
```

### 방법 C: Cloudflare 대시보드 Git 연동

Workers Builds가 아니라 **Pages → Create project → Connect to Git**으로 연결합니다. 위 **루트 404 증상** 표의 A 또는 B 설정을 반드시 적용하세요.

`npx wrangler deploy`(Workers)는 `*.workers.dev`로만 배포되며 `*.pages.dev`를 채우지 않습니다. Pages로 옮긴 뒤에는 Workers Builds 설정을 끄거나 deploy 명령을 Pages용으로 바꿔야 합니다.

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
