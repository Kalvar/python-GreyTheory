"""File inputs must preserve order, orientation, and pixel meaning."""

import builtins
import csv

import numpy as np
import pytest

from greytheory.io import load_images

Image = pytest.importorskip("PIL.Image")


def test_single_path_and_batch_keep_pixel_values_and_order(tmp_path):
    dark, light = tmp_path / "dark.png", tmp_path / "light.png"
    Image.new("RGB", (12, 8), (0, 128, 255)).save(dark)
    Image.new("RGB", (12, 8), "white").save(light)
    single = load_images(dark)
    assert single.shape == (1, 8, 12, 3)
    np.testing.assert_allclose(single[0, 0, 0], [0, 128 / 255, 1])
    batch = load_images([light, dark])
    np.testing.assert_allclose(batch[0], 1)
    np.testing.assert_array_equal(batch[1], single[0])
    assert load_images(dark, mode="L").shape == (1, 8, 12)


def test_jpeg_exif_orientation_is_applied_before_batching(tmp_path):
    path = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (12, 8), "red")
    exif = Image.Exif()
    exif[274] = 6
    image.save(path, exif=exif)
    result = load_images(path)
    assert result.shape == (1, 12, 8, 3)
    assert result[0, 0, 0, 0] > 0.9


def test_transparency_uses_white_instead_of_hidden_rgb_values(tmp_path):
    path = tmp_path / "transparent.png"
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 0, 255))
    image.save(path)
    result = load_images(path)
    np.testing.assert_array_equal(result[0, 0, 0], 0)
    np.testing.assert_array_equal(result[0, 1, 1], 1)


def test_resize_preserves_aspect_ratio_with_white_padding(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("L", (8, 4), 0).save(path)
    result = load_images(path, mode="L", size=(8, 8))[0]
    np.testing.assert_array_equal(result[:2], 1)
    np.testing.assert_array_equal(result[2:6], 0)
    np.testing.assert_array_equal(result[6:], 1)


def test_mixed_dimensions_require_explicit_size(tmp_path):
    paths = [tmp_path / "one.png", tmp_path / "two.png"]
    Image.new("RGB", (12, 8)).save(paths[0])
    Image.new("RGB", (8, 12)).save(paths[1])
    with pytest.raises(ValueError, match="dimensions differ"):
        load_images(paths)
    assert load_images(paths, size=(16, 16)).shape == (2, 16, 16, 3)


def test_scientific_high_bit_depth_and_animated_inputs_are_not_silently_reduced(tmp_path):
    path = tmp_path / "counts.png"
    Image.fromarray(np.full((8, 8), 40000, dtype=np.uint16)).save(path)
    with pytest.raises(ValueError, match="8-bit display"):
        load_images(path)
    animation = tmp_path / "animation.gif"
    Image.new("RGB", (8, 8), "black").save(
        animation, save_all=True, append_images=[Image.new("RGB", (8, 8), "white")], duration=100,
    )
    with pytest.raises(ValueError, match="single-frame"):
        load_images(animation)


def test_bad_inputs_and_missing_optional_dependency_are_clear(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="at least one"):
        load_images([])
    with pytest.raises(ValueError, match="mode"):
        load_images([], mode="RGBA")
    with pytest.raises(ValueError, match="size"):
        load_images([], size=(0, 12))
    with pytest.raises(FileNotFoundError):
        load_images(tmp_path / "missing.png")
    original_import = builtins.__import__

    def without_pillow(name, *args, **kwargs):
        if name == "PIL":
            raise ImportError("Pillow not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pillow)
    with pytest.raises(ImportError, match="pip install Pillow"):
        load_images(tmp_path / "missing.png")


def test_file_example_ranks_an_exact_copy_and_exports_aligned_rows(tmp_path):
    from examples.image_files import compare_image_files, create_demo_images, write_results

    paths, query = create_demo_images(tmp_path / "inputs")
    result = compare_image_files(paths, query)
    assert result["ranking"][0] == 3
    assert result["distances"][3] == pytest.approx(0, abs=1e-5)
    assert result["features"].shape[0] == result["components"].shape[0] == 9
    write_results(tmp_path / "results", paths, query, result)
    for filename in ["features.csv", "components.csv", "ranking.csv"]:
        with (tmp_path / "results" / filename).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        assert len(rows) == (9 if filename == "ranking.csv" else 10)
        assert len({len(row) for row in rows}) == 1
    with (tmp_path / "results/ranking.csv").open(newline="", encoding="utf-8") as stream:
        ranking = list(csv.DictReader(stream))
    assert ranking[0]["reference"] == str(paths[3])
    other_query = compare_image_files(paths, paths[0])
    np.testing.assert_allclose(result["components"][:8], other_query["components"][:8])
