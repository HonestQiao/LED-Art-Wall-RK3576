"""
LED点阵屏配置文件 - RK3576 适配版

硬件配置：
- 10块灯板串联成一条长链
- 通过 SPI0 (J11 Pin19) 驱动
- 每块灯板: 5行 x 144列 = 720 LEDs
- 总共: 10块 x 720 = 7200 LEDs
"""

import os

# ========== LED 硬件配置 ==========
# 灯板布局
BOARD_ROWS = 10          # 垂直方向的灯板数量（10块板垂直堆叠）
BOARD_COLS = 1           # 水平方向的灯板数量（串联后视为1列）
LED_ROWS_PER_BOARD = 5   # 每块灯板的行数
LED_COLS_PER_BOARD = 144 # 每块灯板的列数

# 计算总LED数量
LEDS_PER_BOARD = LED_ROWS_PER_BOARD * LED_COLS_PER_BOARD  # 5 * 144 = 720
TOTAL_BOARDS = BOARD_ROWS * BOARD_COLS                     # 10 * 1 = 10
TOTAL_LEDS = TOTAL_BOARDS * LEDS_PER_BOARD                # 10 * 720 = 7200

# 屏幕总分辨率
SCREEN_COLS = BOARD_COLS * LED_COLS_PER_BOARD  # 1 * 144 = 144
SCREEN_ROWS = BOARD_ROWS * LED_ROWS_PER_BOARD  # 10 * 5 = 50

# ========== SPI 配置 ==========
SPI_BUS = 0          # SPI0
SPI_DEVICE = 0       # CE0
SPI_SPEED_HZ = 2400000  # 2.4 MHz (WS2812B 推荐)

# ========== 显示配置 ==========
DEFAULT_BRIGHTNESS = 0.4   # 默认亮度 0.1-1.0
DEFAULT_DURATION = 10.0    # 默认显示时长（秒）

# ========== 状态显示配置 ==========
# 是否在桌面环境显示状态窗口
# True: 启用状态显示（需要 DISPLAY 环境变量）
# False: 禁用状态显示（无头模式）
# None: 自动检测（有 DISPLAY 就显示）
ENABLE_STATUS_DISPLAY = None

# ========== AI 图片生成配置 ==========
# API 相关配置
API_URL = "https://api.minimaxi.com/v1/image_generation"

# 提示词后缀（优化LED显示效果）
LED_PROMPT_SUFFIX = (
    ", pixel art style, "
    "solid black background, "
    "white or bright content on black background, "
    "high contrast, "
    "simplified design, "
    "content should be LARGE and FILL THE FRAME, "
    "maximized subject size, "
    f"suitable for LED display ( {SCREEN_COLS} x {SCREEN_ROWS})"
)

# 智能宽高比计算
ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "16:9": (1280, 720),
    "4:3": (1152, 864),
    "3:2": (1248, 832),
    "2:3": (832, 1248),
    "3:4": (864, 1152),
    "9:16": (720, 1280),
    "21:9": (1344, 576),
}


def calculate_best_aspect_ratio():
    """根据当前屏幕分辨率自动计算最适合的宽高比"""
    screen_ratio = SCREEN_COLS / SCREEN_ROWS
    best_ratio = None
    min_diff = float('inf')

    for ratio_str, (width, height) in ASPECT_RATIOS.items():
        ratio_value = width / height
        is_screen_landscape = SCREEN_COLS >= SCREEN_ROWS
        is_ratio_landscape = width >= height

        if is_screen_landscape != is_ratio_landscape:
            continue

        diff = abs(screen_ratio - ratio_value)
        if diff < min_diff:
            min_diff = diff
            best_ratio = ratio_str

    return best_ratio or "1:1"


BEST_ASPECT_RATIO = calculate_best_aspect_ratio()

# ========== UDP 服务器配置 ==========
UDP_IP = "0.0.0.0"
UDP_PORT = 12346
DEFAULT_SERVER_IP = "192.168.1.170"  # RK3576开发板IP（客户端使用）
