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

### Unofficial implementations and rights notices

Paper-based algorithms in GreyTheory are **unofficial implementations**. They are not affiliated with, approved by, or endorsed by the papers’ authors or their institutions. References credit the original research; implementation differences and independently designed extensions are documented separately.

MIT covers the rights granted by this project’s contributors. It does not establish permission under third-party patents or confirm freedom to operate. Users should assess applicable rights and obtain any necessary permissions for their use and deployment regions. The software is provided “as is” under MIT; this notice does not alter that license or exclude liability that cannot lawfully be excluded.

If you believe an implementation infringes your patent, copyright or other rights, please email [ilovekalvar@gmail.com](mailto:ilovekalvar@gmail.com) with your contact details, the right claimed, and the affected algorithm or files. For patent concerns, include the patent number, jurisdiction and relevant claims, and explain how the implementation relates to them. Rights holders or authorized representatives may submit notices privately; do not post confidential information in public issues.

The maintainer will review substantiated notices and, where warranted, correct the attribution, modify, temporarily disable, remove, or withdraw the affected implementation from project-controlled code and distributions. Receiving a notice or taking precautionary action is not an admission of infringement.
