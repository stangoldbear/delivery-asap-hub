---
id: "project-9-store-credit"
type: "project"
name: "Store credit as a payment method"
tier: "tier-3"
priority: "2"
status: "blocked"
blocked_reason: ""
intro: ""
dates:
  started: "2026-08-11"
  target_delivery: "2026-11-05"
  deadline_text: "2026-11-05"
  deadline_type: "soft"
tech_footprint:
  platforms:
    - "iOS"
    - "Android"
    - "Backend (dev)"
  qa_effort: "high"
  content_impact: false
stakeholders:
  tech_lead: "stakeholder-alan-turing"
dependencies:
  upstream:
    - project_or_service: "Payment orchestrator"
      team: "Payments"
      contact: "stakeholder-alan-turing"
      criticality: "high"
jira:
  request: "NIMBUS-1180"
todos: []
todos_history: []
---

## Notes

Blocked with no reason recorded on purpose: the status pill must render
without a hover tooltip, and the empty intro must show its empty state.
