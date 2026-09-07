---
name: audit-installed-bundles
description: 현재 저장소의 .cursor/와 로컬 catalog를 조사해 어떤 에이전트 번들이 설치되어 있는지 파악한다
---

# Audit Installed Bundles

## 사용 시점

- Bundle Catalog gate가 번들 적용 여부를 확인할 때
- `manage-agent-bundles` 실행 전 현재 상태를 파악할 때
- 어떤 번들이 이미 `.cursor/`에 있는지 사용자에게 설명해야 할 때

## 목표

추정하지 않고 `.cursor/`, 로컬 catalog, 소스 catalog를 실제로 읽어 **현재 설치 상태**를 보고한다. 이 Skill은 파일을 설치·삭제하지 않는다.

## 기본값

- **번들 소스**: `https://github.com/geunsu-son/agent_skill_bundle`
- **소스 catalog**: `workshop-kit/catalog.md`
- **로컬 catalog**: `.cursor/agent-bundles/catalog.md`

## 절차

### 1. 저장소 유형 판별

- `workshop-kit/catalog.md`가 있으면 **번들 소스 저장소**다.
- 없으면 **소비 프로젝트**다.

### 2. `.cursor/` 스캔

다음을 수집한다.

- `.cursor/rules/*.mdc` — Rule 파일 목록
- `.cursor/skills/*/SKILL.md` — Skill 디렉터리 목록
- `.cursor/agent-bundles/catalog.md` 존재 여부

각 Rule·Skill의 파일명과 경로를 적는다.

### 3. catalog 읽기

- 로컬 catalog가 있으면 `Installed Bundles` 표를 읽는다.
- 번들 소스의 `workshop-kit/catalog.md`를 읽어 등록 번들과 Rule·Skill 매핑을 확보한다.

소비 프로젝트에서는 소스 catalog를 번들 소스 URL에서 가져온다.

### 4. 번들 매칭

소스 catalog의 각 번들에 대해 아래를 판정한다.

| 상태 | 의미 |
|---|---|
| `installed` | Rule과 Skill(필요 시 Script·Automation)이 `.cursor/`에 모두 있다 |
| `partial` | 일부만 있다 |
| `catalog-only` | 로컬 catalog에는 있으나 `.cursor/` 파일이 없거나 부족하다 |
| `files-only` | `.cursor/`에 파일은 있으나 로컬 catalog에 없다 |
| `missing` | `.cursor/`와 로컬 catalog 모두에 없다 |

Bundle Catalog gate 번들은 아래 파일로 판정한다.

- Rule: `bundle-catalog.mdc`
- Skill: `audit-installed-bundles`, `manage-agent-bundles`, `report-bundle-feedback`

### 5. 이상 징후 찾기

- 같은 목적의 Rule·Skill이 중복 설치되었는지
- 소스 catalog에 없는 orphan Rule·Skill이 `.cursor/`에 있는지
- 로컬 catalog와 `.cursor/`가 어긋나는지
- Bundle Catalog gate가 없는데 다른 번들만 있는지

### 6. gate 판단 입력 만들기

다음을 정리한다.

- **gate 상태**: Bundle Catalog가 `installed` / `partial` / `missing` 중 무엇인가
- **이미 설치된 번들**
- **부분 설치·불일치 번들**
- **아직 설치되지 않은 후보**
- **조치 제안**: gate 보완, 재설치, catalog 정리. 추가 설치는 사용자가 요청할 때만 gate를 통해 진행

### 7. 결과 보고

```md
## 번들 설치 조사 결과

### Gate 상태
- Bundle Catalog: installed | partial | missing

### 설치됨
- ...

### 부분 설치·불일치
- ...

### 미설치 후보
- ...

### Orphan 파일
- ...

### Gate 다음 단계
- gate 보완 필요 여부, catalog 정리 필요 여부
- 추가 설치는 사용자가 요청할 때만 진행 (이 Skill에서는 설치를 권유하지 않음)
```

## 완료 조건

- `.cursor/`와 catalog를 실제로 읽었다.
- 번들별 상태(`installed` / `partial` / `missing` 등)가 구분되어 있다.
- gate가 다음 설치 질문을 할 수 있을 만큼 상태와 불일치가 정리되어 있다.
- `audit` 요청이면 설치 권유 없이 보고만 한다.
- 이 Skill 단계에서 파일을 설치·삭제하지 않았다.

## 기본 요청 예시

```text
이 저장소에 어떤 Agent Skill Bundle이 설치되어 있는지 조사해줘.
.cursor/와 catalog를 확인하고, gate 기준으로 설치·미설치·불일치를 정리해줘.
```
