# Working agreement for this repo

- **Before starting a new problem and before every commit:** update `docs/PROJECT_HISTORY.md` (dated entry: problem, approach, what changed/failed, result)
  and keep `PROJECT_STATUS.md` (current state, limits, next tasks) and `README.md` (how to run, what's left) consistent with it.
- Record architecture/dependency choices in `docs/decisions/`, experiments in `docs/experiments/`, data/licences in `docs/DATA_SOURCES.md`.
- Don't claim musical quality without a test or listening evidence. Keep the demo working (`python -m vocal2chord demo`) and `python -m pytest -q` green.
- Commit on the designated development branch; no PR unless asked.
