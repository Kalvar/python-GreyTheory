"""Generate synthetic XRF data and run the bundled AI handwriting style demo."""

import argparse
from pathlib import Path

if __package__:
    from .demos import run_handwriting_demo, run_xrf_demo
    from .demos._report import report
else:
    from demos import run_handwriting_demo, run_xrf_demo
    from demos._report import report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", choices=("all", "xrf", "handwriting"), default="all")
    parser.add_argument("--output", type=Path, default=Path("artifacts/synthetic_demos"))
    args = parser.parse_args(argv)
    if args.demo in {"all", "xrf"}:
        result = run_xrf_demo(args.output / "xrf")
        print("Synthetic XRF report:", result["report"].resolve())
        for row in result["summary"]["metrics"]:
            print(row)
    if args.demo in {"all", "handwriting"}:
        result = run_handwriting_demo(args.output / "handwriting")
        print("AI handwriting STYLE report:", result["report"].resolve())
        for row in result["summary"]["metrics"]:
            print(row)
    if args.demo == "all":
        report(args.output / "index.html", "合成光譜與 AI 筆跡 demo",
               "兩組可重現的輸入與數值分析；沒有使用外部儀器樣本或真實筆跡。",
               [("合成 XRF 光譜", '<p>144 組光譜、EMSA/MSA 交換檔、已知混合權重與 PCA／GreyPCA 比較。</p>'
                 '<p><a href="xrf/index.html">開啟光譜報告</a></p><img src="xrf/spectra_and_ranking.svg" alt="Synthetic XRF spectra">'),
                ("AI 筆跡風格比對", '<p>18 格 AI 合成筆跡；12 格參考、6 格查詢。風格標籤不代表真實作者。</p>'
                 '<p><a href="handwriting/index.html">開啟筆跡報告</a></p>'
                 '<img src="handwriting/style_embeddings.svg" alt="Synthetic handwriting style embeddings">')])
        print("Demo index:", (args.output / "index.html").resolve())


if __name__ == "__main__":
    main()
