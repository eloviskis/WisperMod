# wispermod.spec  — PyInstaller build spec para Windows
# Gerado para: Python 3.11, PyInstaller >= 6.3, --onedir

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Coletar todos os dados/binários/imports dos pacotes pesados
datas_torch,   bins_torch,   hi_torch   = collect_all("torch")
datas_whisper, bins_whisper, hi_whisper = collect_all("whisper")
datas_ctk,     _,            hi_ctk     = collect_all("customtkinter")
datas_tiktoken,_,            hi_tiktoken= collect_all("tiktoken")

a = Analysis(
    ["desktop_app.py"],
    pathex=["."],                       # permite importar o pacote core/
    binaries=bins_torch + bins_whisper,
    datas=[
        ("models", "models"),           # modelo Whisper small.pt
        ("bin",    "bin"),              # ffmpeg.exe
    ]
    + datas_torch
    + datas_whisper
    + datas_ctk
    + datas_tiktoken,
    hiddenimports=[
        # pacote local
        "core",
        "core.processador",
        # whisper
        "whisper",
        "whisper.audio",
        "whisper.model",
        "whisper.tokenizer",
        "whisper.transcribe",
        "whisper.decoding",
        "whisper.normalizers",
        "whisper.timing",
        # tiktoken
        "tiktoken",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
        # ui / sistema
        "customtkinter",
        "_tkinter",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        # numpy / numba
        "numpy",
        "numpy.core._multiarray_umath",
        "numba",
        "numba.core",
    ]
    + hi_torch
    + hi_whisper
    + hi_ctk
    + hi_tiktoken,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # reduzir tamanho — não usados pelo app
        "matplotlib",
        "scipy",
        "PIL",
        "Pillow",
        "cv2",
        "flask",
        "django",
        "fastapi",
        "uvicorn",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WisperMod",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # coloque "assets/icon.ico" se tiver um ícone
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WisperMod",
)
