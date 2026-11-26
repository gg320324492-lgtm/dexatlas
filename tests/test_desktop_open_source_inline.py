"""「打开来源」在文件内 locator 上真的给出源码 —— 文案与行为对齐.

P3 修复(PR #17)让没有单文件落点的 locator(包级、DEX 内、后端未完成)
禁用并给出可见说明,但文件内 locator(``jadx:`` / ``apktool:``)点了仍是
一个 ``window.alert``,文案写着「来源文件(后端解析)」而它既不解析也不
打开文件——文案与行为有出入(phase5-acceptance 走查项 9).

修复后的行为:点击「打开来源」调用后端 ``/locators/resolve``(后端本就
返回源码文本、真实路径、字节数与截断标记,无需新端点),源码在抽屉内
内联展示,附解析出的真实路径与行数/字节这类可核对的信息;按钮不再弹
alert,「后端解析」四个字只出现在真的解析了的场合.

桌面行为单测跑在 vitest(``desktop/src/locators.test.ts``);这里按本仓库
桌面回归的惯例读源码文本守卫接线(与 ``test_desktop_stale_copy.py`` 同
法——真要渲染组件需要一套 DOM 脚手架,那是 vitest 的事).每条针对修复
的断言在修复前的树上都是红的.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_DETAIL = ROOT / "desktop" / "src" / "pages" / "ProjectDetail.tsx"
PROJECT_DETAIL_CSS = ROOT / "desktop" / "src" / "pages" / "ProjectDetail.css"
LOCATORS = ROOT / "desktop" / "src" / "locators.ts"


def _source(path: Path) -> str:
    """The text of a file that must exist for this behaviour to be there."""
    assert path.is_file(), f"{path} does not exist"
    return path.read_text(encoding="utf-8")


def _button_region(source: str, span: int = 900) -> str:
    """The source that precedes the 「打开来源」 button's label.

    The label is the string literal in the busy/idle ternary, so anchor on
    it rather than on a JSX text node.
    """
    at = source.find('"打开来源"')
    assert at > -1, "ProjectDetail.tsx no longer renders a 打开来源 button"
    return source[max(0, at - span) : at]


def _search(source: str, pattern: str) -> int:
    match = re.search(pattern, source)
    return match.start() if match else -1


def test_open_source_no_longer_alerts() -> None:
    """The button must not answer a click with a window.alert any more.

    The alert was the defect: its text claimed the backend had resolved the
    locator while nothing had been resolved and nothing was shown. Red on
    the pre-fix tree, where the onClick body is the alert call itself.
    """
    source = _source(PROJECT_DETAIL)
    assert "window.alert(" not in source, (
        "「打开来源」仍在用 window.alert: 文案与行为不符的旧实现回来了"
    )


def test_open_source_click_resolves_instead_of_alerting() -> None:
    """The click handler must go to the backend resolve, not to an alert.

    「打开来源」and「resolve」share one mechanism now: the click resolves
    the locator, and the drawer shows what came back.
    """
    region = _button_region(_source(PROJECT_DETAIL))
    assert "resolveSelected" in region, (
        "「打开来源」的 onClick 没有走后端 resolve —— 点击行为仍是弹窗一类"
    )


def test_inline_source_panel_renders_path_and_verifiable_meta() -> None:
    """The drawer body renders the resolved source with checkable facts.

    「真的给出源码」要能核对: 解析出的真实路径、行数、字节数必须一起
    展示, 代码块可滚动。缺了路径, 源码就没有落点; 缺了大小/行数, 截断
    就说不清。
    """
    source = _source(PROJECT_DETAIL)
    assert "inlineSourceOf(" in source, "抽屉没有从 resolve 响应里提取源码视图"
    assert "da-ev-source" in source, "抽屉 body 没有内联源码面板的容器"
    assert re.search(r"inlineSource\.path", source), "内联源码面板没有展示解析出的真实路径"
    assert re.search(r"inlineSource\.lines", source) and re.search(
        r"inlineSource\.bytesLabel", source
    ), "内联源码面板没有展示行数与字节数这类可核对的信息"
    assert re.search(r"inlineSource\.truncated", source), "截断的源码必须如实说明自己被截断了"


def test_locators_module_derives_the_source_view() -> None:
    """locators.ts extracts the source view from the resolve response.

    后端 ``resolve_locator`` 成功时 ``reason`` 是解析出的真实路径,
    ``text`` 携带源码与字节数/截断标记(mcp/tools/evidence.py, 无需新端
    点)。前端要有一个纯函数从响应里取这些, 而不是在组件里散着取。
    """
    source = _source(LOCATORS)
    assert re.search(r"export function inlineSourceOf\(", source), (
        "locators.ts 缺少 inlineSourceOf: 源码视图的提取逻辑不在场"
    )
    assert re.search(r"export function formatBytes\(", source), (
        "locators.ts 缺少 formatBytes: 字节数没有人类可读的展示"
    )
    assert "truncated" in source and "bytes" in source, (
        "inlineSourceOf 必须透传后端的截断标记与字节数"
    )
    detail = _source(PROJECT_DETAIL)
    assert "inlineSourceOf" in detail, "ProjectDetail.tsx 没有使用 locators 的 inlineSourceOf"


def test_inline_source_block_is_a_scrollable_mono_code_block() -> None:
    """The CSS backs the panel with a scrollable monospace block.

    展示形态与既有证据抽屉一致: 等宽字体、可滚动、路径可换行。没有这
    条样式, 面板要么撑破抽屉要么被截死。
    """
    css = _source(PROJECT_DETAIL_CSS)
    at = _search(css, r"\.da-ev-source__code")
    assert at > -1, "ProjectDetail.css 没有源码块的样式"
    scope = css[at : at + 400]
    assert "--font-mono" in scope, "源码块不是等宽字体"
    assert "overflow" in scope, "源码块不可滚动"
    assert "max-height" in scope, "源码块没有高度上限, 会把抽屉撑开"


def test_disabled_note_for_non_file_locators_still_visible() -> None:
    """P3 的行为不许被这次改动碰坏: 无落点仍禁用且说明可见。

    这条在修复前后都是绿的——它是护栏, 不是回归。
    """
    source = _source(PROJECT_DETAIL)
    assert re.search(r"disabled=\{[^}]*openSource[^}]*\}", source), "按钮的 disabled 接线不见了"
    assert "openSource.note &&" in source, "禁用时的可见说明不见了"
    assert 'id="da-ev-open-source-hint"' in source, "说明的 aria 锚点不见了"
