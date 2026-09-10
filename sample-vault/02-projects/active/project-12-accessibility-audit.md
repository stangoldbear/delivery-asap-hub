---
id: "project-12-accessibility-audit"
type: "project"
name: "Accessibility audit & remediation"
tier: "tier-3"
priority: "4"
status: "active"
intro: |-
  Multi-year effort: the audit ran in January 2026, remediation continues
  into 2027. Used as the fixture for a chart that spans past and future.
dates:
  started: "2026-01-12"
  target_delivery: "2027-03-31"
  deadline_text: "2027-03-31"
  deadline_type: "soft"
tech_footprint:
  platforms:
    - "iOS"
    - "Android"
    - "Content"
    - "QA"
  qa_effort: "high"
  content_impact: true
stakeholders:
  business_owner: "stakeholder-mary-jackson"
  qa_lead: "stakeholder-jean-bartik"
dependencies:
  upstream:
    - project_or_service: "Design system 3.0"
      team: "Design Systems"
      contact: "stakeholder-hedy-lamarr"
      criticality: "medium"
  downstream:
    - project_or_service: "Public accessibility statement"
      team: "Legal"
      contact: "stakeholder-mary-jackson"
      criticality: "high"
risks_and_criticalities:
  - id: "RISK-01"
    description: "Remediation competes with feature work every quarter"
    severity: "medium"
    mitigation: "Reserve 10% of each sprint"
    owner: "stakeholder-unassigned"
planning_factors:
  team_capacity_needed: "10% of every squad, continuous"
  critical_path: "Audit → prioritised backlog → per-quarter remediation"
jira:
  request: "NIMBUS-0980"
  epics:
    - "NIMBUS-0981"
    - "NIMBUS-0982"
todos:
  - id: "todo-project-12-accessibility-audit-1-1788000070"
    text: "Publish the Q4 remediation scorecard"
    deadline: "2026-12-19"
    done: false
todos_history:
  - id: "todo-project-12-accessibility-audit-2-1785000000"
    text: "Run the audit with the external agency"
    deadline: "2026-01-30"
    done: true
    completed_at: "2026-01-30 18:00"
---

## Notes

Timeline fixture: one task entirely in the past and one beyond the configured
chart end date.
