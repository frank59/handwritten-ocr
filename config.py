"""Global configuration constants."""

# Supported image formats
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

# Max file size in MB
MAX_FILE_SIZE_MB = 20

# Image preprocessing
TARGET_LONG_EDGE = 2048
MIN_LONG_EDGE = 1024

# OCR settings
OCR_DROP_SCORE = 0.3
OCR_DET_DB_THRESH = 0.3
OCR_DET_DB_UNCLIP_RATIO = 1.8
OCR_REC_BATCH_NUM = 6

# Confidence threshold for highlighting in GUI
LOW_CONFIDENCE_THRESHOLD = 0.7

# GUI settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
APP_NAME = "手写表格识别与导出工具"
