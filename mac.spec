# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for macOS application bundle (.app)

生成 macOS 应用包: handwritten-ocr.app
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集数据文件
datas = [
    ('src', 'src'),
    ('config.py', '.'),
]

# 尝试收集 paddle 和 paddleocr 的数据文件
try:
    datas += collect_data_files('paddleocr', include_py_files=False)
except Exception:
    pass

try:
    datas += collect_data_files('paddle', include_py_files=False)
except Exception:
    pass

try:
    datas += collect_data_files('shapely', include_py_files=False)
except Exception:
    pass

# PaddlePaddle 3.0 模块
hiddenimports = [
    # PaddlePaddle 3.0
    'paddle',
    'paddle.base',
    'paddle.base.core',
    'paddle.base.framework',
    'paddle.base.executor',
    'paddle.inference',
    'paddle.framework',
    'paddle.framework.ir',
    'paddle.tensor',
    'paddle.device',
    'paddle.dataset',
    'paddle.reader',
    'paddle.distributed',
    'paddle.nn',
    'paddle.nn.layer',
    'paddle.nn.functional',
    'paddle.optimizer',
    'paddle.io',
    'paddle._C_ops',
    
    # PaddleOCR
    'paddleocr',
    'paddleocr.paddleocr',
    'paddleocr.ppocr',
    'paddleocr.ppocr.utils',
    'paddleocr.ppocr.utils.utility',
    'paddleocr.ppocr.utils.logging',
    'paddleocr.ppocr.utils.network',
    'paddleocr.ppocr.utils.e2e_utils',
    'paddleocr.ppocr.post_processing',
    'paddleocr.ppocr.post_processing.db_postprocess',
    'paddleocr.ppocr.data',
    'paddleocr.ppocr.data.imaug',
    'paddleocr.ppocr.data.imaug.operators',
    'paddleocr.ppocr.data.dataset',
    'paddleocr.ppocr.predict_system',
    'paddleocr.ppocr.architecture',
    'paddleocr.tools',
    'paddleocr.tools.infer',
    'paddleocr.tools.infer.utility',
    
    # 依赖
    'shapely',
    'shapely.geometry',
    'shapely.ops',
    'pyclipper',
    'psutil',
    'scipy',
    'scipy.spatial',
    'scipy.spatial.qhull',
    'scipy.special',
    'scipy.sparse',
    'six',
    'lmdb',
    'pyyaml',
    'yaml',
    'tqdm',
    'tqdm.auto',
    'attrs',
    
    # 图像处理
    'cv2',
    'PIL',
    'PIL.Image',
    
    # 数值计算
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy.fft',
    'numpy.linalg',
    
    # 数据处理
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'pandas.core',
    'pandas.io',
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.styles',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.writer',
    'openpyxl.utils',
    
    # PySide6
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    
    # 标准库
    'logging',
    'pathlib',
    'tempfile',
    'shutil',
    'json',
    're',
    'collections',
    'collections.abc',
    'typing',
    'threading',
    'multiprocessing',
    'concurrent.futures',
    'queue',
    'functools',
    'itertools',
    'operator',
    'contextlib',
    'warnings',
    'traceback',
    'copy',
    'pickle',
    'struct',
    'hashlib',
    'random',
    'math',
    'time',
    'datetime',
    'xml.etree.ElementTree',
    'csv',
    'argparse',
    'importlib',
    'importlib.abc',
    'importlib.machinery',
    'importlib.resources',
    'importlib.util',
    'site',
    'os',
    'sys',
    'abc',
    'dataclasses',
]

# 排除不需要的模块
excludes = [
    'tkinter',
    'matplotlib',
    'torch',
    'tensorflow',
    'keras',
    'pytest',
    'unittest',
    'jupyter',
    'ipython',
    'Cython',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/runtime_hook_paddle.py'],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# macOS 应用包结构
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
    upx=False,  # macOS 上不使用 UPX
    runtime_tmpdir=None,
    console=False,  # macOS GUI 应用不需要控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    entitlements_file=None,
    icon=None,  # 可设置: icon='assets/app.icns'
)

# 创建 macOS .app bundle
app = BUNDLE(
    exe,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='handwritten-ocr.app',
    info_plist={
        'CFBundleName': 'handwritten-ocr',
        'CFBundleDisplayName': '手写表格识别',
        'CFBundleIdentifier': 'com.example.handwritten-ocr',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleExecutable': 'handwritten-ocr',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'CFBundleIconFile': None,  # 可设置图标: 'app.icns'
    },
    icon=None,
    bundle_identifier=None,
)
