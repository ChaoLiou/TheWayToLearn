"""印出「第幾步 / 共幾步」的進度行。script 階段會自己印；agent 自己做的階段（segment、analyze、
以及 atlas 的彙整）跑完後呼叫這支，格式才一致。

  uv run scripts/progress.py segment ["附註"]
  uv run scripts/progress.py --list        # 列出所有步驟
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import STEPS, print_step


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?", choices=[k for k, _ in STEPS])
    ap.add_argument("note", nargs="?", default="")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list or not args.stage:
        for i, (k, zh) in enumerate(STEPS, 1):
            print(f"[{i}/{len(STEPS)}] {k:<9} {zh}")
        return
    print_step(args.stage, args.note)


if __name__ == "__main__":
    main()
