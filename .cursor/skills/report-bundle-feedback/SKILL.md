---
name: report-bundle-feedback
description: 번들 Skill 사용 후 개선 제안을 Issue 초안으로 정리하고, 사용자 2차 승인 후 번들 소스 repo에 전송한다
---

# Report Bundle Feedback

`bundle-catalog` **총관리 Rule의 하위 Skill**입니다. 별도 번들이 아닙니다.  
Rule·Skill·gate 개선 제안을 번들 소스 repo Issue로 되돌릴 때 이 절차를 따른다.

## 사용 시점

다음 **모두**를 만족할 때만 시작한다.

- `.cursor/agent-bundles/catalog.md`의 `Feedback Participation`이 `enabled`다.
- **작업 완료**를 사용자가 알렸거나, **번들 Skill을 사용한 PR**이 작성되었다.
- 이번 작업에서 Rule·Skill·gate에 **추가·개선하면 좋겠다고 제안할 내용**이 있다.

`disabled`이면 이 Skill을 시작하지 않는다.

## 목표

번들 Skill 활용 과정에서 생긴 **개선 제안과 이유**를 번들 소스 repo Issue로 남긴다.  
전송 전 사용자가 본문을 검토하고 **2차 승인**한다. 실패해도 강요하지 않는다.

## 기본값

- **번들 소스 repo**: `geunsu-son/agent_skill_bundle`
- **Issue URL**: `https://github.com/geunsu-son/agent_skill_bundle/issues`

## 보낼 내용 (중심)

- 사용한 **번들·Skill·Rule** 이름
- Skill·Rule·gate에 **추가하거나 개선하면 좋겠다는 제안**
- **그렇게 제안하는 이유** (어떤 작업 맥락에서 불편·부족·과했는지)
- (선택) 바로 도움이 된 점, 과했던 절차

## 보내지 않을 내용

다음은 Issue 본문에 넣지 않는다. 초안 작성 후에도 다시 확인한다.

- API key, token, password, cookie, 세션 값
- 내부 전용 URL, 사설 IP, VPN 주소
- 고객·개인 식별 정보, 계약·매출 등 민감 업무 데이터
- consumer repo **소스 코드 전체** 또는 대용량 로그
- 사용자가 “빼 달라”고 한 내용

repo 이름·공개 URL·PR 번호·번들명 정도는 가능하나, 내부 전용 정보는 `[REDACTED]`로 바꾼다.

## 절차

### 1. 참여 설정 확인

`.cursor/agent-bundles/catalog.md`의 `Feedback Participation`을 읽는다.

| 값 | 동작 |
|---|---|
| `enabled` | 2단계로 진행 |
| `disabled` | 종료 (묻지 않음) |
| 없음 | `connect` 때 설정되지 않았으면 묻지 않고 종료 |

### 2. 1차 gate — 보내도 될지

개선 제안이 있을 때만 짧게 묻는다.

```text
이번 작업에서 Agent Skill Bundle Rule·Skill 개선 제안이 있습니다.
번들 소스 repo(agent_skill_bundle)에 Issue로 보내도 될까요?

- 보내면: 개선 제안과 이유만 전송합니다 (민감 정보는 제외).
- 보내지 않으면: 여기서 종료합니다.
```

“아니오”, “괜찮아”, “안 보내도 돼”면 **종료**. 재촉하지 않는다.

### 3. Issue 초안 작성

아래 형식으로 초안을 만든다. **개선 제안·이유**가 본문의 중심이어야 한다.

```md
## Summary

- Consumer repo: <repo name or public slug>
- Bundle(s) used: ...
- Trigger: work complete | PR <link or number>
- Date: YYYY-MM-DD

## Skill / Rule improvement suggestions

### 1. <Skill or Rule name>

**Suggestion:** 무엇을 추가·수정하면 좋은지

**Reason:** 작업 중 왜 필요했는지

### 2. ...

## What worked (optional)

- ...

## Out of scope

- No secrets or customer data included.
```

민감 정보가 섞였으면 제거하거나 `[REDACTED]` 처리한다.

### 4. 2차 gate — 초안 검토 후 전송 승인

초안 **전체**를 사용자에게 보여 준 뒤 묻는다.

```text
아래 Issue 초안을 검토해 주세요.
민감한 정보가 없는지 확인한 뒤, 정말 번들 소스 repo에 보낼까요?

---
<초안 전체>
---

- 예 → Issue 생성
- 아니오 → 전송하지 않고 종료 (초안은 consumer repo에만 남겨도 됨)
```

사용자가 수정을 요청하면 반영한 뒤 **다시 2차 gate**를 거친다.

### 5. Issue 전송

승인 후 번들 소스 repo에 Issue를 생성한다.

```bash
gh issue create \
  -R geunsu-son/agent_skill_bundle \
  --title "Bundle feedback: <bundle-name> — <short summary>" \
  --body-file /tmp/bundle-feedback.md \
  --label "bundle-feedback"
```

`gh`가 없거나 권한이 없으면 6단계로 넘긴다.

성공 시 Issue URL을 사용자에게 알려 준다.

### 6. 전송 실패 시 (선택 안내)

강요하지 않고 한 번만 정중히 안내한다.

```text
자동으로 Issue를 만들지 못했습니다 (권한 또는 도구 제한일 수 있습니다).
원하시면 아래 초안을 참고해 agent_skill_bundle repo에 Issue를 직접 등록해 주시면
번들 개선에 도움이 됩니다. 하지 않으셔도 괜찮습니다.

Issue 작성: https://github.com/geunsu-son/agent_skill_bundle/issues/new
```

초안을 `.cursor/agent-bundles/feedback-drafts/<date>-<bundle>.md`에 남겨도 된다.

### 7. 기록

전송·거절·실패 여부를 로컬 catalog `Feedback Log`에 한 줄 추가한다 (선택).

## 완료 조건

- `disabled`면 시작하지 않았다.
- `enabled`일 때 1차·2차 gate를 거쳤다.
- 전송 전 사용자가 초안 전체를 봤다.
- 민감 정보가 본문에 없다.
- 실패 시 강요 없이 선택 안내만 했다.

## 기본 요청 예시

```text
이번 작업에서 쓴 Skill 번들 개선 제안을
report-bundle-feedback Skill 절차로 Issue 초안까지 만들어줘.
```
