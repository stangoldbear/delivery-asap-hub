# Delivery plan — Q3/Q4 2026

Timeline source of truth for the dashboard. Each task line is
`<label> :<modifiers>, <start>, <duration|end>`; the label carries the short
project code (`P1`, `P2`, ...) declared in `settings.toml` under
`[project_codes]`. A task with no known code lands in the last tier
("operational") as a stand-alone row.

Modifiers: `crit` (critical path), `active` (in progress), `done` (used here
for time off, rendered in the time-off colour).

```mermaid
gantt
    title Mobile delivery — Q3/Q4 2026
    dateFormat YYYY-MM-DD
    axisFormat %d/%m

    section Backend
    Backend Dev #1 P1 Menu API v2        :crit, active, 2026-08-24, 2026-10-09
    Backend Dev #2 P5 carrier matrix     :active, 2026-09-07, 20d
    Backend Dev #3 P9 payment orchestrator :2026-08-11, 2026-11-05
    Backend Dev #2 P11 checkout hardening :2026-09-28, 12d
    Backend Dev #1 P8 banner config      :2026-09-02, 10d

    section iOS
    iOS Dev #1 P1 menu integration       :crit, active, 2026-09-14, 25d
    iOS Dev #2 P2 durability sheet       :2026-09-21, 2026-11-27
    iOS Dev #3 P3 home modules           :active, 2026-09-01, 30d
    iOS Dev #4 P6 designer name          :2026-09-14, 15d
    iOS Dev #2 P10 delivery estimate     :done, 2026-07-20, 2026-09-12
    iOS Dev #1 P12 a11y audit            :done, 2026-01-12, 2026-02-27
    iOS Dev #1 P12 a11y remediation Q1   :2027-01-11, 2027-03-31

    section Android
    Android Dev #1 P1 menu integration    :crit, active, 2026-09-14, 25d
    Android Dev #2 P2 durability sheet    :2026-09-21, 2026-11-27
    Android Dev #3 P3 home modules        :active, 2026-09-01, 30d
    Android Dev #4 P6 designer name       :2026-09-14, 15d
    Android Dev #2 P5 tracking URL        :2026-10-05, 10d

    section QA & PM
    QA #1 P1 regression                  :2026-10-19, 10d
    QA #2 P3 A/B validation              :2026-10-05, 8d
    QA #1 P2 compliance checklist        :2026-11-16, 8d
    QA #2 time off                       :done, 2026-09-21, 5d
    PM #1 P1 rollout coordination        :active, 2026-09-01, 2026-11-20
    Contractor #7 P4 discovery           :2026-10-12, 5d
    iOS Dev #9 P99 unknown project       :2026-10-26, 4d

    section Operations
    Company all-hands                    :2026-09-25, 1d
    Release freeze — peak season         :crit, 2026-11-23, 2026-12-31
    Team offsite                         :done, 2026-10-15, 2d
```

## How to read it

- **crit** marks the critical path, **active** work in progress.
- Rows whose label prefix matches a member in `[[squads]]` show that person's
  name and role colour; anything else falls back to keyword matching.
