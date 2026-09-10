---
id: "project-5-carrier-tracking"
type: "project"
name: "Carrier tracking URL"
tier: "tier-2"
priority: "2"
status: "active"
intro: "Show the carrier tracking URL instead of the raw tracking number in the order detail."
dates:
  started: "2026-09-07"
  target_delivery: "2026-11-30"
  deadline_text: "30/11/2026"
  deadline_type: "soft"
tech_footprint:
  platforms:
    - "iOS"
    - "Android"
    - "Backend (dev)"
  qa_effort: "low"
  content_impact: false
stakeholders:
  tech_lead: "stakeholder-grace-hopper"
  qa_lead: "stakeholder-margaret-hamilton"
dependencies:
  downstream:
    - project_or_service: "Customer care console"
      team: "Care Tools"
      contact: "stakeholder-mary-jackson"
      criticality: "medium"
risks_and_criticalities:
  - id: "RISK-01"
    description: "Two carriers still return a tracking number only"
    severity: "low"
    mitigation: "Fall back to the number when the URL is empty"
    owner: "stakeholder-grace-hopper"
jira:
  request: "NIMBUS-1201"
confluence:
  - "https://confluence.example.com/display/ORD/Carrier-matrix"
todos:
  - id: "todo-project-5-carrier-tracking-1-1788000030"
    text: "Get the URL template from the two remaining carriers"
    deadline: "2026-10-02"
    done: false
---

## Notes

Backend change is small; most of the effort is the carrier matrix.
