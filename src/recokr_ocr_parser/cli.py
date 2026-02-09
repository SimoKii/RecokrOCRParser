from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recokr OCR parser")
    parser.add_argument("--input", required=True, help="OCR JSON 입력 파일 경로")
    parser.add_argument("--output", required=True, help="OCR JSON 출력 파일 경로")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    result = run_pipeline(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
