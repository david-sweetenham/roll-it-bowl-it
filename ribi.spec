# ribi.spec — PyInstaller packaging spec for Roll It & Bowl It
# Not used during development. Run with: pyinstaller ribi.spec
# Requires: pip install pyinstaller

block_cipher = None

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('schema.sql', '.'),
        ('seed_data.py', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'flask',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['config_dev'],  # Never include dev config in builds
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RollItBowlIt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set True temporarily if debugging packaging issues
    icon=None,      # Add path to .ico file when available
)
