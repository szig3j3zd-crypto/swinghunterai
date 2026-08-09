"""
株探し Streamlit dashboard driver.

Drives the running dashboard with a headless browser: opens it, selects a
direction, clicks "候補を更新" (scan), waits for the scan to finish, and
saves a screenshot. Requires the dashboard to already be running
(see SKILL.md for the launch command) - this script does not start it.

Usage:
    python driver.py [--url http://localhost:8501] [--direction long|short]
                      [--out dashboard.png] [--timeout 300]

Exit code is non-zero if the page never rendered or the scan never finished.
"""

import argparse
import sys

from playwright.sync_api import sync_playwright


def run(url, direction, out_path, timeout_s):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )

        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("text=株探し", timeout=15000)

        if direction == "short":
            page.click("text=ショート（売り）")

        page.click("text=候補を更新")

        # Streamlit shows a "Stop" control top-right while a script run is in
        # progress. Wait for it to disappear rather than for the st.spinner
        # element - the spinner can flash and disappear before the actual
        # script run (which triggers a rerun) finishes, giving a false "done".
        finished = False
        for _ in range(max(timeout_s // 5, 1)):
            page.wait_for_timeout(5000)
            if page.get_by_text("Stop", exact=True).count() == 0:
                finished = True
                break

        page.screenshot(path=out_path)
        browser.close()

        print(f"screenshot saved: {out_path}")
        print(f"scan finished: {finished}")
        print(f"console errors: {console_errors}")

        if not finished or console_errors:
            return 1

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--direction", choices=["long", "short"], default="long")
    parser.add_argument("--out", default="dashboard.png")
    parser.add_argument("--timeout", type=int, default=300, help="seconds to wait for the scan")
    args = parser.parse_args()

    sys.exit(run(args.url, args.direction, args.out, args.timeout))
