# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PaddleOCR + PySide6 application.

生成独立的 Windows exe 文件。

使用方法:
    pyinstaller build.spec --clean --noconfirm

打包后需要手动复制 paddle libs:
    xcopy venv\Lib\site-packages\paddle\libs\*.dll dist\handwritten-ocr\_internal\paddle\libs\ /Y
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

# 需要收集的隐藏导入模块（精简版）
hiddenimports = [
    # PaddlePaddle 核心
    'paddle',
    'paddle.fluid',
    'paddle.fluid.core',
    'paddle.fluid.framework',
    'paddle.fluid.layers',
    'paddle.fluid.dygraph',
    'paddle.fluid.executor',
    'paddle.inference',
    'paddle.framework',
    'paddle.nn',
    'paddle.nn.layer',
    'paddle.nn.functional',
    'paddle.optimizer',
    'paddle.io',
    'paddle._C_ops',
    
    # PaddleOCR 模块
    'paddleocr',
    'paddleocr.paddleocr',
    'paddleocr.ppocr',
    'paddleocr.ppocr.utils',
    'paddleocr.ppocr.utils.utility',
    'paddleocr.ppocr.utils.logging',
    'paddleocr.ppocr.utils.network',
    'paddleocr.ppocr.utils.e2e_utils',
    'paddleocr.ppocr.utils.e2e_utils.pgnet',
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
    
    # 关键依赖
    'shapely',
    'shapely.geometry',
    'shapely.geometry.polygon',
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
    'site',
]

# 排除不需要的模块
excludes = [
    'tkinter',
    'matplotlib',
    'torch',
    'tensorflow',
    'keras',
    'torchvision',
    'transformers',
    'huggingface_hub',
    'datasets',
    'langchain',
    'openai',
    'boto3',
    'google.cloud',
    'docker',
    'kubernetes',
    'ray',
    'dask',
    'distributed',
    'django',
    'flask',
    'fastapi',
    'selenium',
    'playwright',
    'requests',
    'pytest',
    'unittest',
    'coverage',
    'black',
    'flake8',
    'pylint',
    'mypy',
    'jupyter',
    'ipython',
    'notebook',
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
    console=True,  # 调试时用 True，成功后改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)