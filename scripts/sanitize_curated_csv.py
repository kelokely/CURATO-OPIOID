#!/usr/bin/env python3
"""Write public-safe copies of curated CSV tables."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


PATH_RE = re.compile(r"(?:/Users|/project|/gscratch|/cluster|/Volumes)/[^\s,;|]+")


def scrub_value(value: object) -> object:
    if not isinstance(value, str):
        return value

    def repl(match: re.Match[str]) -> str:
        path = Path(match.group(0))
        return path.name or "[redacted-path]"

    return PATH_RE.sub(repl, value)


def sanitize_csv(src: Path, dst: Path, chunksize: int = 50000) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    first = True
    for chunk in pd.read_csv(src, chunksize=chunksize, low_memory=False):
        object_cols = chunk.select_dtypes(include=["object", "str"]).columns
        for col in object_cols:
            chunk[col] = chunk[col].map(scrub_value)
        chunk.to_csv(dst, index=False, mode="w" if first else "a", header=first)
        first = False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("--chunksize", type=int, default=50000)
    args = parser.parse_args()
    sanitize_csv(args.src, args.dst, chunksize=args.chunksize)


if __name__ == "__main__":
    main()
