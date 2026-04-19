"""
PyInstaller runtime hook for PaddlePaddle compatibility.

Fixes:
1. site.USER_SITE being None in frozen environment
2. setuptools bootstrap dependency (_distutils_hack) not available
"""

import site
import sys
import sysconfig
import os
import types

# Stub out _distutils_hack — it's a setuptools bootstrap shim that
# overrides stdlib distutils. Not needed in frozen apps, but setuptools
# __init__.py does `import _distutils_hack.override` unconditionally.
if '_distutils_hack' not in sys.modules:
    _dh = types.ModuleType('_distutils_hack')
    _dh.override = None
    _override = types.ModuleType('_distutils_hack.override')
    sys.modules['_distutils_hack'] = _dh
    sys.modules['_distutils_hack.override'] = _override

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