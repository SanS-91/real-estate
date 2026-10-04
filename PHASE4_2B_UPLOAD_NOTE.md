# Phase 4.2B Upload Note

This patch is additive to the stable v7.2.1 website.

It intentionally contains **no HTML or `assets/` frontend files** and does not replace the project README.

After upload, do not expect the visible website to change. The only new user-facing GitHub feature is the **Macro Candidate Collector** workflow under the repository Actions tab.

The scheduled workflow has read-only repository permissions and uploads candidate artifacts; it does not publish to `data/processed` or modify the website.
