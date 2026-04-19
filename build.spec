# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集 PaddleOCR 相关的数据文件
datas = [
    ('paddleocr.py', '.'),
    ('paddle', 'paddle'),
]

# 收集 PaddleOCR 子模块
hiddenimports = [
    'paddle',
    'paddleocr',
    'paddleocr.ppocr',
    'paddleocr.ppocr.utils',
    'paddleocr.ppocr.utils.network',
    'paddleocr.ppocr.utils.logging',
    'paddleocr.ppocr.utils.utility',
    'paddleocr.ppocr.post_processing',
    'paddleocr.ppocr.predict_system',
    'paddleocr.ppocr.det',
    'paddleocr.ppocr.rec',
    'paddleocr.ppocr.cls',
    'paddleocr.tools',
    'paddleocr.tools.infer',
    'paddle.inference',
    'shapely',
    'shapely.geometry',
    'pyclipper',
    'psutil',
    'pyclipper',
    'scipy',
    'scipy.spatial',
    'scipy.spatial.qhull',
    'six',
    'lmdb',
    'pyyaml',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('config.py', '.'),
    ] + collect_data_files('paddleocr') + collect_data_files('paddle'),
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'torch',
        'tensorflow',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='handwritten-ocr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为 False 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可设置图标: icon='app.ico'
)
