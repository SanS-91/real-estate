# Phase 5.7A — Legal Structured Candidate Collector

## Purpose
Close the Legal collection gap identified by the master roadmap.

The existing registry watcher detects changed pages and new official links. Phase 5.7A adds the next stage:
official legal page → parser → normalized candidate → review artifact.

## Parsed fields
The collector only extracts objective metadata:
- document number
- title
- document type
- issued date
- effective date
- issuing agency
- controlled legal topics
- official URL
- source provenance

It does not invent a legal summary, legal impact, or key changes.

## Review policy
Every parsed candidate is marked review-required.
Missing agency/topic metadata is surfaced as a review issue rather than inferred silently.

## Deduplication
Candidates are checked against the curated Legal registry using:
- document number
- official URL

Existing records are classified as unchanged or existing-review.
Only new records are written to candidate staging.

## Automation
Workflow: **Legal Candidate Collector**

The workflow:
1. refreshes the existing Legal/Infrastructure registry watch,
2. takes newly discovered Legal official links,
3. parses them into Legal candidates,
4. uploads candidate artifacts.

Production Legal data is never written by this workflow.

## Next
Phase 5.7B adds the equivalent structured candidate flow for Infrastructure.
After both collectors are stable, Phase 5.7C adds explicit Preview → Promote gates for reviewed Legal and Infrastructure candidates.
