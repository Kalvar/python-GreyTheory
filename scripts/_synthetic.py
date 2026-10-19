"""Small generated SPX/BCF files for install smoke tests (no instrument data)."""

from pathlib import Path
import struct


def make_bcf(path):
    chunk_size, base, total = 512, 0x118, 8
    output = bytearray(base + chunk_size * total)
    output[:8] = b"AAMVHFSS"
    output[base : base + 9] = b"AASFSSGN-"
    struct.pack_into("<I", output, 0x128, chunk_size)
    # Directory needs 3*512 bytes: use a larger chunk size.
    chunk_size = 2048
    output = bytearray(base + chunk_size * total)
    output[:8] = b"AAMVHFSS"
    output[base : base + 9] = b"AASFSSGN-"
    struct.pack_into("<I", output, 0x128, chunk_size)
    struct.pack_into("<3I", output, 0x140, 1, 3, total)
    xml = (
        b"<TRTSpectrumDatabase><ClassInstance><SpectrumData0>"
        b"<CalibAbs>0</CalibAbs><CalibLin>0.01</CalibLin>"
        b"</SpectrumData0></ClassInstance></TRTSpectrumDatabase>"
    )
    payload = bytes([2, 3, 0, 0, 1, 2, 3, 0, 0, 0, 0])
    spectrum = bytearray(424)
    struct.pack_into("<4I", spectrum, 0, 1, 1, 3, 1)
    struct.pack_into("<2I", spectrum, 416, 1, 0)
    spectrum.extend(struct.pack("<5H2I", 3, 3, 0, 12, 2, len(payload), len(payload)))
    spectrum.extend(payload)
    positions = struct.pack("<2IQ", 1, 1, 424)
    for i, (name, content) in enumerate(
        zip(["HeaderData", "SpectrumData0", "SpectrumPositions0"], [xml, spectrum, positions])
    ):
        pointer, data_block = 2 + i * 2, 3 + i * 2
        entry = base + chunk_size + 32 + 512 * i
        struct.pack_into("<IQ", output, entry, pointer, len(content))
        output[entry + 224 : entry + 224 + len(name)] = name.encode()
        struct.pack_into("<I", output, base + pointer * chunk_size + 32, data_block)
        data_offset = base + data_block * chunk_size + 32
        output[data_offset : data_offset + len(content)] = content
    Path(path).write_bytes(output)


def make_spx(path):
    Path(path).write_text("""<?xml version="1.0" encoding="utf-8"?><TRTSpectrum>
    <ClassInstance Type="TRTSpectrum"><ChannelCount>3</ChannelCount>
    <Channels>1,2,3</Channels><CalibAbs>0</CalibAbs><CalibLin>0.01</CalibLin>
    </ClassInstance></TRTSpectrum>""")
