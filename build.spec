# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PaddleOCR + PySide6 application.

使用 collect_all 递归收集所有子模块（包括动态 import），
彻底解决 hiddenimports 遗漏导致的 ModuleNotFoundError。
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# 收集数据文件
datas = [
    ('src', 'src'),
    ('config.py', '.'),
]

# 收集第三方库的数据文件
for pkg in ['paddleocr', 'paddle', 'shapely', 'pyclipper', 'psutil',
            'openpyxl', 'tqdm', 'attr', 'lmdb', 'yaml']:
    try:
        datas += collect_data_files(pkg, include_py_files=False)
    except Exception:
        pass

# collect_all: 递归收集所有子模块，包括动态 import 的模块。
# 注意：setuptools 不使用 collect_all，避免触发 vendored 依赖的 hooks 递归。
# setuptools 59.8.0 使用 collect_submodules + 手动指定子模块代替。
_collect_all = []
for pkg in ['paddle', 'paddleocr', 'shapely', 'scipy', 'pyclipper',
            'lmdb', 'pyyaml', 'tqdm', 'attrs', 'six', 'psutil',
            'openpyxl', 'cv2', 'PIL']:
    try:
        _collected = collect_all(pkg)
        if _collected:
            _collect_all += _collected
            print(f'collect_all({pkg}): {len(_collected)} submodules')
    except Exception as e:
        print(f'collect_all({pkg}) failed: {e}')

# 补充 collect_submodules（处理已知的子模块路径）
# setuptools 使用 collect_submodules 而非 collect_all，避免触发 hooks 递归
_collect_sub = []
for pkg in ['numpy', 'pandas', 'setuptools', 'pkg_resources']:
    try:
        subs = collect_submodules(pkg)
        _collect_sub += subs
        print(f'collect_submodules({pkg}): {len(subs)} submodules')
    except Exception as e:
        print(f'collect_submodules({pkg}) failed: {e}')

# hiddenimports: collect_all + collect_submodules + 必须显式指定的模块
hiddenimports = _collect_all + _collect_sub + [
    # PySide6 — Qt 绑定
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.support',

    # 标准库中 PyInstaller 无法自动分析的模块
    'logging',
    'logging.config',
    'logging.handlers',
    'unittest',
    'unittest.mock',
    'multiprocessing',
    'multiprocessing.context',
    'multiprocessing.pool',
    'multiprocessing.spawn',
    'concurrent.futures',
    'concurrent.futures.thread',
    'concurrent.futures.process',
    'importlib',
    'importlib.abc',
    'importlib.machinery',
    'importlib.resources',
    'importlib.util',
    'pkg_resources.extern',
]

# 排除不需要的模块
excludes = [
    'tkinter',
    'matplotlib',
    'mpl_toolkits',
    'torch',
    'tensorflow',
    'keras',
    'torchvision',
    'transformers',
    'huggingface_hub',
    'datasets',
    'accelerate',
    'diffusers',
    'langchain',
    'openai',
    'anthropic',
    'boto3',
    'botocore',
    'awscli',
    'google.cloud',
    'googleapiclient',
    'grpc',
    'grpcio',
    'docker',
    'kubernetes',
    'ray',
    'dask',
    'distributed',
    'prefect',
    'airflow',
    'celery',
    'redis',
    'pymongo',
    'mysql',
    'psycopg2',
    'sqlalchemy',
    'django',
    'flask',
    'fastapi',
    'starlette',
    'uvicorn',
    'gunicorn',
    'werkzeug',
    'jinja2',
    'selenium',
    'playwright',
    'scrapy',
    'bs4',
    'beautifulsoup4',
    'httpx',
    'aiohttp',
    'pytest',
    '_pytest',
    'coverage',
    'hypothesis',
    'black',
    'flake8',
    'pylint',
    'mypy',
    'isort',
    'tox',
    'nox',
    'jupyter',
    'jupyter_client',
    'jupyter_core',
    'ipython',
    'ipykernel',
    'notebook',
    'nbformat',
    'nbconvert',
    'Cython',
    'cython',
    'wheel',
    'pip',
    'sphinx',
    'docutils',
    'pygments',
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
    [],
    exclude_binaries=True,
    name='handwritten-ocr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='handwritten-ocr',
)
