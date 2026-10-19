"""Independent, bounded SFS/BCF reader inferred from supplied M4 binary data.

No HyperSpy/RosettaSciIO source was used. Supported layout is intentionally
narrow: uncompressed SFS streams with indexed, instructively packed pixels.
Unrecognized encodings fail explicitly. See the Bruker spectra section in README.md.
"""

from pathlib import Path
import math
import struct

import numpy as np

from ..._validation import integer
from .spx import Spectrum, calibration, parse_xml


class UnsupportedBCFError(ValueError):
    pass


class _SFS:
    BASE = 0x118

    def __init__(self, path):
        self.path = Path(path)
        self.file_size = self.path.stat().st_size
        with self.path.open("rb") as handle:
            head = handle.read(0x150)
        if len(head) < 0x150 or head[:8] != b"AAMVHFSS" or head[0x118:0x121] != b"AASFSSGN-":
            raise UnsupportedBCFError("unsupported or truncated SFS/BCF signature")
        self.chunk_size = struct.unpack_from("<I", head, 0x128)[0]
        directory, count, total = struct.unpack_from("<3I", head, 0x140)
        if not 512 <= self.chunk_size <= 16 * 1024 * 1024 or self.chunk_size % 512:
            raise ValueError("invalid SFS chunk size")
        self.payload = self.chunk_size - 32
        if self.BASE + total * self.chunk_size != self.file_size:
            raise ValueError("truncated or inconsistent SFS file length")
        if count < 1 or count * 512 > self.payload:
            raise UnsupportedBCFError("multi-block SFS directory is not verified")
        raw = self._chunk(directory)
        self.entries = {}
        for i in range(count):
            entry = raw[32 + i * 512 : 32 + (i + 1) * 512]
            pointer = struct.unpack_from("<I", entry)[0]
            length = struct.unpack_from("<Q", entry, 4)[0]
            name = entry[224:484].split(b"\0")[0].decode("cp1252")
            if name and pointer != 0xFFFFFFFF:
                if name in self.entries:
                    raise UnsupportedBCFError("duplicate SFS stream names")
                self.entries[name] = (pointer, length)

    def _chunk(self, index):
        offset = self.BASE + index * self.chunk_size
        if index < 1 or offset + self.chunk_size > self.file_size:
            raise ValueError("SFS chunk reference outside file")
        with self.path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(self.chunk_size)
        if len(data) != self.chunk_size:
            raise ValueError("truncated SFS chunk")
        return data

    def stream(self, name):
        if name not in self.entries:
            raise UnsupportedBCFError(f"missing indexed BCF stream {name}")
        pointer, length = self.entries[name]
        blocks = math.ceil(length / self.payload)
        if blocks * 4 > self.payload:
            raise UnsupportedBCFError("multi-level SFS stream index is not verified")
        raw = self._chunk(pointer)
        pointers = struct.unpack_from(f"<{blocks}I", raw, 32)
        for index in pointers:
            if index < 1 or self.BASE + (index + 1) * self.chunk_size > self.file_size:
                raise ValueError("invalid stream chunk reference")
        if len(set(pointers)) != len(pointers):
            raise ValueError("duplicate stream chunk reference")
        return _Stream(self, pointers, length)


class _Stream:
    def __init__(self, container, blocks, length):
        self.container, self.blocks, self.length = container, blocks, length

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.length:
            raise ValueError("BCF stream read outside bounds")
        c = self.container
        parts = []
        with c.path.open("rb") as handle:
            while size:
                block, within = divmod(offset, c.payload)
                length = min(size, c.payload - within)
                handle.seek(c.BASE + self.blocks[block] * c.chunk_size + 32 + within)
                part = handle.read(length)
                if len(part) != length:
                    raise ValueError("truncated BCF stream")
                parts.append(part)
                offset += length
                size -= length
        return b"".join(parts)


def _decode_instructive(data, channels):
    """Nibble-packed nonnegative deltas with per-packet integer baseline."""
    output = np.zeros(channels, dtype=np.uint64)
    cursor = channel = 0
    while cursor < len(data):
        if channel == channels and len(data) - cursor <= 4 and not any(data[cursor:]):
            cursor = len(data)
            break
        if cursor + 2 > len(data):
            raise ValueError("truncated BCF packet")
        width, count = data[cursor : cursor + 2]
        cursor += 2
        if count == 0 or channel + count > channels:
            raise ValueError("BCF packet channel count mismatch")
        if width == 0:
            channel += count
            continue
        if width not in (1, 2):
            raise UnsupportedBCFError(f"unverified BCF nibble width {width}")
        packed_size = (width * count + 1) // 2
        if cursor + width + packed_size > len(data):
            raise ValueError("truncated packed BCF counts")
        baseline = int.from_bytes(data[cursor : cursor + width], "little")
        cursor += width
        packed = data[cursor : cursor + packed_size]
        cursor += packed_size
        for j in range(count):
            value = 0
            for k in range(width):
                index = j * width + k
                nibble = (packed[index // 2] >> (4 * (index % 2))) & 15
                value += nibble << (4 * k)
            output[channel + j] = baseline + value
        channel += count
    if channel != channels:
        raise ValueError("decoded BCF channel count mismatch")
    return output


class BCFMap:
    def __init__(self, path, *, max_metadata_bytes=32 * 1024 * 1024, max_channels=65536):
        self._sfs = _SFS(path)
        header = self._sfs.stream("HeaderData")
        if header.length > max_metadata_bytes:
            raise ValueError("BCF XML metadata exceeds configured limit")
        root = parse_xml(header.read(0, header.length), max_bytes=max_metadata_bytes)
        if root.tag != "TRTSpectrumDatabase":
            raise UnsupportedBCFError("unsupported BCF metadata root/version")
        self.detectors = tuple(
            sorted(
                int(name[len("SpectrumData") :])
                for name in self._sfs.entries
                if name.startswith("SpectrumData") and name[12:].isdigit()
            )
        )
        if not self.detectors:
            raise UnsupportedBCFError("no verified indexed spectrum streams")
        self._streams, self.energy_axes, self.metadata = {}, {}, {}
        shape = None
        for detector in self.detectors:
            data = self._sfs.stream(f"SpectrumData{detector}")
            positions = self._sfs.stream(f"SpectrumPositions{detector}")
            width, height, channels, version = struct.unpack("<4I", data.read(0, 16))
            if version != 1 or width == 0 or height == 0 or not 1 <= channels <= max_channels:
                raise UnsupportedBCFError("unsupported BCF spectrum header/version")
            if width * height > 100_000_000 or positions.length != 8 + 8 * width * height:
                raise ValueError("BCF position index dimensions or limits violated")
            if struct.unpack("<2I", positions.read(0, 8)) != (width, height):
                raise ValueError("BCF position and spectrum dimensions disagree")
            current = height, width, channels
            if shape is not None and shape != current:
                raise UnsupportedBCFError("detector dimensions do not match")
            shape = current
            spectrum = root.find(f".//SpectrumData{detector}")
            if spectrum is None:
                raise ValueError("missing detector-specific metadata")
            self.energy_axes[detector] = calibration(spectrum, channels)
            self.metadata[detector] = dict(
                detector=detector, energy_unit="keV", source=str(path), encoding="indexed-instructive"
            )
            self._streams[detector] = data, positions
        self.shape = shape
        self.lazy = True

    def get_pixel(self, y, x, detector=0):
        y = integer(y, "y", minimum=0, maximum=self.shape[0] - 1)
        x = integer(x, "x", minimum=0, maximum=self.shape[1] - 1)
        if detector not in self._streams:
            raise ValueError("unknown detector")
        data, positions = self._streams[detector]
        offset = struct.unpack("<Q", positions.read(8 + 8 * (y * self.shape[1] + x), 8))[0]
        channels, repeated, flag, packing, dtype, length, unpacked = struct.unpack(
            "<5H2I", data.read(offset, 18)
        )
        if channels > self.shape[2] or channels != repeated:
            raise ValueError("invalid pixel channel count")
        if flag != 0 or packing != 12 or dtype != 2 or length != unpacked:
            raise UnsupportedBCFError("unverified compressed or packed BCF pixel encoding")
        if length > 32 * self.shape[2] + 1024:
            raise ValueError("BCF pixel payload exceeds limit")
        decoded = _decode_instructive(data.read(offset + 18, length), channels)
        result = np.zeros(self.shape[2], dtype=np.uint64)
        result[:channels] = decoded
        return result

    def get_spectra(self, roi=None, detector=0):
        if roi is None:
            roi = (0, 0, self.shape[0], self.shape[1])
        if len(roi) != 4:
            raise ValueError("roi must be (y0, x0, y1, x1), exclusive upper bounds")
        y0, x0, y1, x1 = [integer(v, "roi coordinate", minimum=0) for v in roi]
        if not 0 <= y0 < y1 <= self.shape[0] or not 0 <= x0 < x1 <= self.shape[1]:
            raise ValueError("ROI is empty or outside map")
        return np.stack(
            [self.get_pixel(y, x, detector) for y in range(y0, y1) for x in range(x0, x1)]
        ).reshape(y1 - y0, x1 - x0, self.shape[2])

    def iter_tiles(self, tile_shape=(16, 16), detector=0):
        height = integer(tile_shape[0], "tile height")
        width = integer(tile_shape[1], "tile width")
        for y in range(0, self.shape[0], height):
            for x in range(0, self.shape[1], width):
                roi = (y, x, min(y + height, self.shape[0]), min(x + width, self.shape[1]))
                yield roi, self.get_spectra(roi, detector)

    def sum_detectors(self, y, x):
        axes = [self.energy_axes[d] for d in self.detectors]
        if any(axis is None for axis in axes) or not all(np.array_equal(axes[0], a) for a in axes[1:]):
            raise ValueError("detector energy axes differ; explicit count-conserving alignment is required")
        spectra = [self.get_pixel(y, x, d) for d in self.detectors]
        summed = np.zeros(self.shape[2], dtype=np.uint64)
        for spectrum in spectra:
            if np.any(summed > np.iinfo(np.uint64).max - spectrum):
                raise OverflowError("detector sum exceeds uint64")
            summed += spectrum
        return Spectrum(summed, axes[0].copy(), dict(method="aligned-channel-sum", detectors=self.detectors))


def read_bcf(path, lazy=True, **kwargs):
    result = BCFMap(path, **kwargs)
    if not isinstance(lazy, bool):
        raise TypeError("lazy must be bool")
    if not lazy:
        # Explicit eager materialization; lazy=True never expands a full cube.
        result.data = {d: result.get_spectra(detector=d) for d in result.detectors}
        result.lazy = False
    return result
