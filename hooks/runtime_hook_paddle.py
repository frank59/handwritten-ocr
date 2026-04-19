"""
PyInstaller runtime hook for PaddlePaddle compatibility.

Fixes the site.USER_SITE issue that causes:
TypeError: sequence item 0: expected str instance, NoneType found
in paddle/fluid/core.py
"""

import site
import sys
import sysconfig
import os

# Fix site.USER_SITE being None in frozen environment
if site.USER_SITE is None:
    site.ENABLE_USER_SITE = True
    # Try to set a valid USER_SITE path
    if hasattr(sys, 'frozen'):
        # PyInstaller frozen executable
        base_dir = os.path.dirname(sys.executable)
        site.USER_SITE = os.path.join(base_dir, '_internal', 'Lib', 'site-packages')
    else:
        site.USER_SITE = sysconfig.get_path('purelib') or os.path.join(sys.prefix, 'Lib', 'site-packages')

# Ensure paddle can find its libs
if hasattr(sys, 'frozen'):
    # Add the internal lib path for paddle libs
    internal_lib = os.path.join(os.path.dirname(sys.executable), '_internal')
    if os.path.exists(internal_lib):
        # Some paddle versions need this
        os.environ.setdefault('PADDLE_LIB_PATH', internal_lib)