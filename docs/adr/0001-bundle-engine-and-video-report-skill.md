# Bundle Engine, Prep Skill, Report Skill, And Plugin Boundary

We separate the Python bundle engine from Codex skills and the future plugin packaging surface. The bundle engine owns provider collection, normalization, diagnostics, manifest writing, retained working media, and frame extraction without calling an LLM or writing the final report.

The Codex workflow is split into two skill responsibilities. `video-bundle-prep` prepares evidence: it invokes the bundle engine, inspects stage-1 text evidence, classifies the video, chooses a visual policy, extracts frames, checks readiness, and writes `report.input.json`. `video-report` writes the final user-facing report from a prepared bundle or `report.input.json`. For user convenience, `video-report` may call the prep workflow automatically when the user gives it a raw video link or local file, but this is orchestration rather than a merged responsibility.

The eventual project packaging surface should be a Codex plugin containing both skills, shared documentation, helper scripts, and bundle-engine entrypoints. The plugin should not collapse provider collection, evidence preparation, and final report writing into one opaque AI summarizer. The plugin shell is deliberately deferred until quick/deep report structure and visual output design are stable; until then, the project is maintained as two skills plus the Python CLI.

Semantic video-type classification belongs in Codex after stage-1 text evidence is available, not in provider keyword rules; this keeps platform tooling and report reasoning from collapsing into one opaque pipeline.
