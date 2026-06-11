# PyInstaller spec — Steam-ready Windows build (G35 platform decisions).
# Build:  pip install pyinstaller && pyinstaller aphelion.spec
# Output: dist/APHELION/APHELION.exe (folder mode: fast start, easy patching)

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["aphelion/main.py"],
    pathex=["."],
    datas=[("data", "data"), ("design/README.md", "design")],
    hiddenimports=collect_submodules("aphelion"),
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="APHELION",
    console=False,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="APHELION")
