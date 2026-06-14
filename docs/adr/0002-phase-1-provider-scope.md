# Phase 1 Provider Scope

Phase 1 originally prioritized a stable, diagnosable bundle pipeline with YouTube working end to end rather than full provider parity. Bilibili, Xiaohongshu, and local video were allowed to start as skeletons or narrow adapters until their real workflows were deliberately scoped, which prevented early crawler complexity from destabilizing the core bundle contract.

Status update: this ADR is historical. Bilibili, Xiaohongshu, and local video have since moved beyond skeleton status. Local video now has a baseline import, metadata, transcription, optional visual recall, and bundle-readiness path; Bilibili and Xiaohongshu have platform-specific provider workflows described in `docs/current-status.md` and `docs/development-rules.md`.
