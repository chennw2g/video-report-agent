# Plan-Guided Screenshot Candidates

Candidate screenshot collection should use agent-guided intent rather than full high-frequency coverage by
default. The `video-bundle-prep` workflow first collects text evidence, classifies the source, writes
`visual_selection_plan.json`, and then calls `extract-frames --plan visual_selection_plan.json`.

With a plan, `--max-screenshots 0` and `--max-candidate-screenshots 0` mean no cap on the planned
coarse+anchor candidate set, not a request to extract every high-frequency fixed interval. The current
planned coarse intervals are `low=30s`, `medium=15s`, and `high=8s`; semantic anchors from the plan add
targeted frames around important timestamps. A positive cap remains an explicit performance or storage
tradeoff. When it truncates coverage, `slides.json.extraction` records the cap and diagnostics include
`VISUAL_COVERAGE_TRUNCATED`.

Report image volume is still a separate concern. `video-bundle-prep` should keep `select-evidence
--max-images` and `prepare-report --max-images` selective for `report.input.json`, while the bundle retains
the planned candidate evidence. Re-running frame extraction refreshes `slides.json`, removes stale candidate
screenshots from earlier passes, and prevents old screenshot records from being carried forward in
`manifest.json`. Final quick/deep report mode affects `video-report` output depth and rendered image volume,
not bundle candidate extraction policy.
