# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_automasi.py'],
    pathex=[],
    binaries=[],
    datas=[('tombol_preview.png', '.'), ('tombol_next.png', '.')],
    hiddenimports=['tkcalendar', 'babel.numbers'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'numpy', 'cv2', 'scipy', 'matplotlib', 'pyarrow', 'psycopg2', 'psycopg', 'torch', 'sklearn', 'IPython', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'notebook', 'pytest', 'sqlalchemy', 'pymupdf4llm', 'pymupdf_layout'],
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
    name='AutomasiNota',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
