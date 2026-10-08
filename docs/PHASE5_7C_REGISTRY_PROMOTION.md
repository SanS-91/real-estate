# Phase 5.7C — Legal & Infrastructure Preview → Promote Gate

## Purpose
Complete the original Master Phase 4 collection path for Legal and Infrastructure.

Both modules now follow:
Source → Watch/Discovery → Parse → Normalize → Deduplicate → Candidate → Preview → Promote.

## Legal promotion
A Legal candidate can promote only when:
- no review issues remain
- document number is present
- it does not conflict with an existing canonical record

Production IDs are stable and derived from the document number. Candidate-only fields are removed before production.

## Infrastructure promotion
An Infrastructure candidate can promote only when review issues are resolved.

Promotion may:
- apply explicit project field patches
- append a new schedule event
- mark the previous current schedule of the same project + schedule type as superseded
- update the project's current expected completion only from the newly promoted expected-completion schedule

History is never destructively overwritten.

## Workflow
**Legal Infrastructure Candidate Preview Promote**

Inputs:
- module: legal / infrastructure
- mode: preview / promote

Preview is non-mutating.
Promote is explicit and commits only production files for the selected module.

## Master roadmap consequence
With 5.7A, 5.7B and 5.7C complete, all four pillars have a defined collection-to-candidate path and controlled production gate.

Therefore **Master Phase 4 — Source Registry & Auto Data Collection** can be marked complete.

The next work package is **5.8 — Unified Automation & Data Health**, which closes Master Phase 5.
