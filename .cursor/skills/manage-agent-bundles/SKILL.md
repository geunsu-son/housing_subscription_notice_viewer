---
name: manage-agent-bundles
description: Bundle Catalog gate 설치, 번들 선택, 설치·업데이트·삭제·보관을 수행하는 절차
---

# Manage Agent Bundles

## 사용 시점

- 작업 중인 저장소에 Agent Skill Bundle을 연결·점검할 때
- gate를 통해 추가 번들을 설치할 때
- 설치된 번들을 업데이트·삭제할 때

설치 상태 조사는 `audit-installed-bundles` Skill에 맡긴다. 이 Skill은 조사 결과를 받은 뒤 설치·변경을 수행한다.

## 기본값

- **번들 소스**: `https://github.com/geunsu-son/agent_skill_bundle`
- **소스 catalog**: `workshop-kit/catalog.md`
- **로컬 catalog**: `.cursor/agent-bundles/catalog.md`

번들 소스 저장소를 clone하지 않는다. 필요한 파일만 가져온다.

## 절차

### 1. 요청과 범위 확인

- **요청 유형**: `connect`(연결), `add`(추가 설치), `audit`(조사만), `update`, `remove` 중 무엇인가
- 번들 소스 URL
- 사용자가 이미 선택한 번들 또는 Agent 작업 목적

이미 제공된 정보는 다시 묻지 않는다.

`connect`가 아닌 일반 작업 turn에서는 번들 추가 설치를 묻지 않는다.

### 2. Bundle Catalog gate 보완

gate가 `missing` 또는 `partial`이면 아래 Bundle Catalog 번들 파일을 번들 소스에서 가져와 `.cursor/`에 둔다.

- `workshop-kit/rules/bundle-catalog.mdc` → `.cursor/rules/bundle-catalog.mdc`
- `workshop-kit/skills/audit-installed-bundles/SKILL.md` → `.cursor/skills/audit-installed-bundles/SKILL.md`
- `workshop-kit/skills/manage-agent-bundles/SKILL.md` → `.cursor/skills/manage-agent-bundles/SKILL.md`
- `workshop-kit/skills/report-bundle-feedback/SKILL.md` → `.cursor/skills/report-bundle-feedback/SKILL.md`

로컬 catalog가 없으면 아래 템플릿으로 만든다. gate 보완만으로 다른 번들은 아직 설치하지 않는다.

```md
# Local Agent Bundle Catalog

## Bundle Source

https://github.com/geunsu-son/agent_skill_bundle

## Feedback Participation

| 항목 | 값 |
|---|---|
| status | pending |
| set_at | — |

`connect` turn 끝에 `enabled` 또는 `disabled`로 기록한다.

## Installed Bundles

| 번들 | 상태 | Rule | Skill | 메모 |
|---|---|---|---|---|
| Bundle Catalog | active | bundle-catalog.mdc | audit-installed-bundles, manage-agent-bundles, report-bundle-feedback | gate |

## Feedback Log

| date | action | note |
|---|---|---|
```

파일 가져오기 예시:

```bash
SOURCE=https://github.com/geunsu-son/agent_skill_bundle
REF=main
curl -fsSL "$SOURCE/raw/$REF/workshop-kit/rules/bundle-catalog.mdc" -o .cursor/rules/bundle-catalog.mdc
curl -fsSL "$SOURCE/raw/$REF/workshop-kit/skills/audit-installed-bundles/SKILL.md" -o .cursor/skills/audit-installed-bundles/SKILL.md
curl -fsSL "$SOURCE/raw/$REF/workshop-kit/skills/manage-agent-bundles/SKILL.md" -o .cursor/skills/manage-agent-bundles/SKILL.md
curl -fsSL "$SOURCE/raw/$REF/workshop-kit/skills/report-bundle-feedback/SKILL.md" -o .cursor/skills/report-bundle-feedback/SKILL.md
```

### 3. 설치 상태 조사

`audit-installed-bundles` Skill 절차를 실행한다.

- `.cursor/`와 로컬 catalog, 소스 catalog를 읽는다
- 번들별 `installed` / `partial` / `missing` / `catalog-only` / `files-only` 상태를 만든다
- gate 다음 단계 제안을 받는다

조사 결과를 사용자에게 보여 준다. `audit` 요청이면 여기서 종료한다.

### 4. gate: 설치할 번들 선택

**`connect` 또는 `add` 요청일 때만** 실행한다.

- `connect`: 조사 결과를 보여 준 뒤, **이번 turn 안에서 한 번만** 추가 설치할 번들을 묻는다.
- `add`: 요청에 번들이 지정되어 있으면 바로 설치하고, 없을 때만 짧게 확인한다.
- 사용자가 “추가하지 않음”, “gate만 유지”, “여기까지” 등으로 끝내면 설치하지 않고 종료한다.

질문에 포함할 내용:

- 이미 설치된 번들
- 불일치·부분 설치가 있으면 정리 필요 여부
- 아직 설치되지 않은 후보

```text
현재 설치 상태를 확인했습니다.

[설치됨]
- ...

[미설치 후보]
1. Agent Skill Workshop — 아이디어를 번들로 구현
2. Session Market Briefing — 세션 경제 브리핑
3. Web Crawler Craft — 웹 크롤러 제작
4. 지금은 추가 설치하지 않음

어떤 번들을 설치할까요?
```

사용자가 고른 번들만 다음 단계로 넘긴다.

### 5. 선택된 번들 설치

#### 공방 키트 번들

```text
workshop-kit/rules/<rule>.mdc        → .cursor/rules/<rule>.mdc
workshop-kit/skills/<skill>/SKILL.md → .cursor/skills/<skill>/SKILL.md
```

#### 예시 번들

```text
examples/<bundle-name>/rules/<rule>.mdc        → .cursor/rules/<rule>.mdc
examples/<bundle-name>/skills/<skill>/SKILL.md → .cursor/skills/<skill>/SKILL.md
```

예시 번들 Rule은 기본적으로 `alwaysApply: false`를 유지한다.

설치·삭제·업데이트 후 로컬 catalog를 갱신한다.

### 6. 피드백 참여 설정 (`connect`만)

`Feedback Participation`이 `pending`이거나 없을 때 **한 번** 묻는다.

```text
Agent Skill Bundle 개선에 참여하시겠습니까?

작업을 마치거나 Skill을 사용한 PR을 작성했을 때,
Rule·Skill에 추가·개선하면 좋겠다는 제안이 있으면 Issue로 보낼지 물어볼 수 있습니다.
보내기 전에는 Issue 초안을 보여 드리고, 정말 보낼지 다시 확인합니다.

- 예 → enabled
- 아니오 → disabled (이후 피드백 전송을 묻지 않음)
```

선택 결과를 `.cursor/agent-bundles/catalog.md`의 `Feedback Participation`에 기록한다. 이미 `enabled`/`disabled`이면 다시 묻지 않는다.

### 7. 재조사와 요약

변경이 있었다면 `audit-installed-bundles` Skill을 다시 실행한다.

```md
## 번들 관리 결과

### Gate 상태
- Bundle Catalog: installed | partial | missing

### 조사 결과
- ...

### 이번에 설치·변경한 번들
- ...

### 추가 설치 (요청 시에만)
- gate를 통해 추가 설치하려면 사용자가 명시적으로 요청한다.
```

연결 turn을 마칠 때 미설치 후보 목록을 반복해 설치를 재촉하지 않는다.

## 번들 소스 저장소 내부

`workshop-kit/catalog.md`가 있는 저장소에서는 원본 편집과 `.cursor/` 동기화를 수행한다. 연결 흐름은 동일하게 **gate 보완 → 조사 → 선택 → 설치**다.

## 완료 조건

- Bundle Catalog gate가 `installed` 상태다.
- 요청 유형(`connect` / `add` / `audit` / `update` / `remove`) 범위를 벗어나지 않았다.
- `connect`/`add` turn에서만 설치 질문을 했고, 그 외 turn에서는 추가 설치를 묻지 않았다.
- `connect` turn에서 피드백 참여(`enabled`/`disabled`)가 기록되었다.
- 재조사 후 로컬 catalog와 `.cursor/` 상태가 일치한다.

피드백 전송은 `report-bundle-feedback` Skill을 따른다. 작업 완료·Skill 사용 PR 작성 시, `enabled`일 때만 1차 gate를 연다.

## 기본 요청 예시

```text
지금 작업 중인 이 저장소에 Agent Skill Bundle을 연결해줘.
번들 소스: https://github.com/geunsu-son/agent_skill_bundle

1. Bundle Catalog gate를 먼저 설치하거나 보완하고
2. audit-installed-bundles로 현재 설치 상태를 조사한 뒤
3. 어떤 번들을 추가로 설치할지 나에게 물어봐
```
