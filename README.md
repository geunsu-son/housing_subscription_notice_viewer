# 청약 공고 뷰어

HUG, LH, SH 청약 공고를 필터로 조회하고 네이버 지도로 열어보는 정적 사이트입니다. Cloudflare Pages 무료 플랜에 올리도록 만들어 두었습니다.

## 로컬에서 보기

```bash
python -m pip install -r requirements.txt
python scripts/build_data.py
python -m http.server 8000 --directory web
```

브라우저에서 http://localhost:8000 을 엽니다. `web/index.html`을 파일로 직접 열면 데이터 `fetch`가 실패합니다.

## 공고 추가·수정

1. `source/`에 엑셀을 넣습니다. 파일명: `{날짜} {주택공사} {공고명}.xlsx`  
   예: `2025.12.10 SH 25년 3차 장기매임대 매입임대주택.xlsx`
2. `python scripts/build_data.py`
3. 생성된 `web/data/`를 커밋하고 푸시합니다. Pages가 연결되어 있으면 다시 배포됩니다.

엑셀 컬럼 분기는 예전 Streamlit 앱과 같습니다.

- `공급계` 있음: SH 행복주택형
- `매입유형` 있음: HUG형
- 그 외: `주택구조(방수)` 또는 `공급형` 필요

## Cloudflare Pages 배포

저장소의 `web/` 폴더만 올립니다. 빌드 명령은 비워 두고, 출력 디렉터리는 `web`입니다.

- 대시보드: Pages 프로젝트에서 Root directory는 비우고, Build output directory를 `web`으로 지정
- CLI: `npx wrangler pages deploy web`

`wrangler.toml`의 `pages_build_output_dir`도 `web`입니다.

## 구성

| 경로 | 역할 |
|---|---|
| `source/` | 원본 엑셀 |
| `scripts/build_data.py` | 엑셀 → `web/data/*.json` |
| `web/` | 정적 사이트 |
| `crawling_rent_house_list.ipynb` | 공고 수집 노트북 (사이트와 별개) |
