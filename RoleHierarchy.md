# CampusTrace — Project Overview

## What We're Building

**CampusTrace** is a graph-based, risk-weighted contact tracing and infection control platform designed for institutional (college campus) environments. It moves beyond the binary exposure alerts used by apps like Aarogya Setu and TraceTogether, replacing them with graded risk scores, disease-agnostic configuration, and privacy-preserving aggregation — while directly supporting administrative decision-making (isolation capacity, outbreak clusters) rather than only notifying individuals.

The system uses real institutional data — class timetables, batch/lab enrollment, and faculty teaching schedules — to build a **contact graph** automatically, without requiring students to manually check in every day. Health reporting (by students or faculty) triggers forward and backward contact tracing over this graph, producing risk-graded alerts with relevant symptoms and precautions attached.

## Problem Statement

Existing contact tracing applications were built as emergency, single-disease, nation-scale tools that produce binary exposure alerts, rely on centralized data models, and lack integration with institutional response capacity. This results in poor daily engagement, alert fatigue, and systems that become obsolete after a single outbreak. There is a need for a **disease-agnostic, privacy-preserving contact tracing system for closed institutional environments** that generates graded, actionable risk signals and directly supports administrative infection-control decisions rather than isolated individual alerts.

## Why a College Campus

- Bounded, well-structured population (timetables, room allocations, batch enrollment already exist as data)
- Natural daily usage — students/faculty already interact with timetables/attendance, so passive presence logging fits existing habits instead of competing for attention
- Rich enough for meaningful sub-network analysis (divisions, batches, labs, faculty) without needing external hardware (no BLE beacons, no GPS)

## Scope: Starting Point and Growth Path

- **Phase 1 (pilot):** One real division (Second Year CS-C, BTech Computer Engineering) — the timetable data used is real, contributed by a team member
- **Phase 2:** A second division is introduced once the single-division pipeline (presence generation, tracing, risk scoring) is verified — this is when the faculty cross-division bridging feature becomes demonstrable, since a bridge requires at least two divisions to connect
- Architecture is designed so scaling to more divisions requires no schema changes — `division_id` is a foreign key throughout

## Explicit Non-Goals (for this project's scope)

- No Bluetooth/BLE proximity sensing or GPS — all contact data is derived from structured institutional records (timetables, enrollment, health reports)
- No medical diagnosis — the self-assessment interface is a rule-based triage helper, not a diagnostic tool
- No production-grade infrastructure (no Docker, no cloud deployment, no external third-party APIs) — kept self-contained and demo-runnable locally

## Tech Stack (summary — see `methodology.md` for full rationale)

- **Frontend:** React (kept simple — no additional UI framework layered on top)
- **Backend:** Flask (Python)
- **Database:** MySQL
- **Core algorithms:** Written from scratch in Python (no NetworkX or equivalent shortcut libraries) — Graph, BFS/DFS, Union-Find, priority queues/heaps, since this project is centered on demonstrating DSA and algorithmic logic explicitly

## Team

Four members, one shared foundation, then role-family ownership:

| Member | Owns |
|---|---|
| Person 1 | Foundation: schema, auth/RBAC, core DSA/algorithm modules |
| Person 2 | Student module (registration, self-report, self-assessment, alerts) |
| Person 3 | Course Faculty + Class Teacher module (absence flagging, division view) |
| Person 4 | Health Admin + Institute Admin module (dashboards, Disease KB, capacity, timetable entry) |

See `role_hierarchy.md` for full role/permission detail and `methodology.md` for the phased build plan.