"""
PyInstaller runtime hook for PaddlePaddle compatibility.

Fixes site.USER_SITE being None in frozen environment.
setuptools 59.8.0 uses stdlib distutils, no extra hacks needed.
"""

import site
import sys
import sysconfig
import os

# Fix site.USER_SITE being None in frozen environment
if site.USER_SITE is None:
    site.ENABLE_USER_SITE = True
    if hasattr(sys, 'frozen'):
        # PyInstaller frozen executable
        base_dir = os.path.dirname(sys.executable)
        site.USER_SITE = os.path.join(base_dir, '_internal', 'Lib', 'site-packages')
    else:
        site.USER_SITE = sysconfig.get_path('purelib') or os.path.join(sys.prefix, 'Lib', 'site-packages')

# Ensure paddle can find its libs
if hasattr(sys, 'frozen'):
    internal_lib = os.path.join(os.path.dirname(sys.executable), '_internal')
    if os.path.exists(internal_lib):
        os.environ.setdefault('PADDLE_LIB_PATH', internal_lib)
