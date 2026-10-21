# Third-party notices

GreyTheory's own code is released under the [MIT License](LICENSE).

Runtime dependencies are listed in [pyproject.toml](pyproject.toml) and installed
separately. Their source code and native libraries are not bundled with GreyTheory.
Each dependency retains its own license and copyright notices.

If you redistribute dependencies with an application, retain the notices supplied
with those packages and comply with the licenses of the versions you distribute.

Research and file-format acknowledgements are listed in the
[README references](README.md#references).

The optional desktop workbench uses [pywebview](https://github.com/r0x0r/pywebview),
licensed under BSD-3-Clause. It is installed separately with the `workbench` extra;
its code and platform GUI dependencies are not bundled in this source distribution.

The experimental research models are independently written implementations of
cited mathematical definitions or explicitly documented engineering variants.
No author source code, publisher figures, article text, or external experimental
datasets are bundled. The RL-FGM article is licensed CC BY-NC 4.0; that article
is not redistributed or relicensed as MIT. Model sources and implementation
differences are documented in the usage guide.
