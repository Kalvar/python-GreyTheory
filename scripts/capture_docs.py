"""Capture public, synthetic-only workbench screenshots; optional Playwright dependency.

Run from the repository: python scripts/capture_docs.py
Use --browser-executable /path/to/chrome when Playwright browsers are not installed.
"""

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-executable", type=Path)
    args = parser.parse_args(argv)
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[1]
    output = root / "docs/images"
    with sync_playwright() as playwright:
        options = {"headless": True}
        if args.browser_executable:
            options["executable_path"] = str(args.browser_executable)
        browser = playwright.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1360, "height": 920}, device_scale_factor=1)
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                requests.append(request.url) if request.url.startswith(("http://", "https://")) else None
            ),
        )
        page.goto((root / "examples/workbench/index.html").as_uri(), wait_until="load")
        page.wait_for_function("() => typeof dataset !== 'undefined' && dataset && dataset.rows===15")
        page.locator("#analyze").click()
        page.wait_for_selector(".rank-row")

        def capture(name, section):
            height = (
                1100
                if "handwriting" in name
                else 1060
                if any(key in name for key in ("routes", "art"))
                else 920
            )
            page.set_viewport_size({"width": 1360, "height": height})
            page.locator(section).evaluate("node => node.scrollIntoView({block:'start'})")
            page.screenshot(path=str(output / name), animations="disabled")

        capture("workbench-doe.png", "#dataPanel")
        page.locator('[data-help="start"]').click()
        page.wait_for_selector("#manualDialog[open]")
        page.screenshot(path=str(output / "workbench-manual.png"), animations="disabled")
        page.locator("#closeManual").click()
        page.locator('[data-tab="lab"]').click()
        for scenario, name in [("routes", "workbench-routes.png"), ("art", "workbench-art.png")]:
            page.locator("#scenario").select_option(scenario)
            page.locator("#runScenario").click()
            page.wait_for_function(
                "() => document.getElementById('scenarioTables').querySelector('table')!==null"
            )
            capture(name, "#labPanel")
        page.locator('[data-tab="images"]').click()
        page.locator("#imageDemo").click()
        page.wait_for_selector(".image-card")
        capture("workbench-handwriting.png", "#imagesPanel")
        if errors or requests:
            raise RuntimeError(f"Screenshot validation failed: {errors}; HTTP requests: {requests}")
        browser.close()
    print(f"5 synthetic-only screenshots: {output}")


if __name__ == "__main__":
    main()
