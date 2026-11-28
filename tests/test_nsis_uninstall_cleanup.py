"""Regression tests for the NSIS uninstaller leaving a non-empty directory.

The defect
----------
A real-machine run on 2026-11-28 (recorded in
``docs/reports/phase5-machine-verification.md`` §5.8.4) showed that, after the
application had been *used* once, a silent NSIS uninstall exited 0 and removed
the registry entry and both shortcuts — but left the install directory on
disk, with ``.dexatlas\\dexatlas.db`` and ``.dexatlas\\projects\\`` inside.
"Installed but never started" uninstalled cleanly, so the difference was the
workspace the first run had created.

Two facts combined:

* the shortcuts' ``WorkingDirectory`` is the install directory, and in the
  installed form the sidecar had no cwd of its own, so ``Settings``' relative
  default ``.dexatlas`` was created *inside the install directory*;
* Tauri's generated uninstaller ends with ``RMDir "$INSTDIR"``, and NSIS's
  ``RMDir`` removes a directory **only when it is empty**.

What is checked
---------------
Tauri generates ``installer.nsi`` at build time, so the project cannot edit
that file; the supported extension point is
``bundle.windows.nsis.installerHooks`` — a ``.nsh`` file whose
``NSIS_HOOK_PREUNINSTALL`` / ``NSIS_HOOK_POSTUNINSTALL`` macros are inserted
into the generated uninstaller. The hooks file is the fix, and this file pins:

* ``tauri.conf.json`` actually wires it, and the path resolves (relative to
  ``desktop/src-tauri/``, as the bundler resolves it);
* the uninstaller removes a **non-empty** ``$INSTDIR`` (``RMDir /r "$INSTDIR"``
  in the post-uninstall hook) — the plain ``RMDir`` in Tauri's template does
  not;
* that recursive delete is guarded: it only runs when the directory was shown
  to be this application's install directory (the main executable was there
  before Tauri deleted it) and not during an update;
* the hook never touches ``%APPDATA%`` (the ``backend.json`` that the MSI path
  preserves byte for byte);
* the root cause is fixed in the sidecar: the installed form pins both its
  cwd and ``DEXATLAS_WORKSPACE`` to
  ``%LOCALAPPDATA%\\<bundle id>\\workspace`` instead of inheriting the
  shortcut's working directory.

Why static assertions are the right level
-----------------------------------------
``installer.nsi`` does not exist until ``tauri build`` runs, and NSIS is not a
dependency of the Python suite; compiling a synthetic installer in the test
would either need the toolchain or skip — and a skip is not a pass. The static
pin catches the failures that matter (a dropped config key, a deleted hook, a
re-introduced relative workspace). The behaviour itself — install, start once,
uninstall, directory gone — is measured on a real machine and recorded in the
report. The ``RMDir /r`` semantics are NSIS's: ``/r`` recurses into
subdirectories, and the plain form only removes a directory when it is empty.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "desktop" / "src-tauri"
TAURI_CONF = TAURI_DIR / "tauri.conf.json"
SIDECAR = TAURI_DIR / "src" / "sidecar.rs"


def _nsis_config() -> dict:
    return json.loads(TAURI_CONF.read_text(encoding="utf-8"))["bundle"]["windows"]["nsis"]


def _hooks_path() -> Path:
    """The hook file the installer is built from.

    The path in ``tauri.conf.json`` is relative to the Tauri project directory
    (``desktop/src-tauri/``), which is where the bundler resolves it from.
    """
    return (TAURI_DIR / _nsis_config()["installerHooks"]).resolve()


def _hooks_text() -> str:
    return _hooks_path().read_text(encoding="utf-8")


def _macro_body(text: str, name: str) -> str:
    start = text.index(f"!macro {name}")
    end = text.index("!macroend", start)
    return text[start:end]


def _code_lines(text: str) -> list[str]:
    """The hook's lines with ``;`` comments removed (NSIS comments)."""
    return [line for line in text.splitlines() if not line.lstrip().startswith(";")]


def test_the_config_points_at_the_hooks_file() -> None:
    """The NSIS installer must be built from the hooks file this test checks."""

    configured = _nsis_config().get("installerHooks")
    assert configured, "bundle.windows.nsis.installerHooks 必须指向卸载钩子文件"
    hooks = _hooks_path()
    assert hooks.is_file(), f"钩子文件不存在：{hooks}"
    assert hooks.suffix == ".nsh", f"installerHooks 应当是 .nsh 文件，实际 {hooks}"
    assert hooks.is_relative_to(TAURI_DIR), f"钩子文件应当放在 desktop/src-tauri/ 下：{hooks}"


def test_the_hooks_are_declared_at_the_top_level() -> None:
    """``Var`` must be outside the macros (NSIS declarations are top-level).

    The hook file is ``!include``-d into the generated script before any
    section, so a top-level ``Var`` compiles; declaring it inside a macro
    would not.
    """

    text = _hooks_text()
    code = _code_lines(text)
    assert "Var DexAtlasOwnInstallDir" in code, "安装目录归属标志必须以顶格 Var 声明"
    assert text.index("Var DexAtlasOwnInstallDir") < text.index("!macro NSIS_HOOK_PREUNINSTALL"), (
        "Var 声明必须在宏之前（NSIS 要求）"
    )


def test_the_hooks_define_both_uninstall_macros() -> None:
    """Tauri only inserts a hook when the macro is defined; both are needed."""

    text = _hooks_text()
    for name in ("NSIS_HOOK_PREUNINSTALL", "NSIS_HOOK_POSTUNINSTALL"):
        body = _macro_body(text, name)
        assert body.strip(), f"{name} 不能是空宏"


def test_the_uninstaller_removes_a_non_empty_install_directory() -> None:
    """The defect itself: a used install directory is not empty.

    Tauri's template does ``RMDir "$INSTDIR"``, which NSIS refuses when the
    directory still has anything in it — and a first run leaves
    ``.dexatlas\\`` there. The post-uninstall hook must delete the directory
    recursively so a non-empty one is actually removed.
    """

    body = _macro_body(_hooks_text(), "NSIS_HOOK_POSTUNINSTALL")
    assert 'RMDir /r "$INSTDIR"' in body, (
        "卸载段必须递归删除 $INSTDIR（RMDir /r）；只做 RMDir 时非空目录删不掉"
    )


def test_the_recursive_delete_is_guarded() -> None:
    """``RMDir /r`` deletes whatever the path says; prove the path is ours.

    ``$INSTDIR`` is read from the registry's ``InstallLocation``. If that value
    were ever wrong, an unguarded recursive delete would remove a directory
    that is not the application's. The pre-uninstall hook records whether the
    main executable was actually there (before Tauri deletes it), and the
    post-uninstall hook only recurses when it was; updates are excluded too,
    because the new version reuses the directory.
    """

    text = _hooks_text()
    pre = _macro_body(text, "NSIS_HOOK_PREUNINSTALL")
    assert '${If} ${FileExists} "$INSTDIR\\${MAINBINARYNAME}.exe"' in pre, (
        "必须用主程序 exe 确认 $INSTDIR 确实是本应用的安装目录"
    )
    assert "StrCpy $DexAtlasOwnInstallDir 1" in pre

    post = _macro_body(text, "NSIS_HOOK_POSTUNINSTALL")
    assert "$DexAtlasOwnInstallDir == 1" in post, "递归删除必须以「目录确实是我们建的」为前提"
    assert "$UpdateMode <> 1" in post, "升级时不能删安装目录（新版本马上要用）"


def test_the_hooks_never_touch_the_roaming_configuration() -> None:
    """``%APPDATA%\\<bundle id>\\backend.json`` is user configuration.

    The MSI path preserves it byte for byte; the NSIS uninstaller (with its
    "delete app data" checkbox left unchecked, the default) must too. The hook
    only operates inside ``$INSTDIR``.
    """

    code = "\n".join(_code_lines(_hooks_text()))
    assert "APPDATA" not in code, "卸载钩子不能删 %APPDATA% 下的配置（backend.json）"
    assert "backend.json" not in code


def test_the_sidecar_pins_the_installed_workspace_to_the_app_local_data_dir() -> None:
    """Root cause: the installed sidecar must not inherit the shortcut's cwd.

    Without this, the uninstaller hook would only be cleaning up a defect that
    keeps recurring on every run.
    """

    source = SIDECAR.read_text(encoding="utf-8")
    assert "fn backend_cwd(" not in source, (
        "旧的 backend_cwd() 在安装形态返回 None（继承启动器 cwd），必须由 BackendLaunch 取代"
    )
    assert "app_local_data_dir()" in source, "安装形态的工作区必须挂在应用本地数据目录下"
    assert 'join("workspace")' in source
    assert 'command.env("DEXATLAS_WORKSPACE", dir)' in source, (
        "安装形态必须显式把工作区告诉后端，而不是依赖相对路径"
    )
