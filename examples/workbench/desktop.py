"""Open the bundled HTML in a native window, or execute an exported request. No server."""

import argparse
import json
from pathlib import Path
import sys

from .backend import Backend

ENTRY = Path(__file__).resolve().parent / "index.html"


class Bridge:
    def __init__(self):
        self._backend = Backend()

    def save_result(self, value, name):
        import webview

        paths = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename=Path(name).name)
        if not paths:
            return None
        path = Path(paths[0] if isinstance(paths, (list, tuple)) else paths)
        path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"
        )
        return str(path)

    def config(self):
        return self._backend.config()

    def request(self, endpoint, options):
        return self._backend.request(endpoint, options)


def execute_file(path, output=None):
    path = Path(path)
    if path.stat().st_size > 45 * 1024 * 1024:
        raise ValueError("運算請求超過 45 MiB。")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("format") != "greytheory-request-v1":
        raise ValueError("不是 GreyTheory 匯出的運算請求。")
    backend = Backend()
    body = document["body"].copy()
    dataset = None
    if document["endpoint"] == "/api/analyze":
        dataset = backend.request("/api/load", document["source"])
        body["dataset"] = dataset["id"]
    result = backend.request(document["endpoint"], body)
    if document["endpoint"] == "/api/load":
        dataset = result
    response = dict(
        format="greytheory-result-v1",
        endpoint=document["endpoint"],
        options=body,
        result=result,
        dataset=dataset,
        source=document.get("source"),
    )
    output = Path(output) if output else path.with_name(path.stem + ".result.json")
    output.write_text(
        json.dumps(response, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output and not args.request:
        parser.error("--output requires --request")
    if args.request:
        try:
            print(execute_file(args.request, args.output).resolve())
        except (ValueError, OSError, TypeError, KeyError) as error:
            parser.exit(2, f"Cannot run request: {error}\n")
        return 0
    try:
        import webview
    except ImportError:
        parser.exit(2, 'Desktop UI needs the workbench extra. Run: python -m pip install ".[workbench]"\n')
    # Load project HTML directly into the native renderer; no URL or HTTP server.
    bridge = Bridge()
    webview.settings["ALLOW_DOWNLOADS"] = True
    bridge._window = webview.create_window(
        "GreyTheory Workbench",
        url=ENTRY.as_uri() + "#desktop",
        js_api=bridge,
        width=1400,
        height=950,
        min_size=(800, 600),
        background_color="#0b101a",
    )
    webview.start(http_server=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
