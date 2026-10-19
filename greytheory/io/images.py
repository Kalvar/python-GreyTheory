"""Read display images into batches for ImagePatchFeatures."""

from os import PathLike

import numpy as np

from .._validation import integer


def load_images(paths, *, mode="RGB", size=None):
    """Load one path or a sequence of paths as a float64 batch in [0, 1].

    Requires the optional Pillow dependency. Inputs are single-frame, 8-bit
    display images, not raw scientific intensity arrays. Apply EXIF orientation
    and composite transparency over white before converting to RGB or L.
    With size=(width, height), preserve aspect ratio and pad with white.
    Otherwise all oriented images must have the same dimensions.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ImportError("Reading image files requires Pillow: python -m pip install Pillow") from error

    if mode not in {"RGB", "L"}:
        raise ValueError("mode must be RGB or L")
    if size is not None:
        if len(size) != 2:
            raise ValueError("size must contain (width, height)")
        size = tuple(integer(value, "image size") for value in size)
    paths = [paths] if isinstance(paths, (str, bytes, PathLike)) else list(paths)
    if not paths:
        raise ValueError("provide at least one image path")

    images = []
    expected_shape = None
    for path in paths:
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError(f"{path}: use a single-frame image")
            if source.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "CMYK", "YCbCr"}:
                raise ValueError(f"{path}: use an 8-bit display image; keep scientific intensities as arrays")
            image = ImageOps.exif_transpose(source)
            if "A" in image.getbands() or "transparency" in image.info:
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image.convert("RGBA"))
                image = background
            image = image.convert(mode)
            if size is not None:
                image = ImageOps.pad(image, size, method=Image.Resampling.LANCZOS, color="white")
            values = np.asarray(image, dtype=np.float64) / 255.0
        if expected_shape is not None and values.shape != expected_shape:
            raise ValueError(f"{path}: image dimensions differ; supply a common size=(width, height)")
        expected_shape = values.shape
        images.append(values)
    return np.stack(images)
