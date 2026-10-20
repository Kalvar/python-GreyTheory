"""Bundle computed synthetic previews into JavaScript for direct file:// opening."""

import json
from pathlib import Path

from .backend import Backend
from .scenarios import SCENARIOS


def build(output=None):
    backend = Backend()
    config = backend.config()
    config["catalog"] = [item for item in config["catalog"] if item["id"].startswith(("doe:", "synthetic:"))]
    config["unavailable"] = []  # Never publish local filenames or validation failures.
    config["mode"] = "preview"
    data = {}
    for item in config["catalog"]:
        dataset = backend.request("/api/load", {"id": item["id"]})
        dataset["id"] = "preview:" + item["id"]
        data[item["id"]] = dataset
    results = {}
    for key, dataset in data.items():
        source = backend.request("/api/load", {"id": key})
        results[dataset["id"]] = backend.request(
            "/api/analyze",
            dict(
                dataset=source["id"],
                features=source["defaults"],
                target=source["targets"][0] if source["targets"] else None,
                components=2,
            ),
        )
    scenes = {key: backend.request("/api/scenario", dict(scenario=key)) for key in SCENARIOS}
    handwriting = backend.request("/api/handwriting", dict(demo=True, method="pca"))
    payload = dict(config=config, datasets=data, analysis=results, scenarios=scenes, handwriting=handwriting)
    output = Path(output or Path(__file__).resolve().parent / "static" / "preview-data.js")
    output.write_text(
        "// Generated synthetic previews; computed by Python, not live browser calculations.\nwindow.GREY_PREVIEW="
        + json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace(
            "<", "\\u003c"
        )
        + ";\n",
        encoding="utf-8",
    )
    return output


if __name__ == "__main__":
    print(build())
