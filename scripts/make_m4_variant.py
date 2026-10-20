"""Create a locally simulated BCF variant for GreyTheory, not an instrument export.

Run: python -m scripts.make_m4_variant
Generated files stay in ignored data/test/ alongside the source measurement.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
from xml.etree import ElementTree as ET

import numpy as np

from greytheory.io.bruker import read_bcf

ROOT = Path(__file__).resolve().parents[1]


def _write_container(path, streams):
    """Write only the narrow SFS layout supported by this project's BCF reader."""
    base, chunk_size = 0x118, 4096
    payload_size = chunk_size - 32
    if len(streams) * 512 > payload_size:
        raise ValueError("Too many streams for the verified single-directory layout")
    blocks = [bytearray(chunk_size), bytearray(chunk_size)]
    for i, (name, content) in enumerate(streams.items()):
        count = (len(content) + payload_size - 1) // payload_size
        if count * 4 > payload_size:
            raise ValueError("Stream exceeds verified index size")
        pointer = len(blocks)
        index = bytearray(chunk_size)
        blocks.append(index)
        for j in range(count):
            struct.pack_into("<I", index, 32 + j * 4, len(blocks))
            block = bytearray(chunk_size)
            part = content[j * payload_size : (j + 1) * payload_size]
            block[32 : 32 + len(part)] = part
            blocks.append(block)
        offset = 32 + i * 512
        struct.pack_into("<IQ", blocks[1], offset, pointer, len(content))
        encoded = name.encode("ascii")
        blocks[1][offset + 224 : offset + 224 + len(encoded)] = encoded
    header = bytearray(base)
    header[:8] = b"AAMVHFSS"
    blocks[0][:9] = b"AASFSSGN-"
    struct.pack_into("<I", blocks[0], 16, chunk_size)
    struct.pack_into("<3I", blocks[0], 40, 1, len(streams), len(blocks))
    path.write_bytes(header + b"".join(blocks))


def write_demo_bcf(path, cubes, axes):
    """Round-trip demonstration writer; no general Bruker software compatibility claim."""
    root = ET.Element("TRTSpectrumDatabase")
    metadata = ET.SubElement(root, "ClassInstance", Type="GreyTheorySynthetic")
    ET.SubElement(metadata, "Synthetic").text = "true"
    streams = {}
    shape = None
    for detector, cube in sorted(cubes.items()):
        cube = np.asarray(cube)
        if cube.ndim != 3 or cube.size == 0 or not np.isfinite(cube).all():
            raise ValueError("Expected a finite nonempty height × width × channels cube")
        if np.any(cube < 0) or np.any(cube > 65535) or np.any(cube != np.floor(cube)):
            raise ValueError("Demo writer accepts integer counts from 0 to 65535")
        if shape is not None and cube.shape != shape:
            raise ValueError("Detector shapes must match")
        shape = cube.shape
        height, width, channels = shape
        axis = np.asarray(axes[detector])
        if axis.shape != (channels,) or channels < 2 or not np.isfinite(axis).all():
            raise ValueError("Expected a finite linear energy axis")
        step = float(axis[1] - axis[0])
        if step <= 0 or not np.allclose(axis, axis[0] + step * np.arange(channels), rtol=0, atol=1e-9):
            raise ValueError("Demo writer requires a positive linear calibration")
        spectrum = ET.SubElement(metadata, f"SpectrumData{detector}")
        ET.SubElement(spectrum, "CalibAbs").text = repr(float(axis[0]))
        ET.SubElement(spectrum, "CalibLin").text = repr(step)
        data = bytearray(424)
        struct.pack_into("<4I", data, 0, width, height, channels, 1)
        struct.pack_into("<2I", data, 416, width, height)
        offsets = []
        for pixel in cube.reshape(-1, channels):
            offsets.append(len(data))
            # One baseline packet per channel avoids ambiguous adaptive packing.
            payload = b"".join(b"\x02\x01" + int(value).to_bytes(2, "little") + b"\0" for value in pixel)
            data.extend(struct.pack("<5H2I", channels, channels, 0, 12, 2, len(payload), len(payload)))
            data.extend(payload)
        streams[f"SpectrumData{detector}"] = data
        streams[f"SpectrumPositions{detector}"] = struct.pack("<2I", width, height) + struct.pack(
            f"<{len(offsets)}Q", *offsets
        )
    if not streams:
        raise ValueError("At least one detector is required")
    streams = {"HeaderData": ET.tostring(root, encoding="utf-8"), **streams}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_container(path, streams)


def generate(source, output, *, seed=20261020):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Output must differ from the original measurement")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original = read_bcf(source)
    height, width, channels = original.shape
    rng = np.random.default_rng(seed)
    # Gradually increasing additions make locations visibly different after shape normalization.
    yy, xx = np.indices((height, width))
    amplitude = 60 * yy / max(1, height - 1) * xx / max(1, width - 1)
    exposure = np.ones((height, width))
    exposure[0] = np.linspace(0.9, 1.1, width)
    cubes, rows = {}, []
    for detector in original.detectors:
        source_counts = original.get_spectra(detector=detector)
        energy = original.energy_axes[detector]
        if energy is None:
            raise ValueError("Source detector must have a calibrated energy axis")
        additions = np.exp(-0.5 * ((energy - 8.0) / 0.10) ** 2)
        additions += 0.3 * np.exp(-0.5 * ((energy - 10.3) / 0.13) ** 2)
        expected = source_counts * exposure[..., None] + amplitude[..., None] * additions
        cubes[detector] = rng.poisson(expected).astype(np.uint64)
        for y in range(height):
            for x in range(width):
                rows.append(
                    dict(
                        detector=detector,
                        y=y,
                        x=x,
                        exposure_factor=float(exposure[y, x]),
                        added_peak_amplitude=float(amplitude[y, x]),
                        source_total=int(source_counts[y, x].sum()),
                        simulated_total=int(cubes[detector][y, x].sum()),
                    )
                )
    write_demo_bcf(output, cubes, original.energy_axes)
    restored = read_bcf(output)
    assert restored.shape == original.shape and restored.detectors == original.detectors
    for detector in original.detectors:
        np.testing.assert_array_equal(restored.get_spectra(detector=detector), cubes[detector])
        np.testing.assert_allclose(restored.energy_axes[detector], original.energy_axes[detector], atol=1e-9)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    truth = output.with_suffix(".changes.json")
    truth.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = dict(
        simulated=True,
        derived_from_measurement=True,
        seed=seed,
        source=source.name,
        source_sha256=original_hash,
        output=output.name,
        output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        shape=list(original.shape),
        detectors=list(original.detectors),
        retained="Map dimensions, detector-specific energy calibrations and the measured spectral baseline.",
        changes="Poisson resampling; first-row intensity factors 0.9–1.1; spatially increasing artificial Gaussian signals at 8.0 and 10.3 keV.",
        truth=truth.name,
        annotations="Artificial peaks are not calibrated element concentrations or material labels.",
        container="Minimal project-supported SFS/BCF layout; original images and instrument metadata are not copied.",
        compatibility="Verified with GreyTheory only; not certified for import into Bruker instrument software.",
        redistribution="Derived from local measurement data; keep in ignored data/test/. No additional redistribution permission is granted.",
    )
    output.with_suffix(".simulation.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/test/m4_tornado/minBcf.bcf")
    parser.add_argument("--output", type=Path, default=ROOT / "data/test/m4_tornado/minBcf_simulated.bcf")
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    manifest = generate(args.source, args.output, seed=args.seed)
    print(args.output.resolve())
    print(f"Verified round-trip: {manifest['shape']}; detectors {manifest['detectors']}")


if __name__ == "__main__":
    main()
