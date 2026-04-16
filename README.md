# 手写表格识别与导出工具

纯本地离线运行的桌面应用，将手写单据图片自动转换为结构化 Excel 文件。基于 PaddleOCR (PP-OCRv4) 进行文字检测与识别，通过 PySide6 提供可视化交互界面，支持人工纠错后一键导出。

## 功能特性

- **纯离线运行** — 所有 OCR 推理均在本地 CPU 完成，无需联网，数据不出本机
- **手写文字识别** — 基于 PP-OCRv4 模型，支持中文手写体与印刷体混合识别
- **交互式画布** — 在原图上直接查看、编辑、删除、新增文字检测框
  - 双击矩形框可就地编辑识别文本
  - 拖拽调整矩形框位置和大小
  - Ctrl + 拖拽在空白区域创建新检测框
  - Shift 长按临时隐藏所有覆盖层以查看原图
  - Ctrl + 滚轮缩放画布
- **列辅助线** — 可拖拽的垂直辅助线辅助表格列定义
  - 自动根据首行文字位置生成辅助线
  - 手动添加/拖拽辅助线端点，支持倾斜线段
  - 辅助线端点自动限制在图片边界内
- **智能表格生成** — 两种模式
  - 自动聚类模式：根据矩形框坐标自动聚类行列
  - 辅助线模式：按辅助线与矩形框的严格交叉判定分配列，每列从上到下逐个对应单元格
- **可编辑表格预览** — 生成的表格支持双击单元格编辑、插入/删除行
- **Excel 导出** — 一键导出为 `.xlsx` 文件，自动适配列宽

## 系统要求

- Python 3.8+
- 操作系统：macOS / Windows 10+ (64位)
- 最低配置：双核 CPU，8GB 内存
- 推荐配置：四核 CPU，16GB 内存
- 无需独立显卡，纯 CPU 推理

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd handwritten-ocr

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 依赖说明

| 包名 | 版本 | 用途 |
|------|------|------|
| paddlepaddle | 3.0.0 | 深度学习推理框架 |
| paddleocr | 2.10.0 | OCR 引擎 (PP-OCRv4) |
| opencv-python-headless | 4.10.0.84 | 图像预处理 |
| PySide6 | 6.8.3 | GUI 框架 |
| pandas | >=2.0 | 数据处理 |
| openpyxl | >=3.1 | Excel 读写 |
| numpy | >=1.24,<2.0 | 数值计算 |

> 首次运行时 PaddleOCR 会自动下载模型文件并缓存到本地，后续运行无需联网。

## 使用方法

```bash
source venv/bin/activate
python main.py
```

### 工作流程

1. **打开图片** — 点击工具栏「打开图片」或 `Ctrl+O`，支持 JPG/PNG/BMP 格式
2. **旋转调整** — 如图片方向不正，使用「左旋」「右旋」按钮调整
3. **OCR 识别** — 点击「识别」，等待检测与识别完成，结果以矩形框叠加在原图上
4. **纠错编辑** — 在画布上检查识别结果
   - 双击矩形框修改错误文字
   - 拖拽矩形框调整位置
   - 右键删除错误检测框
   - Ctrl + 拖拽创建遗漏区域的新检测框
5. **列辅助线**（可选）— 点击「生成列辅助」自动生成，或「添加辅助线」手动添加，拖拽端点微调
6. **生成表格** — 点击「生成表格」，根据矩形框坐标（或辅助线交叉）生成结构化表格
7. **表格编辑** — 在表格预览中双击单元格做最后修正
8. **导出 Excel** — 点击「导出 Excel」或 `Ctrl+S`，选择保存路径

## 项目结构

```
handwritten-ocr/
├── main.py                          # 应用入口
├── config.py                        # 全局配置常量
├── requirements.txt                 # Python 依赖
├── src/
│   ├── preprocessing/
│   │   ├── loader.py                # 图片加载与校验
│   │   └── enhancer.py              # 图像增强（矫正、降噪、缩放）
│   ├── ocr/
│   │   ├── engine.py                # PaddleOCR 引擎单例管理
│   │   ├── detector.py              # 文字区域检测
│   │   └── recognizer.py            # 文字识别
│   ├── parsing/
│   │   ├── data_models.py           # 共享数据模型 (TextBox, ParsedDocument 等)
│   │   └── table_generator.py       # 表格结构生成（坐标聚类 / 辅助线模式）
│   ├── gui/
│   │   ├── main_window.py           # 主窗口与流程编排
│   │   ├── toolbar.py               # 状态驱动的工具栏
│   │   ├── table_widget.py          # 可编辑表格控件
│   │   ├── dialogs.py               # 对话框工具函数
│   │   └── canvas/
│   │       ├── image_canvas.py      # 交互式画布 (QGraphicsView)
│   │       ├── text_box_item.py     # 可拖拽/编辑的文字框 (QGraphicsRectItem)
│   │       ├── text_edit_proxy.py   # 文字编辑代理与信号中枢
│   │       └── column_guide_item.py # 列辅助线 (QGraphicsLineItem)
│   ├── export/
│   │   └── excel_writer.py          # Excel 导出 (Pandas + OpenPyXL)
│   └── workers/
│       ├── ocr_worker.py            # OCR 后台线程
│       └── recognize_crop_worker.py # 裁剪区域重新识别线程
└── tests/                           # 测试目录
```

## 配置项

在 `config.py` 中可调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SUPPORTED_EXTENSIONS` | .jpg .jpeg .png .bmp | 支持的图片格式 |
| `MAX_FILE_SIZE_MB` | 20 | 图片文件大小上限 (MB) |
| `TARGET_LONG_EDGE` | 2048 | 图像预处理目标长边像素 |
| `OCR_DROP_SCORE` | 0.3 | OCR 识别置信度阈值 |
| `LOW_CONFIDENCE_THRESHOLD` | 0.7 | 低置信度高亮阈值 |
| `WINDOW_WIDTH` / `WINDOW_HEIGHT` | 1200 x 800 | 默认窗口尺寸 |

## 技术架构

```
图像预处理层 (preprocessing)
    ↓
OCR 推理层 (ocr) — PaddleOCR PP-OCRv4, CPU-only
    ↓
结构化解析层 (parsing) — 坐标聚类 / 辅助线交叉
    ↓
GUI 展示层 (gui) — PySide6 QGraphicsView 交互画布
    ↓
数据导出层 (export) — Pandas + OpenPyXL → .xlsx
```

## 许可证

私有项目，保留所有权利。
