---
id: "project-10-delivery-estimate"
type: "project"
name: "Expected delivery date on order status"
tier: "tier-3"
priority: "3"
status: "active"
intro: "Surface the expected delivery date in the order status screen."
dates:
  started: "2026-07-20"
  target_delivery: "2026-09-12"
  deadline_text: ""
  deadline_type: "soft"
tech_footprint:
  platforms:
    - "iOS"
    - "Android"
  qa_effort: "low"
  content_impact: false
jira:
  request: "NIMBUS-1099"
  epics:
    - "NIMBUS-1100"
confluence:
  - "https://confluence.example.com/display/ORD/Delivery-estimate"
todos: []
todos_history:
  - id: "todo-project-10-delivery-estimate-1-1786000000"
    text: "Validate the estimate with the logistics team"
    deadline: "2026-08-14"
    done: true
    completed_at: "2026-08-14 15:30"
  - id: "todo-project-10-delivery-estimate-2-1786000001"
    text: "Add the tracking event to the analytics plan"
    deadline: ""
    done: true
    completed_at: "2026-08-20 10:05"
---

## Notes

`deadline_text` is empty on purpose: the badge must fall back to
`target_delivery`, and only then to N/A.
