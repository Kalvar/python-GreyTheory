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
        for language in ("en", "zh-TW", "ja"):
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
            page.goto(
                (root / "examples/workbench/index.html").as_uri() + f"?lang={language}", wait_until="load"
            )
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
                page.wait_for_timeout(150)
                page.screenshot(
                    path=str(output / name.replace(".png", f".{language}.png")), animations="disabled"
                )

            capture("workbench-doe.png", "#dataPanel")
            page.locator('[data-help="start"]').click()
            page.wait_for_selector("#manualDialog[open]")
            page.screenshot(path=str(output / f"workbench-manual.{language}.png"), animations="disabled")
            page.locator("#closeManual").click()
            page.locator('[data-tab="lab"]').click()
            for scenario, name in [
                ("routes", "workbench-routes.png"),
                ("optimization", "workbench-optimization.png"),
                ("research", "workbench-research.png"),
                ("art", "workbench-art.png"),
            ]:
                page.locator("#scenario").select_option(scenario)
                if scenario == "research":
                    page.locator("#scenarioParams-pca_mode").select_option("on")
                page.locator("#runScenario").click()
                page.wait_for_function(
                    "() => document.getElementById('scenarioTables').querySelector('table')!==null"
                )
                capture(name, "#labPanel")
                if scenario == "optimization":
                    before = page.evaluate("JSON.stringify(scenarioResult)")
                    for stage in ("calibration", "search", "pareto", "stability"):
                        page.locator(f'[data-stage="{stage}"]').click()
                        assert page.locator("#optimizationPlot svg").count() == 1
                        assert page.evaluate("JSON.stringify(scenarioResult)") == before
                    page.locator('[data-help="scenario"]').click()
                    assert page.locator("#help-optimization").is_visible()
                    page.locator("#closeManual").click()
                if scenario == "research":
                    for tool in ("ginn", "fginn", "grey_fuzzy_gpr"):
                        page.locator("#scenarioParams-tool").select_option(tool)
                        page.locator("#runScenario").click()
                        page.wait_for_function(
                            "tool => scenarioResult && scenarioResult.parameters.tool === tool", arg=tool
                        )
                    capture("workbench-research-gpr.png", "#labPanel")
                    page.locator('[data-help="scenario"]').click()
                    assert page.locator("#help-research").is_visible()
                    page.locator("#closeManual").click()
                # Changing language must not reset a fitted result or its inputs.
                if scenario == "art":
                    before = page.evaluate("JSON.stringify(scenarioResult)")
                    for other in ("en", "zh-TW", "ja", language):
                        page.locator("#language").select_option(other)
                        page.wait_for_function("lang => window.greyLanguage.current === lang", arg=other)
                        assert page.locator("#scenario").input_value() == "art"
                        assert page.evaluate("JSON.stringify(scenarioResult)") == before
                    page.locator('[data-help="scenario"]').click()
                    assert page.locator("#help-art").is_visible()
                    page.locator('[data-manual-section="files"]').click()
                    assert page.locator("#help-files").is_visible()
                    page.locator("#closeManual").click()

            page.locator("#scenarioParams-art_source").select_option("ai_images")
            page.locator("#runScenario").click()
            page.wait_for_selector(".art-image-frame img")
            page.wait_for_function(
                "() => [...document.querySelectorAll('.art-image-frame img')].every(image=>image.complete && image.naturalWidth>0)"
            )
            page.locator('#scenarioDiagram input[type="checkbox"]').uncheck()
            page.locator(".art-image-frame svg").wait_for(state="hidden")
            page.locator('#scenarioDiagram input[type="checkbox"]').check()
            page.locator(".art-image-frame svg").wait_for(state="visible")
            capture("workbench-art-image.png", "#labPanel")
            page.locator('[data-tab="images"]').click()
            page.locator("#imageDemo").click()
            page.wait_for_selector(".image-card")
            capture("workbench-handwriting.png", "#imagesPanel")
            page.goto(
                (root / "data/demo/artwork/review/index.html").as_uri() + f"?lang={language}",
                wait_until="load",
            )
            page.wait_for_selector("#observedOverlay rect")
            page.wait_for_function(
                "() => [...document.querySelectorAll('#viewer img')].every(image=>image.complete && image.naturalWidth>0)"
            )
            page.set_viewport_size({"width": 1360, "height": 1480})
            page.locator("#viewer").evaluate("node => node.scrollIntoView({block:'start'})")
            page.locator("#viewer").screenshot(
                path=str(output / f"workbench-art-review.{language}.png"), animations="disabled"
            )
            if errors or requests:
                raise RuntimeError(f"Screenshot validation failed: {errors}; HTTP requests: {requests}")
            page.close()
        browser.close()
    print(f"30 localized synthetic-only screenshots: {output}")


if __name__ == "__main__":
    main()
