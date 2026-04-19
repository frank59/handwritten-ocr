# Windows 打包指南

本文档说明如何将手写表格识别工具打包为 Windows 可执行文件 (.exe)。

## 环境准备

### 硬件要求
- Windows 10/11 (64位)
- 建议 16GB+ RAM（OCR 推理需要较多内存）
- 至少 10GB 可用磁盘空间

### 软件要求
- Python 3.10 或 3.11（推荐，3.12 可能存在兼容性问题）
- Git for Windows
- 8GB+ RAM

## 打包步骤

### 1. 克隆项目

```powershell
git clone <your-repo-url>
cd handwritten-ocr
```

### 2. 创建虚拟环境

```powershell
# 使用 Python 3.10 创建虚拟环境
py -3.10 -m venv venv
.\venv\Scripts\activate
```

### 3. 安装依赖

```powershell
# 安装 CPU 版本的 PaddlePaddle（节省空间，无 CUDA 依赖）
pip install paddlepaddle==3.0.0

# 安装其他依赖
pip install paddleocr==2.10.0
pip install opencv-python-headless==4.10.0.84
pip install PySide6==6.8.3
pip install pandas>=2.0
pip install openpyxl>=3.1
pip install "numpy>=1.24,<2.0"

# 安装打包工具
pip install pyinstaller
```

### 4. 验证运行环境

```powershell
python main.py
```

确保程序能正常运行后再进行打包。

### 5. 执行打包

```powershell
pyinstaller build.spec --clean
```

打包过程可能需要 10-20 分钟，取决于网络和硬件。

### 6. 查找输出文件

打包完成后，可执行文件位于：
```
dist\handwritten-ocr\handwritten-ocr.exe
```

整个 `dist\handwritten-ocr` 文件夹可以分发给用户。

## 常见问题

### Q1: 打包后运行报错 "ModuleNotFoundError"

某些动态导入的模块未被收集。编辑 `build.spec`，在 `hiddenimports` 中添加缺失的模块：

```python
hiddenimports = [
    # ... 现有模块
    'missing_module_name',  # 添加这里
]
```

### Q2: 程序启动很慢

这是正常现象，首次运行需要初始化 PaddleOCR 模型缓存。后续运行会使用缓存，速度正常。

### Q3: 打包体积太大 (>2GB)

PaddleOCR 模型文件较大。可接受的分发方式：
- 提供下载链接，首次运行时自动下载模型
- 或者接受大体积（模型本身约 200MB）

### Q4: 杀毒软件报毒

PyInstaller 打包的程序有时会被误报。解决方案：
- 使用代码签名证书签名
- 向杀毒软件厂商提交误报
- 使用 Nuitka 替代 PyInstaller（编译为 C）

### Q5: 图标不显示

将 256x256 的 .ico 文件放到项目根目录，编辑 `build.spec`：

```python
exe = EXE(
    # ...
    icon='app.ico',  # 替换为你的图标文件
)
```

## 高级配置

### 使用单文件模式

修改 `build.spec` 中的 `exe` 部分：

```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='handwritten-ocr',
    console=False,
    onefile=True,  # 添加此行，生成单个 exe 文件
)
```

单文件模式启动较慢，不推荐用于大程序。

### 分离数据和程序

默认情况下，数据文件会放在程序同目录下。如需分离：

```python
exe = EXE(
    # ...
    strip=False,
    upx=False,
    runtime_tmpdir='.',  # 运行时临时文件位置
)
```

## 测试打包结果

在没有安装 Python 的 Windows 电脑上测试：

1. 复制整个 `dist\handwritten-ocr` 文件夹
2. 运行 `handwritten-ocr.exe`
3. 检查日志输出是否有错误

## 进一步优化

### 使用 Nuitka 编译

Nuitka 可以将 Python 编译为 C，性能更好：

```powershell
pip install nuitka

# 编译（需要 Visual Studio Build Tools）
python -m nuitka --standalone --onefile --enable-plugin=pyside6 main.py
```

### 使用 conda 环境

使用 conda 可以更好地管理 PaddlePaddle 的二进制依赖：

```powershell
conda create -n ocr-env python=3.10
conda activate ocr-env
# 安装 PyTorch CPU 版本
conda install pytorch cpuonly -c pytorch
# 安装其他依赖
pip install paddleocr PySide6 pandas openpyxl
```

## 获取帮助

如果打包遇到问题，请提供：
1. 完整的错误信息
2. 你的 Windows 版本
3. Python 版本 (`python --version`)
4. 打包命令的完整输出
