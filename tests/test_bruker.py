"""Reader checks use generated files and malformed inputs; no external dataset is required."""

import numpy as np
import pytest

from greytheory.io.bruker import read_spx, read_bcf
from greytheory.io.bruker.bcf import _decode_instructive


def test_spx_synthetic_and_safety(tmp_path):
    p = tmp_path / "test.spx"
    p.write_bytes(b"""<?xml version="1.0" encoding="windows-1252"?><TRTSpectrum>
    <ClassInstance Type="TRTSpectrum"><ChannelCount>3</ChannelCount><Channels>1,2,3</Channels>
    <CalibAbs>-1</CalibAbs><CalibLin>0.1</CalibLin></ClassInstance></TRTSpectrum>""")
    s = read_spx(p)
    np.testing.assert_array_equal(s.counts, [1, 2, 3])
    np.testing.assert_allclose(s.energy, [-1, -0.9, -0.8])
    with pytest.raises(ValueError):
        read_spx(p, max_bytes=8)
    p.write_text('<!DOCTYPE a [<!ENTITY x "oops">]><TRTSpectrum>&x;</TRTSpectrum>')
    with pytest.raises(ValueError):
        read_spx(p)


def test_packet_and_malformed():
    # two zero channels, two 4-bit values with baseline 1, two 8-bit values.
    data = bytes([0, 2, 1, 2, 1, 0x32, 2, 2, 0, 0, 20, 30])
    np.testing.assert_array_equal(_decode_instructive(data, 6), [0, 0, 3, 4, 20, 30])
    with pytest.raises(ValueError):
        _decode_instructive(data[:-1], 6)


def test_bad_bcf(tmp_path):
    p = tmp_path / "bad.bcf"
    p.write_bytes(b"AAMVHFSS")
    with pytest.raises(ValueError):
        read_bcf(p)


def test_generated_bcf(tmp_path):
    from scripts._synthetic import make_bcf

    path = tmp_path / "generated.bcf"
    make_bcf(path)
    b = read_bcf(path)
    np.testing.assert_array_equal(b.get_pixel(0, 0), [1, 2, 3])
    np.testing.assert_array_equal(b.sum_detectors(0, 0).counts, [1, 2, 3])
    eager = read_bcf(path, lazy=False)
    assert eager.data[0].shape == (1, 1, 3)
    with pytest.raises(ValueError):
        b.get_pixel(-1, 0)
    with pytest.raises(ValueError):
        b.get_spectra((0, 0, 2, 1))
    damaged = path.read_bytes()[:-1]
    path.write_bytes(damaged)
    with pytest.raises(ValueError):
        read_bcf(path)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "windows-1252"])
def test_spx_encodings(encoding, tmp_path):
    xml = f'''<?xml version="1.0" encoding="{encoding}"?><TRTSpectrum>
    <ClassInstance Type="TRTSpectrum"><ChannelCount>1</ChannelCount><Channels>7</Channels>
    </ClassInstance></TRTSpectrum>'''
    path = tmp_path / "encoding.spx"
    path.write_bytes(xml.encode(encoding))
    result = read_spx(path)
    assert result.counts.tolist() == [7] and result.energy is None


def test_bcf_unverified_width_rejected():
    with pytest.raises(ValueError, match="unverified"):
        _decode_instructive(bytes([3, 1, 0, 0, 0, 0, 0]), 1)
