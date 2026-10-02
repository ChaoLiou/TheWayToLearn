"""`pacer` 這個跨 agent 入口的漂移防線。

SKILL.md 是給別家 agent 看的唯一說明（`npx skills add` 只搬這個檔），所以這裡擋三件事：
新增 script 忘了接進 `pacer`、SKILL.md 寫了不存在的子指令、以及 `${CLAUDE_PLUGIN_ROOT}` 跑回來。
"""
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cli
import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
LIBS = {"common", "i18n", "blog", "cli"}   # 函式庫，沒有自己的子指令


def scripts_with_main() -> set[str]:
    out = set()
    for f in sorted((ROOT / "scripts").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        if any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body):
            out.add(f.stem)
    return out


def test_every_script_is_reachable():
    assert scripts_with_main() - LIBS == set(cli.COMMANDS)


def test_help_lists_commands(capsys):
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    for name in cli.COMMANDS:
        assert name in out


def test_unknown_command():
    assert cli.main(["nope"]) == 2


def test_paths_runs_without_argv(capsys):
    assert cli.main(["paths"]) == 0
    assert "ROOT" in capsys.readouterr().out


@pytest.mark.parametrize("f", SKILLS, ids=lambda f: f.parent.name)
def test_skill_has_no_plugin_root(f):
    """指令不能再依賴 ${CLAUDE_PLUGIN_ROOT}：別家 agent 沒有這個變數，也沒有 scripts/。"""
    assert "CLAUDE_PLUGIN_ROOT" not in f.read_text(encoding="utf-8")


@pytest.mark.parametrize("f", SKILLS, ids=lambda f: f.parent.name)
def test_skill_commands_exist(f):
    text = f.read_text(encoding="utf-8")
    used = set(re.findall(r"(?<![\w-])pacer ([a-z][a-z-]*)", text)) - {"paths"}
    unknown = {u for u in used if u not in cli.COMMANDS} - {"<子指令>"}
    assert not unknown, f"{f.parent.name} 用了不存在的子指令：{sorted(unknown)}"


@pytest.mark.parametrize("f", SKILLS, ids=lambda f: f.parent.name)
def test_skill_states_how_to_install(f):
    """每份都要能單獨使用，所以安裝說明不能只寫在 /learn 裡。"""
    assert "uv tool install" in f.read_text(encoding="utf-8")


@pytest.mark.parametrize("f", SKILLS, ids=lambda f: f.parent.name)
def test_skill_frontmatter_is_valid_yaml(f):
    """frontmatter 要能被標準 YAML parser 讀。

    Claude Code 的 parser 很寬鬆，`description: [步驟 8/11…` 這種開頭照樣吃；但 YAML 會把開頭的
    `[` 當 flow sequence，標準 parser 直接報錯 —— `npx skills add` 就是這樣默默漏掉 9 個 skill
    （只裝了 5 個）。所以描述以 `[` 或 `{` 開頭時一定要加引號。
    """
    import yaml

    text = f.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f
    meta = yaml.safe_load(text.split("---\n")[1])
    assert meta["name"] == f.parent.name
    assert isinstance(meta["description"], str) and meta["description"].strip()
