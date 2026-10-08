# Phase 5.7B — Infrastructure Structured Candidate Collector

## Purpose
Close the Infrastructure collection gap identified by the master roadmap.

The existing registry watcher detects changed pages and new official links. Phase 5.7B converts newly discovered official updates into structured Infrastructure candidates for review.

## Parsed changes
The collector looks for objective fields only:
- matched infrastructure project
- announcement date
- expected completion / operation-start milestone
- progress percentage
- total investment
- operational / under-construction status cues
- official source and provenance

## History principle
Schedule changes are append-only.

A newly parsed completion or operation milestone does not overwrite the current schedule in production. It becomes a candidate schedule event for review. The later promotion stage is responsible for marking the prior current schedule as superseded when appropriate.

## Project patch principle
Current project fields such as:
- current_progress_percent
- current_total_investment
- status

are emitted as a proposed patch with explicit from/to differences.

The collector never mutates the production project registry.

## Matching and review
Projects are matched against controlled aliases for the tracked infrastructure registry.
If project identity or announcement date cannot be resolved, the candidate is flagged for review rather than silently inferred.

## Automation
Workflow: **Infrastructure Candidate Collector**

The workflow:
1. refreshes the shared registry watch,
2. consumes newly discovered infrastructure official links,
3. parses structured candidate changes,
4. uploads review artifacts.

Production Infrastructure data is never written by this workflow.

## Next
Phase 5.7C adds shared Preview → Promote gates for reviewed Legal and Infrastructure candidates.
