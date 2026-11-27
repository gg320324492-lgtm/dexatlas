"""Regression tests for the MSI's repair path (Phase 5, defect A8).

The defect
----------
Installing the MSI on a real machine (2026-11-27) and then deleting the
installed ``Uninstall DexAtlas Studio.lnk`` showed that ``msiexec /fa`` did
**not** bring the shortcut back. The install log had no ``ShortcutCreate``
operation at all: the installer never tried to rebuild the shortcut.

What the measurement said
-------------------------
Three control runs on the same machine, same MSI, only the reinstall mode
differing:

======================  ==================  =====================
command                 REINSTALLMODE        shortcut came back
======================  ==================  =====================
``msiexec /fa``         ``a``                no
``msiexec /fas``        ``as``               **yes**
``msiexec /fa`` (exe    ``a``                no
also deleted)
======================  ==================  =====================

So the deciding factor is the ``s`` flag of ``REINSTALLMODE`` ("re-install
shortcuts"), not the key path of the component that owns the shortcut: with
the shortcut moved into the component whose key path is the ``.exe`` and the
mode still ``a``, the shortcut was *still* not rebuilt.

Two more facts from the same logs, both of which this file pins down:

* the flag has to be in place **before the costing phase**
  (``CostInitialize``/``FileCost``/``CostFinalize``) — the set of shortcuts
  to rebuild is decided there, not by the ``CreateShortcuts`` action;
* ``msiexec /fa`` sets ``REINSTALLMODE=a`` on the command line, and that
  value is written before the sequence starts, so the value in the Property
  table (``amus``) does not survive it. Marking the property ``Secure``
  does not change that (measured: the value was still ``a``).

Hence the fix in the template: a type 51 custom action scheduled before
``CostInitialize`` appends the ``s`` flag to whatever mode was asked for.

What is checked
---------------
The MSI's tables come from ``desktop/src-tauri/wix/main.wxs`` — a fork of
tauri-bundler's template — so the tables can be checked without building an
installer. The built MSI is checked by hand as well; see
``docs/desktop-packaging.md`` for the procedure and its recorded result.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
TAURI_DIR = DESKTOP / "src-tauri"
TAURI_CONF = TAURI_DIR / "tauri.conf.json"
WIX_NS = "{http://schemas.microsoft.com/wix/2006/wi}"


def _wix_config() -> dict:
    return json.loads(TAURI_CONF.read_text(encoding="utf-8"))["bundle"]["windows"]["wix"]


def _template_path() -> Path:
    """The template the MSI is built from.

    The path in ``tauri.conf.json`` is relative to the Tauri project
    directory (``desktop/src-tauri/``), which is where the bundler resolves
    it from — not to the shell's working directory.
    """
    return (TAURI_DIR / _wix_config()["template"]).resolve()


def _root() -> ET.Element:
    return ET.parse(_template_path()).getroot()


def _component_of_shortcut(root: ET.Element, shortcut_id: str) -> ET.Element:
    parent = {child: node for node in root.iter() for child in node}
    for shortcut in root.iter(f"{WIX_NS}Shortcut"):
        if shortcut.get("Id") == shortcut_id:
            component = parent.get(shortcut)
            assert component is not None, f"{shortcut_id} 不在任何组件里"
            return component
    raise AssertionError(f"模板里没有 {shortcut_id} 这个快捷方式")


def _property(root: ET.Element, prop_id: str) -> ET.Element | None:
    for prop in root.iter(f"{WIX_NS}Property"):
        if prop.get("Id") == prop_id:
            return prop
    return None


def _custom_action(root: ET.Element, action_id: str) -> ET.Element:
    for action in root.iter(f"{WIX_NS}CustomAction"):
        if action.get("Id") == action_id:
            return action
    raise AssertionError(f"模板里没有 {action_id} 这个自定义动作")


def _sequence(root: ET.Element, sequence_id: str) -> ET.Element:
    for sequence in root.iter(f"{WIX_NS}{sequence_id}"):
        return sequence
    raise AssertionError(f"模板里没有 {sequence_id} 序列")


def test_the_config_points_at_the_forked_template() -> None:
    """The MSI must be built from the template this file checks."""

    template = _template_path()
    assert template.is_file(), f"模板不存在：{template}"
    assert template.parent.name == "wix", (
        f"模板应当放在 desktop/src-tauri/wix/ 下，实际在 {template}"
    )


def test_the_shortcut_flag_is_added_before_the_costing_phase() -> None:
    """The ``s`` flag has to be in place before the installer decides.

    ``msiexec /fa`` puts ``REINSTALLMODE=a`` on the command line, and that
    value is written before the sequence starts — the value in the Property
    table does not survive it, and marking the property ``Secure`` does not
    help (measured). The set of shortcuts to rebuild is decided during the
    costing phase, so the flag has to be added before ``CostInitialize``.
    """

    root = _root()
    action = _custom_action(root, "ReinstallShortcutsToo")
    assert action.get("Property") == "REINSTALLMODE", (
        "自定义动作改的不是 REINSTALLMODE，重装快捷方式的标志就加不上去"
    )
    value = action.get("Value") or ""
    assert "[REINSTALLMODE]" in value and "s" in value, (
        f"自定义动作的 Value 是 {value!r}；它应当在原有的标志后面补一个 s"
    )

    sequence = _sequence(root, "InstallExecuteSequence")
    entries = {child.get("Action"): child for child in sequence if child.get("Action") is not None}
    assert "ReinstallShortcutsToo" in entries, (
        "ReinstallShortcutsToo 没有排进 InstallExecuteSequence"
    )
    entry = entries["ReinstallShortcutsToo"]
    assert entry.get("Before") == "CostInitialize" or entry.get("After") in (
        "ValidateProductID",
        "AppSearch",
        "FindRelatedProducts",
    ), (
        "补标志的动作必须排在成本计算（CostInitialize/FileCost/CostFinalize）之前，"
        f"现在排在 {entry.get('Before') or entry.get('After')}"
    )


def test_the_uninstall_shortcut_is_keyed_on_a_file() -> None:
    """The component that owns the shortcut is keyed on a file, not on a registry value.

    This is **not** what makes the repair work (measured: with the shortcut in
    a file-keyed component and the mode still ``a``, the shortcut was not
    rebuilt). It is kept because the upstream component that owned the
    shortcut had its key path in ``HKCU`` while the shortcut itself is written
    into the per-machine installation directory, so the component's state and
    the shortcut's presence could drift apart.
    """

    root = _root()
    component = _component_of_shortcut(root, "UninstallShortcut")

    keyed_files = [
        f.get("Id") for f in component.findall(f"{WIX_NS}File") if f.get("KeyPath") == "yes"
    ]
    assert keyed_files, (
        "UninstallShortcut 所在组件的 KeyPath 必须是文件；"
        "KeyPath 是注册表值时，组件的状态与快捷方式的去留会脱节"
    )

    keyed_registry = [
        r.get("Name")
        for r in component.findall(f"{WIX_NS}RegistryValue")
        if r.get("KeyPath") == "yes"
    ]
    assert not keyed_registry, f"组件的 KeyPath 不该是注册表值 {keyed_registry}"


def test_the_uninstall_shortcut_sits_with_the_executable() -> None:
    """The shortcut's component is the one that owns the .exe."""

    root = _root()
    component = _component_of_shortcut(root, "UninstallShortcut")
    file_ids = {f.get("Id") for f in component.findall(f"{WIX_NS}File")}
    assert "Path" in file_ids, (
        "卸载快捷方式应当与 exe 在同一个组件里（组件的 KeyPath 是 exe），"
        f"实际组件 {component.get('Id')} 里的文件是 {sorted(file_ids)}"
    )


def test_per_user_shortcuts_are_not_mixed_into_the_machine_component() -> None:
    """ICE57: a component may not mix per-machine and per-user data.

    The Start Menu and Desktop shortcuts live in the user's profile, so they
    cannot join the component whose key path is the .exe under Program Files.
    They stay in their own components; the repair path for them is the same
    ``s`` flag, which rebuilds every shortcut in the table.
    """

    root = _root()
    machine_component = _component_of_shortcut(root, "UninstallShortcut")
    for shortcut_id in ("ApplicationStartMenuShortcut", "ApplicationDesktopShortcut"):
        component = _component_of_shortcut(root, shortcut_id)
        assert component is not machine_component, (
            f"{shortcut_id} 在用户的配置文件里，不能放进以 exe 为 KeyPath 的"
            "per-machine 组件（ICE57）"
        )


def test_the_repair_entry_is_not_switched_off() -> None:
    """The Control Panel's repair entry has to exist.

    ``ARPNOREPAIR`` is what switched it off; with it set, the only repair
    route left was the command line — and that route could not restore the
    shortcut either.
    """

    root = _root()
    prop = _property(root, "ARPNOREPAIR")
    if prop is None:
        return
    value = (prop.get("Value") or "").strip().lower()
    assert value not in ("yes", "1", "true"), f"ARPNOREPAIR={value} 会把控制面板的「修复」入口关掉"
