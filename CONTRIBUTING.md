# Contributing to DealerStudio

The first goal is dependable, editable vehicle photography. A contribution should preserve the actual vehicle, make uncertain output easier to review, or make the local workflow more reliable.

## Development

Use Python 3.13 and uv:

```powershell
uv sync --frozen
uv run python launch.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Unit tests use synthetic processing fixtures and check the frozen dataset's integrity. Actual AI evaluation is separate: install the verified model, then run `uv run python -m benchmark.run --output benchmark/results/a-new-run`. Read the failed examples and compare results visually. Do not improve scores by quietly changing frozen annotations. If labels genuinely need correction, document it as a new dataset version and retain the previous results.

## Boundaries worth preserving

- Processing must work locally after explicit setup. No cloud fallback, accounts or telemetry.
- Keep source photos intact. Never invent unseen parts, repair material condition details or change paint color through generative processing.
- Keep the UI responsive and memory bounded; respect cancellation and isolate per-photo failures.
- Treat model code, weights, fonts and assets as separately licensed components. Include exact sources, versions and required notices for new dependencies or weights.
- Distinguish synthetic tests, actual inference and manual visual review in reports.
- Give users actionable errors and useful manual controls when automation is unreliable.

Focused improvements to masks, grounding controls, export behavior, accessibility and large-image responsiveness are welcome. Include the concrete before/after behavior and relevant validation in a pull request. New fixtures must carry provenance and licenses permitting redistribution.

Original code contributions are Apache-2.0. Dataset and photo contributions must retain their independently stated licenses; see `benchmark/README.md`.
