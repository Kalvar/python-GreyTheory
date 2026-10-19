"""Toy XRF count maps with known mixing weights and independent simulated maps."""

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline

from .._validation import integer
from ..analysis import GreyFeatureSelector, GreyPCA
from ..io.bruker import read_spx
from ..spectroscopy import PoissonPCA, element_lines
from ._report import plotting, report, table, write_csv, write_json


@dataclass
class SyntheticXRF:
    energy_keV: np.ndarray
    counts: np.ndarray
    mixing_weights: np.ndarray
    map_ids: np.ndarray
    positions: np.ndarray
    material_ids: np.ndarray
    elements: tuple
    map_shape: tuple
    seed: int


def make_xrf_data(*, seed=7, map_shape=(6, 6), n_maps=4, n_channels=1024):
    """Gaussian characteristic lines + continuum + Poisson noise, not a full XRF simulator.

    Mixing weights control line-template amplitudes; they are not calibrated wt%.
    Each map has independently sampled weights, exposure, and counts.
    """
    seed = integer(seed, "seed", minimum=0)
    n_maps = integer(n_maps, "n_maps", minimum=2)
    n_channels = integer(n_channels, "n_channels", minimum=512)
    height, width = (integer(value, "map dimension", minimum=3) for value in map_shape)
    generator = np.random.default_rng(seed)
    energy = np.arange(n_channels) * 0.02
    elements = (("Ca", 20), ("Fe", 26), ("Cu", 29), ("Zn", 30))
    templates = []
    for _, number in elements:
        profile = np.zeros(n_channels)
        for line in element_lines(number, energy_range=(0.5, float(energy[-1]))):
            sigma = 0.045 + 0.006 * np.sqrt(line["energy_keV"])
            peak = np.exp(-0.5 * ((energy - line["energy_keV"]) / sigma) ** 2)
            profile += line["relative_rate"] * peak / peak.sum()
        templates.append(profile / profile.sum())
    templates = np.asarray(templates)
    recipes = np.array([[.85, .09, .03, .03], [.08, .84, .04, .04], [.08, .08, .62, .22]])
    y, x = np.mgrid[:height, :width]
    groups = np.minimum(x.ravel() * 3 // width, 2)
    positions = np.column_stack((y.ravel(), x.ravel()))
    continuum = 12 + 55 * np.exp(-energy / 5) + 10 * np.exp(-0.5 * ((energy - 12) / 3) ** 2)
    weights, counts = [], []
    for _ in range(n_maps):
        mixture = recipes[groups] + generator.uniform(0, .06, (height * width, 4))
        mixture /= mixture.sum(axis=1, keepdims=True)
        exposure = generator.lognormal(0, .06, (height * width, 1))
        expected = exposure * (continuum + 70000 * mixture @ templates)
        weights.append(mixture)
        counts.append(generator.poisson(expected).astype(np.uint32))
    return SyntheticXRF(energy, np.vstack(counts), np.vstack(weights),
                        np.repeat(np.arange(n_maps), height * width),
                        np.tile(positions, (n_maps, 1)), np.tile(groups, n_maps),
                        tuple(name for name, _ in elements), (height, width), seed)


def _write_emsa(path, counts, step):
    # EMSA/MAS 1.0, one Y value per row. No claimed instrument identity.
    fields = {
        "FORMAT": "EMSA/MAS Spectral Data File", "VERSION": "1.0",
        "TITLE": "SYNTHETIC XRF DEMO - NOT AN INSTRUMENT MEASUREMENT",
        "DATE": "19-OCT-2026", "TIME": "00:00", "OWNER": "GreyTheory synthetic demo",
        "NPOINTS": str(len(counts)), "NCOLUMNS": "1", "XUNITS": "keV", "YUNITS": "counts",
        "DATATYPE": "Y", "XPERCHAN": f"{step:.12g}", "OFFSET": "0.0",
        "SIGNALTYPE": "EDS", "COMMENT": "Gaussian XRF lines with Poisson noise; no calibrated concentrations",
    }
    header = "".join(f"#{name:<12}: {value}\n" for name, value in fields.items())
    values = "\n".join(f"{int(value)}.0" for value in counts)
    Path(path).write_text(header + "#SPECTRUM    : Begin synthetic counts\n" + values +
                          "\n#ENDOFDATA   : End synthetic counts\n", encoding="ascii")


def _write_spx(path, counts, step):
    # Minimal schema for this project's reader; not a vendor-exported SPX.
    root = ElementTree.Element("TRTSpectrum")
    spectrum = ElementTree.SubElement(root, "ClassInstance", Type="TRTSpectrum")
    for key, value in {
        "Name": "SYNTHETIC XRF DEMO", "ChannelCount": str(len(counts)),
        "Channels": ",".join(str(int(value)) for value in counts),
        "CalibAbs": "0", "CalibLin": str(step), "Synthetic": "true",
    }.items():
        ElementTree.SubElement(spectrum, key).text = value
    ElementTree.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run_xrf_demo(output_dir="artifacts/synthetic_xrf", *, seed=7):
    """Generate files, read SPX back, and compare held-out-map predictions."""
    plt = plotting()
    output = Path(output_dir)
    for subdirectory in ("emsa", "spx"):
        (output / subdirectory).mkdir(parents=True, exist_ok=True)
    data = make_xrf_data(seed=seed)
    ids = [f"map{m:02d}_y{y:02d}_x{x:02d}" for m, (y, x) in zip(data.map_ids, data.positions)]
    reloaded = []
    for sample_id, counts in zip(ids, data.counts):
        _write_emsa(output / "emsa" / f"{sample_id}.msa", counts, .02)
        path = output / "spx" / f"{sample_id}.spx"
        _write_spx(path, counts, .02)
        spectrum = read_spx(path)
        np.testing.assert_allclose(spectrum.energy, data.energy_keV)
        reloaded.append(spectrum.counts)
    observed = np.asarray(reloaded)
    np.testing.assert_array_equal(observed, data.counts)
    target = data.mixing_weights[:, 2]
    train = data.map_ids != data.map_ids.max()
    test = ~train
    baseline = Pipeline([("pca", PoissonPCA(6)), ("regression", Ridge(alpha=1))])
    grey = Pipeline([("pca", GreyPCA(estimator=PoissonPCA(6), top_k=3)),
                     ("regression", Ridge(alpha=1))])
    metrics, predictions = [], {}
    for name, model in [("PoissonPCA + Ridge", baseline), ("GreyPCA(PoissonPCA) + Ridge", grey)]:
        model.fit(observed[train], target[train])
        predicted = model.predict(observed[test])
        predictions[name] = predicted
        metrics.append({"method": name, "held_out_map_mae": float(mean_absolute_error(target[test], predicted))})
    mean_error = float(mean_absolute_error(target[test], np.full(test.sum(), target[train].mean())))
    metrics.append({"method": "Training-mean baseline", "held_out_map_mae": mean_error})
    selector = GreyFeatureSelector(k=16, direction="either", constant_policy="exclude").fit(observed[train], target[train])
    ranking = np.argsort(-selector.scores, kind="stable")
    band_rows = [(rank, int(index), float(data.energy_keV[index]), float(selector.scores[index]),
                  int(selector.directions[index])) for rank, index in enumerate(ranking[:16], 1)]
    write_csv(output / "energy_ranking.csv", ["rank", "channel", "energy_keV", "gra_score", "comparison_sign"], band_rows)
    write_csv(output / "spectra.csv", ["energy_keV", *ids], zip(data.energy_keV, *observed))
    write_csv(output / "samples.csv", ["sample", "map", "y", "x", "split", "material_style", *data.elements],
              ((sample_id, int(m), int(y), int(x), "train" if fitting else "test", int(group), *weights)
               for sample_id, m, (y, x), fitting, group, weights in
               zip(ids, data.map_ids, data.positions, train, data.material_ids, data.mixing_weights)))
    np.savez_compressed(output / "dataset.npz", energy_keV=data.energy_keV, counts=observed,
                        mixing_weights=data.mixing_weights, map_ids=data.map_ids, positions=data.positions)
    write_csv(output / "predictions.csv", ["sample", "true_Cu_mixing_weight", "poisson_pca", "grey_pca"],
              zip(np.asarray(ids)[test], target[test], *predictions.values()))
    summary = {
        "synthetic": True, "seed": data.seed, "spectra": len(observed), "channels": observed.shape[1],
        "train_maps": sorted(set(data.map_ids[train].tolist())), "test_maps": sorted(set(data.map_ids[test].tolist())),
        "target": "Synthetic Cu line-template mixing weight, not measured wt%",
        "model": "Gaussian xraylib characteristic lines + continuum + Poisson noise; no full matrix/geometry model",
        "spx_readback": "All generated spectra matched this project's reader",
        "bruker_import": "EMSA exchange format; instrument/software import has not been tested",
        "spx_compatibility": "Minimal project-reader fixture, not guaranteed vendor-importable SPX",
        "metrics": metrics, "selected_components": grey.named_steps["pca"].selected_components.tolist(),
        "sources": ["https://www.bruker.com/en/products-and-solutions/elemental-analyzers/eds-wds-ebsd-SEM-Micro-XRF/software-esprit-family/esprit-reporting-and-data-management.html",
                    "https://microscopy.org/files/galleries/MSA-MAS_FileFormatSpecification_1991.pdf"],
    }
    write_json(output / "summary.json", summary)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for group, name in enumerate(["Ca-rich", "Fe-rich", "Cu/Zn-rich"]):
        axes[0].plot(data.energy_keV, observed[data.material_ids == group].mean(axis=0), label=name)
    axes[0].set(xlabel="Energy (keV)", ylabel="Counts (group mean)", yscale="log", title="Synthetic XRF spectra")
    axes[0].legend()
    axes[1].barh([f"{row[2]:.2f}" for row in band_rows][::-1], [row[3] for row in band_rows][::-1])
    axes[1].set(xlabel="Training GRA score", ylabel="Energy (keV)", title="Top energy channels vs Cu mixing weight")
    fig.savefig(output / "spectra_and_ranking.svg")
    fig.savefig(output / "spectra_and_ranking.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), constrained_layout=True)
    maps = [target[test], *predictions.values()]
    for axis, values, title in zip(axes, maps, ["Known synthetic Cu weight", "PoissonPCA + Ridge", "GreyPCA + Ridge"]):
        image = axis.imshow(values.reshape(data.map_shape), vmin=0, vmax=1, cmap="viridis")
        axis.set(title=title, xlabel="x", ylabel="y")
    fig.colorbar(image, ax=axes, label="Mixing weight (not wt%)")
    fig.savefig(output / "held_out_map.svg")
    fig.savefig(output / "held_out_map.png", dpi=160)
    plt.close(fig)
    report(output / "index.html", "合成 XRF 光譜：Grey/PCA 示範",
           "4 張獨立模擬的 6×6 掃描圖，共 144 組光譜；前三張訓練、最後一張測試。",
           [("光譜差異與能量排序", '<img src="spectra_and_ranking.svg" alt="Synthetic spectra and training energy ranking">'),
            ("已知目標與預測", '<img src="held_out_map.svg" alt="Held-out simulated map predictions">' +
             table(["方法", "獨立模擬圖 MAE"], [(row["method"], f'{row["held_out_map_mae"]:.5f}') for row in metrics])),
            ("可下載的輸入與結果", '<p><a href="emsa/' + ids[0] + '.msa">EMSA/MSA 光譜</a> · '
             '<a href="spx/' + ids[0] + '.spx">專案讀取用 SPX</a> · <a href="spectra.csv">全部光譜 CSV</a> · '
             '<a href="samples.csv">模擬真值</a> · <a href="energy_ranking.csv">能量排名</a> · '
             '<a href="predictions.csv">測試圖預測</a> · <a href="summary.json">設定與限制</a></p>'),
            ("怎麼解讀", '<p>混合權重只控制模擬譜線強度，不是儀器量測的元素重量百分比。Bruker 公開列有 EMSA 匯入功能，'
             '但這批檔案尚未在你的 M4／ESPRIT 版本上實測。SPX 僅驗證本專案讀回，沒有使用任何外部儀器測試資料。</p>')])
    return {"report": output / "index.html", "summary": summary, "data": data}
