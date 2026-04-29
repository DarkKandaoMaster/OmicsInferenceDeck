"""转换为Gene Symbol

mRNA的特征原本是 A2BP1|54715 这种。
所以我先写一份Python代码，把特征名按 | 拆分，在该目录下生成一个特征名为纯Entrez ID的文件
然后编写R代码并通过subprocess调用，在该目录下生成一个特征名为标准的Gene Symbol的文件
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path


DEFAULT_INPUT = "rna.fea"
DEFAULT_ENTREZ_OUTPUT = "rna_entrez.fea"
DEFAULT_SYMBOL_OUTPUT = "rna_symbol.fea"
R_SCRIPT = "temp.R"


def convert_feature_to_entrez(input_path: Path, output_path: Path) -> None:
    """Replace the first CSV column from SYMBOL|ENTREZID to pure ENTREZID."""
    with input_path.open("r", newline="", encoding="utf-8") as src, output_path.open(
        "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.reader(src)
        writer = csv.writer(dst, lineterminator="\n")

        header = next(reader, None)
        if header is None:
            raise ValueError(f"{input_path} is empty")

        writer.writerow(header)

        for line_no, row in enumerate(reader, start=2):
            if not row:
                continue

            feature = row[0]
            parts = feature.rsplit("|", 1)
            if len(parts) != 2 or not parts[1]:
                raise ValueError(
                    f"Line {line_no}: first column is not in SYMBOL|ENTREZID format: {feature!r}"
                )

            row[0] = parts[1]
            writer.writerow(row)


def run_r_mapping(entrez_path: Path, symbol_path: Path, r_script: Path) -> None:
    cmd = [
        "Rscript",
        str(r_script),
        "--input",
        str(entrez_path),
        "--output",
        str(symbol_path),
    ]
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert mRNA feature names from SYMBOL|ENTREZID to ENTREZID and current Gene Symbol."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV/FEA file.")
    parser.add_argument(
        "--entrez-output",
        default=DEFAULT_ENTREZ_OUTPUT,
        help="Output file whose first column is pure Entrez ID.",
    )
    parser.add_argument(
        "--symbol-output",
        default=DEFAULT_SYMBOL_OUTPUT,
        help="Output file whose first column is standard Gene Symbol.",
    )
    parser.add_argument(
        "--r-script",
        default=R_SCRIPT,
        help="R script used to map Entrez IDs to Gene Symbols.",
    )
    parser.add_argument(
        "--skip-r",
        action="store_true",
        help="Only generate the pure Entrez ID file and do not call R.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent

    input_path = (base_dir / args.input).resolve()
    entrez_path = (base_dir / args.entrez_output).resolve()
    symbol_path = (base_dir / args.symbol_output).resolve()
    r_script = (base_dir / args.r_script).resolve()

    convert_feature_to_entrez(input_path, entrez_path)
    print(f"Wrote Entrez ID feature file: {entrez_path}")

    if not args.skip_r:
        run_r_mapping(entrez_path, symbol_path, r_script)
        print(f"Wrote Gene Symbol feature file: {symbol_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
