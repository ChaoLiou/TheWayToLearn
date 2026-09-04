"""印出目前生效的路徑：plugin/repo 根、workspace、每個規則檔實際讀哪裡。/learn 第一步先跑，agent 照這個讀規則。

  uv run scripts/paths.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    ROOT,
    config_file,
    override_dir,
    rule_file,
    template_dirs,
)

RULES = ["narrative.md", "segment.md", "overview.md", "output.md", "atlas.md"]


def main():
    print(f"ROOT       {ROOT}")
    print(f"WORKSPACE  {DEFAULT_WORKSPACE}   （$LEARN_WORKSPACE 可改）")
    od = override_dir()
    print(f"OVERRIDE   {od}   {'（存在）' if od.exists() else '（不存在；要客製就建這個目錄，放同名檔案）'}")
    for r in RULES:
        p = rule_file(r)
        print(f"  rules/{r:<14} → {p}{'   ★ 覆寫' if p.parent == od else ''}")
    p = config_file("estimate.yaml")
    print(f"  config/estimate.yaml → {p}{'   ★ 覆寫' if p.parent == od else ''}")
    print(f"  templates            → {template_dirs()[0]}{'   ★ 覆寫' if len(template_dirs()) > 1 else ''}")


if __name__ == "__main__":
    main()
