# FYP Development Records

This folder separates four different kinds of evidence so implementation work, research observations, and experimental results do not get mixed together.

## Files

- `PROJECT_LOG.md` — chronological narrative of major milestones, blockers, architectural decisions, and next steps.
- `CHANGELOG.md` — code/version changes only. Update this whenever `test_connection.py` changes.
- `OBSERVATIONS.md` — research findings and lessons, using stable IDs such as `OBS-020`.
- `EXPERIMENTS.md` — experiment batches, model/configuration used, number of runs, and quantitative results.

## Update rule from now on

After every meaningful change:

1. Add the code change to `CHANGELOG.md`.
2. If the change came from a meaningful behaviour/failure, add or update an entry in `OBSERVATIONS.md`.
3. If a batch of runs was completed, add its results to `EXPERIMENTS.md`.
4. Add only major milestones or methodological decisions to `PROJECT_LOG.md`.
5. Keep `run_events.jsonl` as the machine-readable source of truth for individual run/action data.

Do not manually edit `run_events.jsonl`.

## Recommended Git practice

Commit the code and documentation together when a milestone is reached, for example:

`git commit -am "v0.2.2 fix map decoding and key telemetry"`

This makes the written history traceable to the exact code version that produced each experiment.
