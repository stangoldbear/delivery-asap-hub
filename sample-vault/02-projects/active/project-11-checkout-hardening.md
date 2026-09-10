---
id: "project-11-checkout-hardening"
type: "project"
name: "Checkout hardening"
tier: "tier-9"
priority: "abc"
status: "on-hold"
intro: "Deliberately malformed card: unknown tier, unknown status, non-numeric priority."
dates:
  target_delivery: "2026-10-15"
  deadline_text: "2026-10-15"
  deadline_type: "whenever"
tech_footprint:
  platforms:
    - "Backend (dev)"
  qa_effort: "medium"
  content_impact: false
jira:
  request: "NIMBUS-1300"
todos:
  - id: "todo-project-11-checkout-hardening-1-1788000060"
    text: "Fix the tier and status of this card from the Advanced Edit form"
    deadline: ""
    done: false
---

## Notes

Fixture for the fallback paths: the unknown tier falls back to the default
tier, the unknown status keeps its stored value in a disabled option instead
of being silently rewritten, and the non-numeric priority sorts last.
