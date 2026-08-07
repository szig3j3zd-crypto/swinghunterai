---
name: run-swinghunterai
description: Launch, drive, and screenshot the SwingHunter AI Streamlit dashboard (today's buy/sell candidates); also covers running the data pipeline scripts and the backtest simulator. Use when asked to run, start, launch, test, or screenshot SwingHunter AI, or to verify a UI/rule-engine change actually works end to end.
---

Paths below are relative to the repo root (this directory's great-grandparent,
`SwingHunterAI/`), not to this skill directory.

The interactive surface is a **Streamlit web app** (`ui/dashboard.py`). Drive
it with the Playwright driver in this skill directory (`driver.py`) — there
is no `chromium-cli` in this environment, so this custom driver is the agent
path, not a heredoc.

## Prerequisites

```bash
pip install -r requirements.txt          # includes streamlit
pip install playwright                    # not in requirements.txt - driver-only, dev tool
python -m playwright install chromium      # ~150MB, downloads a headless Chromium build
```

`playwright` is intentionally **not** added to `requirements.txt` — it's only
needed to drive/verify the UI, not to run the app itself.

## Run (agent path): dashboard

1. Launch the dashboard in the background, from the repo root:

   ```bash
   python -m streamlit run ui/dashboard.py --server.port 8501 --server.headless true &
   ```

   `ui/dashboard.py` inserts the repo root into `sys.path` itself at the top
   of the file (`streamlit run` does not add it automatically, and the app's
   absolute imports like `from config.config import ...` need it) — no
   `PYTHONPATH` env var needed.

2. Wait for it to actually serve (don't `sleep` blindly):

   ```bash
   timeout 30 bash -c 'until curl -sf http://localhost:8501 >/dev/null; do sleep 1; done'
   ```

3. Drive it and take a screenshot:

   ```bash
   python .claude/skills/run-swinghunterai/driver.py --direction long --out dashboard.png
   ```

   `driver.py` opens the page, optionally switches to the ショート radio
   button (`--direction short`), clicks 「候補を更新」, waits for the scan
   to finish, screenshots, and prints any browser console errors. Exit code
   is non-zero if the scan didn't finish or the console had errors. A full
   scan of the TSE Prime universe (~1,559 stocks) takes **60-90 seconds** —
   the driver's default `--timeout 300` (seconds) covers this with margin.

4. Stop the server when done (see Gotchas — plain `kill` is unreliable here):

   ```powershell
   Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue |
     Select-Object -ExpandProperty OwningProcess -Unique |
     ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
   ```

## Run (human path): dashboard

```bash
streamlit run ui/dashboard.py
```

Opens a browser tab automatically. Click 「候補を更新」 in the sidebar.
Useless in a headless agent session — use the driver instead.

## Run: data pipeline (CLI scripts, non-interactive)

These don't need a driver — run and check exit code / stdout:

```bash
python scripts/create_stock_master.py      # first run only: build stock_master
python scripts/initialize_stock_data.py    # first run only: ~3y history for all active stocks
python scripts/update_stock_data.py        # daily incremental update
```

## Run: backtest (batch, non-interactive)

`backtest/simulator.py` exposes `run_backtest(df, direction, ...)` per stock;
there's no pre-built CLI entrypoint, so a driving script is written ad hoc.
For anything beyond a handful of stocks, **parallelize** — see Gotchas below,
this is a real ~4x+ wall-clock win and the naive serial loop is slow enough
to matter (roughly 20-55s per stock per direction on 3-10 years of daily
data).

Minimal single-stock smoke script:

```python
from database.stock_price_reader import get_stock_data
from indicators.moving_average import calculate_moving_average
from indicators.volume import calculate_volume_indicators
from backtest.simulator import run_backtest

df = get_stock_data("7203")
df = calculate_moving_average(df)
df = calculate_volume_indicators(df)
trades = run_backtest(df, "long", min_history=100, timeframe="daily")
print(len(trades), trades[:1])
```

## Test

```bash
python -m pytest tests/ --ignore=tests/manual -q
```

`tests/manual/` holds scripts that hit live external APIs (Yahoo/J-Quants) —
not part of the normal automated suite; run individually if needed.

## Gotchas

- **Stopping the background Streamlit process.** `kill %1` / plain
  `taskkill` from git-bash is unreliable on this Windows setup — commands
  either target the wrong process or silently no-op. Use the PowerShell
  `Get-NetTCPConnection` + `Stop-Process` snippet above (via the PowerShell
  tool directly, not `powershell -Command "..."` wrapped inside a bash
  string — nesting that way previously mangled the `-Id` argument into
  something PowerShell couldn't parse).

- **The naive "wait for spinner to disappear" approach is flaky.**
  `st.spinner(...)` around the scan can flash and clear before the actual
  script rerun (which the button click triggers) has finished, so waiting
  for the spinner element's `state="detached"` reports "done" too early and
  the screenshot catches the stale/pre-scan page. `driver.py` instead polls
  for Streamlit's top-right **"Stop"** control (visible while any script run
  is in progress) to disappear — that reliably brackets the whole rerun.

- **`page.wait_for_selector` can't mix `text=` and CSS-attribute selectors
  in one comma-joined string** (e.g. `"[data-testid='stDataFrame'], text=..."`)
  — it throws a parse error on the mixed quoting. Use separate waits/checks
  per condition instead (see how `driver.py` checks for "Stop" via
  `get_by_text(...).count()` rather than one combined selector).

- **`multiprocessing.Pool` with an inline `python -c "..."` script fails on
  Windows** with `AttributeError: module '__main__' has no attribute
  'run_one'`. Windows uses the `spawn` start method, which re-imports the
  worker function in each child process — a function defined in a `-c`
  string isn't importable. Put the worker function and the
  `if __name__ == "__main__":` guard in an actual `.py` file instead. This
  is what makes parallelizing the backtest loop across many stocks
  practical (~87min serial → ~21min with 8 workers over ~100 stocks, in one
  prior run).

- **Terminal encoding.** Japanese output (from prints, or git/PowerShell
  errors) often shows as mojibake in the Bash tool's captured output on
  this Windows setup. Harmless — the underlying files/data are correct
  UTF-8; only the terminal display garbles it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'streamlit'` / `'playwright'` | Not installed yet — see Prerequisites. |
| Driver hangs / times out waiting for "Stop" to disappear | Universe scan (TSE Prime, ~1,559 stocks) genuinely takes 60-90s; pass `--timeout` higher if scanning a larger custom stock list. |
| `curl: (7) Failed to connect` when polling port 8501 | Streamlit hasn't started yet (first launch can take a few seconds) or a stale process is still holding the port from a prior run — stop it first (see Gotchas). |
| Dashboard shows `ModuleNotFoundError: No module named 'config'` (or similar) in its own error page | The `sys.path.insert(...)` bootstrap at the top of `ui/dashboard.py` is missing or was removed — it's what makes the repo root importable without a `PYTHONPATH` env var. This bit a real run once (initial instructions to the user omitted it entirely) before the bootstrap was added; if it regresses, that's the fix. |
