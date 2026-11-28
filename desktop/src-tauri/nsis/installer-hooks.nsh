; DexAtlas Studio 的 NSIS 卸载钩子。
;
; 缺陷（2026-11-28 真机实测，docs/reports/phase5-machine-verification.md §5.8.4）：
; Tauri 模板生成的卸载器只做 `RMDir "$INSTDIR"`，而 NSIS 的 RMDir 只在
; 目录为空时才删掉它。1.2.0 及更早的安装形态下，侧车没有自己的 cwd，继承了
; 启动器的 cwd——快捷方式的 WorkingDirectory 就是安装目录——于是相对路径
; 的工作区 `.dexatlas` 被建在安装目录里。用户只要启动过一次，卸载后安装
; 目录就留在磁盘上，而控制面板里的卸载项已经没了。
;
; 根因修复在应用侧（desktop/src-tauri/src/sidecar.rs）：安装形态把侧车的
; cwd 与 DEXATLAS_WORKSPACE 显式指到 %LOCALAPPDATA%\<bundle id>\workspace。
; 这个文件是卸载器的兜底，管两件事：
;
;   1. 旧版本可能已经把 `.dexatlas` 留在了安装目录里——本钩子把它们连同
;      安装目录一起删掉，用户看到的才是真的卸载干净。
;   2. Tauri 模板本身只删它认识的文件，任何它没列出的残留都会让最后的
;      `RMDir "$INSTDIR"` 失败；这里用 `RMDir /r "$INSTDIR"` 收尾。
;
; **删的是什么**：$INSTDIR 是安装器在安装时选定的目录，里面是 DexAtlas Studio
; 自己的程序文件，以及旧版本错误地建进去的工作区（分析数据库，属于用户数据，
; 但它住在安装目录里——卸载时随目录一起走）。用户设置 `%APPDATA%\<bundle id>\
; backend.json` **不在** $INSTDIR 里，本钩子不碰它。卸载器自带的「删除应用数据」
; 复选框（默认不勾，静默模式跳过）才会删除 %APPDATA% / %LOCALAPPDATA% 下的
; 应用目录。
;
; **不删的情况**：
;   - 升级（$UpdateMode = 1）：安装目录马上要被新版本使用，旧工作区留在原处
;     （新版本改用 %LOCALAPPDATA%，不会覆盖它；下次卸载时再随目录清理）；
;   - $INSTDIR 里没有主程序 exe：$INSTDIR 来自注册表 InstallLocation，路径
;     可能被改坏。没有这层校验，一个指错的路径会被 `RMDir /r` 整个删掉。

Var DexAtlasOwnInstallDir

!macro NSIS_HOOK_PREUNINSTALL
  ; 在 Tauri 删除主程序之前判断：这个目录确实是本应用的安装目录吗？
  ${If} ${FileExists} "$INSTDIR\${MAINBINARYNAME}.exe"
    StrCpy $DexAtlasOwnInstallDir 1
  ${Else}
    StrCpy $DexAtlasOwnInstallDir 0
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  ; 此时 Tauri 已经删完它认识的文件、快捷方式和注册表项。
  ${If} $DexAtlasOwnInstallDir == 1
  ${AndIf} $UpdateMode <> 1
    RMDir /r "$INSTDIR"
  ${EndIf}
!macroend