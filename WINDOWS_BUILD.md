# Windows EXE 打包指南

本文档说明如何将手写表格识别工具打包为独立的 Windows exe 文件。

> ⚠️ **重要**: PyInstaller 不支持跨平台打包。在 macOS 上无法直接生成 Windows exe。

---

## 跨平台打包方案（macOS → Windows）

如果你在 macOS 上开发，有以下几种方式生成 Windows exe：

### 方案 1: GitHub Actions（推荐，免费）

已配置好自动化构建流程，推送到 GitHub 后自动打包。

**使用方法**：

1. 将代码推送到 GitHub 仓库
2. 手动触发构建：进入 Actions → Build Windows EXE → Run workflow
3. 或发布版本：创建 tag（如 `v1.0.0`）自动触发
4. 构建完成后下载 artifact `windows-exe`

**配置文件**: `.github/workflows/build-windows.yml`

### 方案 2: 虚拟机

在 macOS 上安装 Windows 虚拟机：

| 虚拟机软件 | 类型 | 说明 |
|-----------|------|------|
| Parallels Desktop | 商业 | 性能最好，约 ¥600/年 |
| VMware Fusion | 商业 | 稳定可靠 |
| VirtualBox | 免费 | 性能较差 |
| UTM | 免费 | Apple Silicon 推荐 |

### 方案 3: 远程 Windows

使用远程 Windows 电脑或云服务器：

- AWS EC2 Windows 实例
- Azure Windows VM
- 自己的 Windows 电脑（远程桌面）

---

## 在 Windows 上直接打包

### 1. 准备 Windows 环境

```powershell
# 使用 Python 3.10 (推荐，兼容性最好)
py -3.10 -m venv venv
.\venv\Scripts\activate
```

### 2. 安装依赖

```powershell
# 安装 CPU 版本的 PaddlePaddle
pip install paddlepaddle==3.0.0

# 安装其他依赖
pip install paddleocr==2.10.0
pip install opencv-python-headless==4.10.0.84
pip install PySide6==6.8.3
pip install pandas openpyxl "numpy>=1.24,<2.0"

# 安装打包工具
pip install pyinstaller
```

### 3. 验证程序运行

```powershell
python main.py
```

确保程序能正常启动并完成 OCR 识别后再打包。

### 4. 执行打包

```powershell
pyinstaller build.spec --clean --noconfirm
```

打包过程约 10-30 分钟。

### 5. 复制 Paddle libs（关键步骤）

PaddlePaddle 的 DLL 文件可能未被正确收集，需要手动复制：

```powershell
# 创建目标目录
mkdir dist\handwritten-ocr\_internal\paddle\libs

# 复制所有 DLL 文件
xcopy venv\Lib\site-packages\paddle\libs\*.dll dist\handwritten-ocr\_internal\paddle\libs\ /Y /I
```

### 6. 测试打包结果

```powershell
cd dist\handwritten-ocr
.\handwritten-ocr.exe
```

首次运行会自动下载 OCR 模型到用户目录 `C:\Users\<用户名>\.paddleocr\`。

---

## 常见问题排查

### 问题 1: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**: 在 `build.spec` 的 `hiddenimports` 中添加缺失模块：

```python
hiddenimports = [
    # ... 现有模块
    'xxx',  # 添加缺失模块
]
```

### 问题 2: TypeError: sequence item 0: expected str instance, NoneType found

这是 `paddle/fluid/core.py` 中 `site.USER_SITE` 为 None 的问题。

**解决方案**: 已在 `main.py` 和 `hooks/runtime_hook_paddle.py` 中修复。如果仍有问题，检查：

```powershell
# 确保 runtime hook 被正确打包
dir dist\handwritten-ocr\_internal\hooks
```

### 问题 3: 找不到 paddle libs

```
OSError: cannot load library 'paddle\libs\xxx.dll'
```

**解决方案**: 手动复制 DLL 文件：

```powershell
xcopy venv\Lib\site-packages\paddle\libs\*.dll dist\handwritten-ocr\_internal\paddle\libs\ /Y /I
```

### 问题 4: 程序启动后闪退

**解决方案**: 使用 `console=True` 模式查看错误信息：

1. 编辑 `build.spec`，设置 `console=True`
2. 重新打包：`pyinstaller build.spec --clean`
3. 从命令行运行：`.\handwritten-ocr.exe`
4. 查看控制台输出的错误信息

### 问题 5: 打包体积过大

正常情况下打包目录约 1-2GB。如果更大：

1. 检查 `build.spec` 的 `excludes` 是否生效
2. 使用 UPX 压缩（已默认启用）
3. 手动删除不需要的文件：

```powershell
# 删除测试相关文件
rmdir /s /q dist\handwritten-ocr\_internal\tests
rmdir /s /q dist\handwritten-ocr\_internal\pytest
```

---

## 调试技巧

### 查看导入的所有模块

```powershell
# 在 Python 中运行，查看 paddleocr 的所有子模块
python -c "from PyInstaller.utils.hooks import collect_submodules; print(collect_submodules('paddleocr'))"
```

### 验证 DLL 文件

```powershell
# 查看 paddle libs 目录
dir venv\Lib\site-packages\paddle\libs

# 复制后验证
dir dist\handwritten-ocr\_internal\paddle\libs
```

### 添加调试信息

临时修改 `main.py`，在启动时打印路径信息：

```python
import sys
print(f"Python path: {sys.path}")
print(f"Executable: {sys.executable}")
print(f"frozen: {getattr(sys, 'frozen', False)}")
```

---

## 发布准备

### 隐藏控制台窗口

调试成功后，修改 `build.spec`：

```python
exe = EXE(
    # ...
    console=False,  # 改为 False
)
```

重新打包。

### 添加图标

准备 `assets/app.ico` 文件（256x256），修改 `build.spec`：

```python
exe = EXE(
    # ...
    icon='assets/app.ico',
)
```

### 创建分发包

```powershell
# 压缩为 zip
Compress-Archive -Path dist\handwritten-ocr -DestinationPath handwritten-ocr-windows.zip

# 或使用 7-Zip (压缩率更高)
7z a -t7z handwritten-ocr-windows.7z dist\handwritten-ocr\

# 最终文件大小约 500-800MB (压缩后)
```

---

## 用户使用说明

分发给用户时，附带以下说明：

1. 解压 `handwritten-ocr-windows.zip`
2. 运行 `handwritten-ocr.exe`
3. 首次启动需要联网下载模型（约 50MB）
4. 之后可完全离线使用

---

## 文件结构

打包后的目录结构：

```
handwritten-ocr/
├── handwritten-ocr.exe      # 主程序
├── _internal/               # 内部依赖
│   ├── python310.dll        # Python 运行时
│   ├── paddle/              # PaddlePaddle
│   │   └── libs/            # DLL 文件
│   ├── paddleocr/           # PaddleOCR
│   ├── PySide6/             # Qt 库
│   ├── numpy/               # 数值计算
│   ├── pandas/              # 数据处理
│   ├── cv2/                 # OpenCV
│   ├── src/                 # 项目源码
│   └── config.py            # 配置文件
```

---

## 注意事项

1. **必须在 Windows 上打包** - PyInstaller 不支持跨平台打包
2. **使用 Python 3.10** - 3.12 可能存在兼容问题
3. **首次运行需要联网** - 下载 OCR 模型到用户目录
4. **调试时用 console=True** - 方便查看错误信息
5. **手动复制 paddle libs** - 这是关键步骤