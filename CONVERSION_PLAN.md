# Streamlit → Cloudflare Pages 변환 계획

## 목표

청약 공고 뷰어를 Streamlit 서버 앱에서 **정적 HTML/JS 사이트**로 바꾸고, Cloudflare Pages 무료 플랜에 배포 가능하게 만든다.

완료 조건:

- 현재 뷰어의 조회·필터·표·지도 링크가 브라우저만으로 동작한다.
- 엑셀은 빌드 시 JSON으로 변환한다. 런타임에 엑셀/Python/`sqlite3`를 쓰지 않는다.
- Streamlit 앱 코드와 Streamlit 실행 설정을 삭제한다.
- Cloudflare Workers/D1 없이 Pages 정적 호스팅만 사용한다.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 앱 | `streamlit_app.py` (청약 공고 뷰어) |
| 데이터 | `source/*.xlsx` 11개, 총 약 436KB, 행 수 약 40~751 |
| 의존성 | `streamlit`, `openpyxl` (`requirements.txt`의 `requests`는 뷰어 미사용) |
| 실행 | `.devcontainer`에서 `streamlit run streamlit_app.py` (포트 8501) |
| 크롤링 | `crawling_rent_house_list.ipynb` — 뷰어와 분리. 이번 변환 범위 밖 |

뷰어는 읽기 전용이다. 로그인, 저장, 요청 시 크롤링이 없다.

공고 파일마다 컬럼이 다르다. 앱은 대략 세 갈래로 나눈다.

1. `공급계` 있음 → SH 행복주택형. 필터: `공급구분1`, `공급구분2`
2. `매입유형` 있음 → HUG형. 필터: `주택유형`, `매입유형`
3. 그 외 → `주택구조(방수)` 또는 `공급형`으로 필터. 표시 컬럼은 `시도`, `시군구`, `주택명`, `주택군`, `주소`, `주택유형`, `주택구조(방수)` 중 존재하는 것

일부 LH 파일은 `방수`, `모집단위(주택군)`처럼 앱이 직접 쓰지 않는 컬럼명을 쓴다. 변환 시 **현재 Streamlit과 동일한 컬럼만 노출**한다. 컬럼 정규화는 이번 범위에 넣지 않는다.

## 아키텍처

```
source/*.xlsx          ← 원본 (유지)
        │
        ▼  로컬/CI에서 python scripts/build_data.py
web/data/index.json    ← 공고 목록
web/data/*.json        ← 공고별 행
web/index.html
web/app.js
web/styles.css
        │
        ▼  Cloudflare Pages (빌드 없이 정적 업로드)
브라우저에서 필터·표 렌더
```

JSON을 쓰는 이유:

- 데이터 합계가 수천 행 수준이라 클라이언트 필터로 충분하다.
- 공고마다 스키마가 달라 단일 SQLite 테이블보다 파일 분리가 단순하다.
- Pages 무료 플랜은 정적 파일만 있으면 된다. `sql.js`/D1/Workers는 필요 없다.

엑셀을 사이트에서 직접 읽지 않는다. 공고가 바뀌면 `build_data.py`를 다시 돌리고 `web/data/`를 커밋한다.

Cloudflare Pages 빌드 이미지에서 Python을 돌리지 않는다. Python 빌드 의존을 없애 무료 배포를 단순하게 유지한다.

## 산출물 구조

```
scripts/build_data.py      # 엑셀 → JSON
web/index.html
web/styles.css
web/app.js
web/data/index.json
web/data/<공고id>.json
wrangler.toml              # Pages 출력 디렉터리 = web
.gitignore                 # 필요 시 __pycache__ 등
requirements.txt           # pandas, openpyxl 만 (빌드용)
CONVERSION_PLAN.md         # 이 문서 (구현 PR에서 삭제하거나 README로 흡수)
```

유지:

- `source/`
- `crawling_rent_house_list.ipynb`
- `rent_house_list.xlsx` (크롤링 산출물, 뷰어 미사용)

삭제 (마무리 단계):

- `streamlit_app.py`
- `requirements.txt`의 `streamlit`, `requests`(뷰어 미사용이면 제거)
- `.devcontainer/devcontainer.json`의 Streamlit 실행·포트 8501·`streamlit_app.py` 자동 오픈

## 데이터 계약

### `web/data/index.json`

파일명 규칙 `연도.주택공사 공고명.xlsx`을 그대로 파싱한다. (`streamlit_app.py`의 `get_file_df()`와 동일)

```json
{
  "notices": [
    {
      "id": "2025.06.25-HUG-25년2분기-든든전세주택",
      "year": "2025.06.25",
      "company": "HUG",
      "title": "25년2분기 든든전세주택",
      "sourceFile": "2025.06.25 HUG 25년2분기 든든전세주택.xlsx",
      "dataFile": "data/2025.06.25-HUG-25년2분기-든든전세주택.json",
      "kind": "hug"
    }
  ]
}
```

`kind`: `sh_supply` (`공급계`) / `hug` (`매입유형`) / `standard` (나머지)

### 공고별 JSON

```json
{
  "id": "...",
  "kind": "hug",
  "showCols": ["시도", "시군구", "주소", "주택유형", "매입유형", "안심전세포털", "전용면적", "보증금", "월임대료", "네이버지도"],
  "filterCols": ["주택유형", "매입유형"],
  "rows": [
    {
      "시도": "서울특별시",
      "시군구": "강남구",
      "주소": "...",
      "전용면적": 39.5,
      "보증금": 120000000,
      "월임대료": 0,
      "네이버지도": "https://map.naver.com/p/search/..."
    }
  ]
}
```

전처리는 현 `load_data()`와 맞춘다.

- `주소` trim
- `보증금`, `월임대료`(있으면) 콤마/따옴표 제거 후 정수
- `전용면적` float
- `네이버지도` = `https://map.naver.com/p/search/{주소}`
- `showCols` / `filterCols` 규칙은 현 if/elif 그대로
- 정렬: `시도`, `시군구`, `주소`

표시용 평·억원·만원 문자열은 JSON에 넣지 않고 프론트에서 계산한다.

## 기능 대응

| Streamlit | 정적 사이트 |
|---|---|
| 사이드바 연락처 | 푸터 |
| 제목/설명 | `index.html` |
| 연도/주택공사/공고 `selectbox` | `<select>` 3개, 연도→공사→공고 종속 |
| 시도/시군구 | `<select>`, `전체` 옵션 |
| 유형 `multiselect` (값이 1개면 숨김) | 체크박스. 유일 값이면 숨기고 전체 선택 |
| 전용면적/보증금 `slider` | `input type=range` 쌍 또는 number min/max |
| 주소 중복제거 `toggle` | checkbox. groupby 키·min/max·주택수 로직 동일 |
| 값이 하나인 컬럼 숨김 | 렌더 시 동일 |
| `st.data_editor` + LinkColumn | HTML table. 네이버지도/안심전세포털은 `<a target="_blank">` |
| 건수 표시 | `주택 리스트 조회 (총 N건)` |

레이아웃은 현 앱과 같이 왼쪽 공고 선택(약 25%), 오른쪽 필터(약 75%), 아래 표.

공고를 바꾸면 해당 JSON만 `fetch`한다. 11개 파일을 한꺼번에 받지 않는다.

## 단계

### 1. 데이터 빌드 스크립트

- `scripts/build_data.py` 추가
- `source/`를 읽어 `web/data/` 생성
- 파일명 파싱, kind 판별, 전처리, `index.json` 작성을 한곳에 둔다
- 로컬 검증: 공고별 행 수가 엑셀과 같고, kind/showCols가 앱 분기와 같은지 출력

### 2. 정적 프론트

- `web/index.html`, `web/styles.css`, `web/app.js`
- 외부 UI 프레임워크 없이 vanilla JS
- 필터는 메모리 배열에서 수행
- 빈 결과, 파일 로드 실패는 짧은 메시지로 표시

### 3. 로컬 확인

- `python scripts/build_data.py`
- `python -m http.server`로 `web/` 서빙 (file:// 에서 fetch가 막히지 않게)
- 공고 11개를 돌아가며: 기본 표, 시도 필터, 면적/보증금, 중복제거, 지도 링크
- SH 행복주택 / HUG / LH 표준 / `공급형`만 있는 파일을 각각 한 개 이상 확인
- 브라우저 도구로 데스크톱·좁은 폭 레이아웃 확인

### 4. Cloudflare Pages 설정

- `wrangler.toml`에 Pages 프로젝트와 출력 디렉터리 `web` 지정
- 빌드 커맨드 없음. `web/data/`는 저장소에 포함
- README에 배포 절차: Pages에서 `web`을 출력 디렉터리로 지정, 또는 `npx wrangler pages deploy web`
- 커스텀 도메인·Workers는 범위 밖

### 5. Streamlit 제거 (마무리)

구현과 로컬 확인이 끝난 뒤에만 삭제한다.

삭제:

- `streamlit_app.py`
- `requirements.txt`에서 `streamlit` 제거. 빌드용 `pandas`, `openpyxl`만 남김. 뷰어가 쓰지 않는 `requests` 제거
- `.devcontainer/devcontainer.json`
  - `openFiles`에서 `streamlit_app.py` 제거, `web/index.html` 등으로 교체
  - `pip3 install --user streamlit` 제거
  - `postAttachCommand`의 `streamlit run ...` 제거. 필요하면 `python -m http.server -d web`로 교체
  - 포트 8501 관련 설정 제거

남기지 않는 것:

- Streamlit 호환 래퍼, 리다이렉트, 주석 처리된 구 앱

문서:

- 짧은 `README.md` 추가: 데이터 갱신(`source/` 수정 → `python scripts/build_data.py` → 커밋), 로컬 미리보기, Pages 배포
- 이 계획 문서는 README에 흡수한 뒤 삭제해도 된다

### 6. 범위 밖

- 노트북 크롤링을 사이트에 넣기
- 엑셀 컬럼명 정규화 (`방수` → `주택구조(방수)` 등)
- D1, sql.js, Workers API
- 검색, 즐겨찾기, 로그인
- 엑셀 업로드 UI

## 공고 추가 워크플로 (변환 후)

1. `source/`에 xlsx 추가 (파일명: `{날짜} {공사} {공고명}.xlsx`)
2. `python scripts/build_data.py`
3. `web/data/` 변경 커밋·푸시 → Pages 재배포

## 위험

- 스키마 3분기에 안 들어가는 새 엑셀은 지금과 같이 실패한다. 빌드 스크립트가 파일명과 이유를 출력해야 한다.
- JSON을 커밋하므로 엑셀과 JSON이 어긋날 수 있다. README에 빌드 순서를 적고, 가능하면 빌드 스크립트가 행 수를 출력한다.
- `file://`로 열면 `fetch`가 실패한다. 로컬은 HTTP 서버를 쓴다.

## 작업 순서 요약

1. `build_data.py` + 생성된 JSON
2. 정적 프론트 (기능 동등)
3. wrangler/README (Pages)
4. 로컬에서 공고·필터·링크 확인
5. `streamlit_app.py` 및 Streamlit 설정 삭제
6. devcontainer를 정적 미리보기에 맞게 수정
