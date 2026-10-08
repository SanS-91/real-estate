# Phase 5.6A — Project Detail Navigation

## Goal
Improve usability of long Project Detail pages while keeping the existing information architecture.

## Navigation
A sticky in-page navigation is added after the project header:

- Tổng quan
- Giá & lịch sử
- Tin tức
- Pháp lý
- Hạ tầng
- Phân kỳ

Each item scrolls to the corresponding section. The active section is highlighted using IntersectionObserver while the user scrolls.

## URL behavior
Section navigation updates the URL hash, so a specific section can be copied or revisited directly without changing the project-detail route.

Example:
`market.html?view=project-detail&id=mizuki-park#project-pricing`

## UX principles
- drawer remains the quick view
- full Project Detail remains the deep-dive surface
- sticky navigation is horizontally scrollable on small screens
- section anchors account for the sticky navigation offset
- no data semantics are changed in this phase
