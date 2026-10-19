"""Bounded SPX XML reader. Detector calibrations are in keV."""

from dataclasses import dataclass
from pathlib import Path
import re
from io import BytesIO

import numpy as np
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ..._validation import integer


@dataclass
class Spectrum:
    counts: np.ndarray
    energy: np.ndarray | None
    metadata: dict


def parse_xml(data, *, max_bytes=32 * 1024 * 1024, max_depth=64):
    if len(data) > max_bytes:
        raise ValueError("XML exceeds configured byte limit")
    depth = 0
    root = None
    try:
        for event, element in ElementTree.iterparse(BytesIO(data), events=("start", "end"), forbid_dtd=True):
            if event == "start":
                depth += 1
                if root is None:
                    root = element
                if depth > max_depth:
                    raise ValueError("XML exceeds configured depth limit")
            else:
                depth -= 1
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise ValueError("invalid or unsafe Bruker XML") from exc
    if root is None:
        raise ValueError("empty XML")
    return root


def calibration(element, channel_count):
    absolute = element.findtext(".//CalibAbs")
    linear = element.findtext(".//CalibLin")
    if absolute is None or linear is None:
        return None
    offset, step = float(absolute), float(linear)
    if not np.isfinite([offset, step]).all() or step <= 0:
        raise ValueError("invalid linear energy calibration")
    return offset + step * np.arange(channel_count)


def read_spx(path, *, max_bytes=32 * 1024 * 1024, max_channels=1_000_000):
    max_bytes = integer(max_bytes, "max_bytes")
    max_channels = integer(max_channels, "max_channels")
    with Path(path).open("rb") as handle:
        data = handle.read(max_bytes + 1)
    root = parse_xml(data, max_bytes=max_bytes)
    if root.tag != "TRTSpectrum":
        raise ValueError("unsupported SPX root/version")
    spectra = root.findall(".//ClassInstance[@Type='TRTSpectrum']")
    if len(spectra) != 1:
        raise ValueError("expected exactly one SPX spectrum")
    spectrum = spectra[0]
    count_text = spectrum.findtext(".//Channels")
    count_size = spectrum.findtext(".//ChannelCount")
    if count_text is None or count_size is None:
        raise ValueError("SPX is missing Channels or ChannelCount")
    size = int(count_size)
    if not 0 < size <= max_channels:
        raise ValueError("SPX channel count exceeds limit")
    tokens = count_text.strip().split(",")
    if len(tokens) != size or any(not re.fullmatch(r"\s*\d+\s*", value) for value in tokens):
        raise ValueError("SPX counts must be nonnegative integers matching ChannelCount")
    try:
        counts = np.array([int(value) for value in tokens], dtype=np.uint64)
    except OverflowError as exc:
        raise ValueError("SPX count exceeds uint64") from exc
    metadata = {
        e.tag: e.text.strip()
        for e in spectrum.iter()
        if e.text and e.text.strip() and len(e.text) < 256 and e.tag != "Channels"
    }
    metadata.update(source=str(path), energy_unit="keV", format="SPX")
    return Spectrum(counts, calibration(spectrum, size), metadata)
