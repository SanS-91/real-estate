# Phase 5.1 — Compare & Shareable Research

Phase 5.1 extends the Phase 5.0 Research workspace from one subject to a side-by-side comparison of up to three subjects of the same type.

## Comparison modes
- Project vs Project
- Region vs Region
- Developer vs Developer

## URL contract
- Single or multiple selections are stored in `?type=<type>&ids=id1,id2,id3`.
- Legacy `?id=<id>` remains readable.
- The resulting URL can be bookmarked or copied with the Share action.

## Comparison logic
- Counts are derived from each subject's canonical Market / Infrastructure / Legal / recent-activity relationships.
- Shared infrastructure is the intersection of explicit canonical infrastructure links.
- Shared legal topics are the intersection of canonical research-topic links.
- Macro remains a common context layer and is never used as a subject score.
- No synthetic ranking, score, inferred ASP, sales, absorption or legal applicability is created.
