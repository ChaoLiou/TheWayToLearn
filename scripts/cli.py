"""`pacer <子指令>`：跨 agent 的統一入口。

為什麼需要：SKILL.md 原本寫 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" …/scripts/x.py`，
那是 Claude Code 才有的環境變數。裝到 Cursor / Codex / Gemini CLI 之類的 agent 時，
`npx skills add` 只會搬 SKILL.md，不會搬 `scripts/`，所以相對路徑一定找不到檔案。

這支把每個 script 的 main() 收成一個 console script，安裝之後哪個 cwd 都能跑：

  uv tool install git+https://github.com/TheWayToLearn/PACER-Learn   # 裝一次，之後 `pacer …`
  uvx --from git+https://github.com/TheWayToLearn/PACER-Learn pacer paths   # 不安裝，跑一次

rules / config / templates / schemas 跟著 wheel 一起裝（見 pyproject 的 wheel sources），
而 common.ROOT 是從 `__file__` 往上推兩層，所以安裝後一樣找得到，不依賴 cwd。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# 子指令 → 模組名（= scripts/<名>.py）。只收有 main() 的，common / i18n / blog 是函式庫。
COMMANDS = {
    "atlas": "atlas", "brain": "brain", "digest": "digest", "estimate": "estimate",
    "fetch": "fetch", "listen": "listen", "narrate": "narrate", "notes": "notes",
    "options": "options", "paths": "paths", "playlist": "playlist", "progress": "progress",
    "prune": "prune", "publish": "publish", "render": "render", "screenshot": "screenshot",
    "validate": "validate",
}


def usage() -> str:
    from common import ROOT
    lines = [f"pacer <子指令> [參數…]    （程式根目錄 {ROOT}）", "", "子指令："]
    lines += ["  " + "  ".join(sorted(COMMANDS)[i:i + 5]) for i in range(0, len(COMMANDS), 5)]
    lines += ["", "每個子指令的參數跟 scripts/<子指令>.py 一樣，例如：",
              "  pacer paths", "  pacer estimate <url>", "  pacer validate segments <file.json>"]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0
    sub, rest = argv[0], argv[1:]
    if sub not in COMMANDS:
        print(f"沒有這個子指令：{sub}\n\n{usage()}", file=sys.stderr)
        return 2
    mod = importlib.import_module(COMMANDS[sub])
    # paths.py 的 main() 不收參數；其餘都是 main(argv=None)
    try:
        ret = mod.main(rest) if rest or sub != "paths" else mod.main()
    except TypeError:
        ret = mod.main()
    return 0 if ret is None else int(ret)


if __name__ == "__main__":
    raise SystemExit(main())
