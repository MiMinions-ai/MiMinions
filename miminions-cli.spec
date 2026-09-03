# -*- mode: python ; coding: utf-8 -*-
"""Single source of truth for the standalone CLI binary build.

Every setting below is load-bearing; see
memory/past/adrs/0008-cli-binary-build-flags.md. PyInstaller builds succeed even
when one is missing, and the resulting binary then fails at runtime.

Build with: pyinstaller --clean miminions-cli.spec
"""

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# cli/main.py resolves command groups through importlib at invocation time, so
# static analysis cannot discover them.
hiddenimports = collect_submodules("miminions")

# These packages read their own version via importlib.metadata at runtime.
datas = []
for _package in ("miminions", "pydantic-ai-slim", "genai_prices"):
    datas += copy_metadata(_package)

a = Analysis(
    ["src/miminions/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # logfire arrives transitively via pydantic-ai and patches pydantic through
    # inspect.getsource, which has no source to read inside a frozen bundle.
    # logfire_api is a different package, is required by pydantic_graph, and
    # must NOT be excluded.
    excludes=["logfire"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="miminions-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
