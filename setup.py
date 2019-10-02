import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="greytheory",
    version="0.1",
    author="Kalvar",
    author_email="ilovekalvar@gmail.com",
    description="Grey theory, implemented by python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kalvar/python-GreyTheory.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)