"""
PyInstaller runtime hook for PaddlePaddle compatibility.

支持 Windows 和 macOS 平台。
"""

import site
import sys
import sysconfig
import os
import platform

def get_bundle_dir():
    """Get the application bundle directory for macOS .app or exe directory for Windows."""
    if platform.system() == 'Darwin':
        # macOS: app bundle structure
        # sys.executable is in Contents/MacOS/
        exe_dir = os.path.dirname(sys.executable)
        # Go up to Contents/
        contents_dir = os.path.dirname(exe_dir)
        # Go up to .app root
        return os.path.dirname(contents_dir)
    else:
        # Windows/Linux
        return os.path.dirname(sys.executable)

def get_internal_dir():
    """Get the _internal directory path."""
    base_dir = get_bundle_dir()
    internal = os.path.join(base_dir, '_internal')
    if os.path.exists(internal):
        return internal
    # Fallback to executable directory
    return os.path.dirname(sys.executable)

# Fix site.USER_SITE being None in frozen environment
if site.USER_SITE is None:
    site.ENABLE_USER_SITE = True
    if hasattr(sys, 'frozen'):
        # PyInstaller frozen executable
        if platform.system() == 'Darwin':
            # macOS .app bundle
            site.USER_SITE = os.path.join(
                get_bundle_dir(),
                'Contents', 'Resources', 'src', '_internal'
            )
        else:
            # Windows
            site.USER_SITE = os.path.join(get_internal_dir(), 'Lib', 'site-packages')
    else:
        site.USER_SITE = sysconfig.get_path('purelib') or os.path.join(sys.prefix, 'lib', 'site-packages')

# Ensure paddle can find its libs
if hasattr(sys, 'frozen'):
    internal_dir = get_internal_dir()
    if os.path.exists(internal_dir):
        os.environ.setdefault('PADDLE_LIB_PATH', internal_dir)

    # Point PaddleOCR to bundled models (downloaded and extracted during CI build)
    bundle_dir = get_bundle_dir()
    bundled_models = os.path.join(bundle_dir, '_internal', 'models')
    if os.path.exists(bundled_models):
        os.environ.setdefault('PADDLE_OCR_BASE_DIR', bundled_models)

    # macOS specific: ensure Qt can find plugins
    if platform.system() == 'Darwin':
        bundle_dir = get_bundle_dir()
        plugins_path = os.path.join(bundle_dir, 'Contents', 'PlugIns')
        if os.path.exists(plugins_path):
            os.environ.setdefault('QT_PLUGIN_PATH', plugins_path)
