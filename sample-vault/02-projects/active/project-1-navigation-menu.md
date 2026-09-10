---
id: "project-1-navigation-menu"
type: "project"
name: "Navigation menu — second level"
tier: "tier-1"
priority: "1"
status: "active"
blocked_reason: ""
intro: |-
  Rollout of the second level of the navigation menu on all markets.
  Coordination with the "Menu API" backend team is the critical path:
  see https://confluence.example.com/display/NAV/Menu-API for the contract.
dates:
  started: "2026-08-24"
  soft_deadline: "2026-11-06"
  mandatory_deadline: "2026-11-20"
  target_delivery: "2026-11-14"
  deadline_text: "2026-11-14"
  deadline_type: "hard"
tech_footprint:
  platforms:
    - "iOS"
    - "Android"
    - "Backend (dev)"
    - "Backend (config)"
    - "Content"
    - "QA"
  qa_effort: "high"
  content_impact: true
stakeholders:
  business_owner: "stakeholder-mary-jackson"
  tech_lead: "stakeholder-ada-lovelace"
  delivery_manager: "stakeholder-unassigned"
  qa_lead: "stakeholder-margaret-hamilton"
dependencies:
  upstream:
    - project_or_service: "Menu API v2"
      team: "Backend Platform"
      contact: "stakeholder-grace-hopper"
      criticality: "high"
    - project_or_service: "CDN cache invalidation"
      team: "Infrastructure"
      contact: "stakeholder-alan-turing"
      criticality: "medium"
  downstream:
    - project_or_service: "Seasonal campaign landing"
      team: "Marketing Tech"
      contact: "stakeholder-mary-jackson"
      criticality: "low"
risks_and_criticalities:
  - id: "RISK-01"
    description: "Menu API v2 contract not frozen yet"
    severity: "high"
    mitigation: "Weekly sync with the backend platform team"
    owner: "stakeholder-ada-lovelace"
  - id: "RISK-02"
    description: "Translations for 12 markets arrive late"
    severity: "medium"
    mitigation: "Ship English fallback, translate incrementally"
    owner: "stakeholder-mary-jackson"
  - id: "RISK-03"
    description: "Older Android devices lose the scroll position"
    severity: "low"
    mitigation: "Cap the menu depth on API level < 26"
    owner: "stakeholder-katherine-johnson"
planning_factors:
  team_capacity_needed: "2 iOS + 2 Android + 1 backend, ~6 weeks"
  critical_path: "Menu API v2 → client integration → QA regression"
jira:
  request: "NIMBUS-1042"
  epics:
    - "NIMBUS-1043"
    - "NIMBUS-1051"
confluence:
  - "https://confluence.example.com/display/NAV/Menu-API"
  - "https://confluence.example.com/display/NAV/Rollout-plan"
figma:
  - "https://www.figma.com/design/aaaa1111/Navigation-menu"
  - "https://www.figma.com/design/aaaa2222/Menu-motion"
todos:
  - id: "todo-project-1-navigation-menu-1-1788000000"
    text: "Confirm the API contract with the backend platform team"
    deadline: "2026-09-18"
    done: false
  - id: "todo-project-1-navigation-menu-2-1788000001"
    text: "Ask design for the empty-state of the third level"
    deadline: ""
    done: false
todos_history:
  - id: "todo-project-1-navigation-menu-3-1787000000"
    text: "Kick-off with both mobile squads"
    deadline: "2026-08-26"
    done: true
    completed_at: "2026-08-26 17:40"
---

## Notes

Phase 1 (single level) shipped in June. This card only tracks phase 2.
