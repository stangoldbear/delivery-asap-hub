---
id: "project-3-home-redesign"
type: "project"
name: "Home page redesign"
tier: "tier-1"
priority: "3"
status: "active"
intro: "Full rebrand of the home page, including the top banner and the new editorial modules."
dates:
  started: "2026-09-01"
  target_delivery: "2026-10-20"
  deadline_text: "mid October"
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
  tech_lead: "stakeholder-nikola-tesla"
dependencies:
  upstream:
    - project_or_service: "Design system 3.0"
      team: "Design Systems"
      contact: "stakeholder-hedy-lamarr"
      criticality: "medium"
  downstream:
    - project_or_service: "Push campaign templates"
      team: "CRM"
      contact: "stakeholder-mary-jackson"
      criticality: "low"
risks_and_criticalities:
  - id: "RISK-01"
    description: "A/B test window overlaps with the peak season freeze"
    severity: "medium"
    mitigation: "Run the test two weeks earlier"
    owner: "stakeholder-nikola-tesla"
planning_factors:
  team_capacity_needed: "2 iOS + 2 Android, ~5 weeks"
  critical_path: "Design system tokens → module build → A/B test"
jira:
  request: "NIMBUS-1120"
  epics:
    - "NIMBUS-1121"
confluence:
  - "https://confluence.example.com/display/HOME/Redesign-brief"
figma:
  - "https://www.figma.com/design/cccc1111/Home-redesign"
todos:
  - id: "todo-project-3-home-redesign-1-1788000020"
    text: "Review the copy deck with marketing:\nthe hero claim is still the old one.\nReference: https://confluence.example.com/display/HOME/Copy \"final v3\""
    deadline: "2026-09-22"
    done: false
todos_history:
  - id: "todo-project-3-home-redesign-2-1787000020"
    text: "Freeze the module list for release 8.4"
    deadline: "2026-09-04"
    done: true
    completed_at: "2026-09-04 11:15"
  - id: "todo-project-3-home-redesign-3-1787000021"
    text: "Align with the web team on the banner ratio"
    deadline: ""
    done: true
    completed_at: "2026-08-29 09:02"
---

## Notes

The A/B test needs at least two full weeks of traffic.
