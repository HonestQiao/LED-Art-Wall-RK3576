#!/usr/bin/env python3
"""
LED点阵屏服务器 - RK3576 适配版

接收UDP消息，调用MiniMax API生成图片并显示到LED点阵屏
用法等价于: python led_matrix_server.py --api-key xxx
"""

import socket
import json
import os
import sys
import signal
import time
from datetime import datetime
from io import BytesIO

# ========== 加载 .env 文件 ==========
def load_env_file():
    """加载 .env 文件中的环境变量"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

import config

# ========== LED 驱动导入 ==========
from ws2812b_driver import LEDMatrix

# 初始化LED点阵屏
led_matrix = LEDMatrix(
    board_rows=config.BOARD_ROWS,
    board_cols=config.BOARD_COLS,
    led_rows_per_board=config.LED_ROWS_PER_BOARD,
    led_cols_per_board=config.LED_COLS_PER_BOARD,
    spi_bus=config.SPI_BUS,
    spi_device=config.SPI_DEVICE,
    brightness=config.DEFAULT_BRIGHTNESS
)

# ========== 图片生成相关导入 ==========
import base64
import requests
from PIL import Image, ImageEnhance, ImageFilter

# ========== 服务器配置 ==========
UDP_IP = config.UDP_IP
UDP_PORT = config.UDP_PORT
DEFAULT_DURATION = config.DEFAULT_DURATION

# PID文件路径
PID_FILE = "/tmp/led_matrix_server.pid"

print(f"[服务器] LED点阵屏: {config.SCREEN_COLS} x {config.SCREEN_ROWS} = {config.TOTAL_LEDS} LEDs", flush=True)
print(f"[服务器] 最佳宽高比: {config.BEST_ASPECT_RATIO}", flush=True)


# ========== 图片生成 ==========
def generate_image(prompt: str, api_key: str = None, aspect_ratio: str = None) -> Image.Image:
    """调用 MiniMax API 生成图片"""
    if not api_key:
        raise ValueError("请设置 MiniMax API Key")

    use_aspect_ratio = aspect_ratio or config.BEST_ASPECT_RATIO

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": use_aspect_ratio,
        "response_format": "base64"
    }

    print(f"[AI] 正在生成图片 (宽高比: {use_aspect_ratio}): {prompt[:50]}...", flush=True)
    start_time = time.time()
    response = requests.post(config.API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()
    if "data" in result and "image_base64" in result["data"]:
        image_base64_list = result["data"]["image_base64"]
    else:
        raise ValueError(f"API 返回格式异常: {result}")

    if isinstance(image_base64_list, list):
        image_base64 = image_base64_list[0]
    else:
        image_base64 = image_base64_list

    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))
    elapsed = time.time() - start_time
    print(f"[AI] 图片生成成功！原始尺寸: {image.size}，耗时: {elapsed:.2f}秒", flush=True)

    return image


def enhance_for_led(image: Image.Image, threshold: int = 128, contrast: float = 2.0) -> Image.Image:
    """增强图片以适应 LED 显示"""
    if image.mode != 'L':
        img = image.convert('L')
    else:
        img = image.copy()

    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

    img = img.point(lambda p: 255 if p > threshold else 0, mode='L')
    img = img.filter(ImageFilter.MaxFilter(3))
    img = img.point(lambda p: 255 if p > 127 else 0, mode='L')
    img = img.resize((config.SCREEN_COLS, config.SCREEN_ROWS), Image.NEAREST)

    return img


def generate_led_image(prompt: str, api_key: str = None, threshold: int = 100, contrast: float = 2.5, aspect_ratio: str = None) -> Image.Image:
    """生成适合 LED 显示的图片（带后处理）"""
    led_prompt = prompt + config.LED_PROMPT_SUFFIX
    image = generate_image(led_prompt, api_key=api_key, aspect_ratio=aspect_ratio)
    image = enhance_for_led(image, threshold=threshold, contrast=contrast)
    return image


# ========== 状态显示 ==========
def show_status_text(text: str, sub_text: str = None):
    """
    在LED屏幕上显示状态文字
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # 创建黑色背景图像
        img = Image.new('L', (config.SCREEN_COLS, config.SCREEN_ROWS), 0)
        draw = ImageDraw.Draw(img)

        # 计算字体大小
        if len(text) <= 2:
            main_font_size = min(config.SCREEN_ROWS * 0.7, config.SCREEN_COLS / len(text) * 0.8)
        else:
            main_font_size = min(config.SCREEN_ROWS * 0.5, config.SCREEN_COLS / len(text) * 0.8)

        main_font_size = int(main_font_size)
        sub_font_size = int(main_font_size * 0.4)

        # 尝试加载字体
        font_paths = [
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]

        font = None
        sub_font = None
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, main_font_size)
                    sub_font = ImageFont.truetype(fp, sub_font_size)
                    break
                except:
                    continue

        if font is None:
            font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        # 计算主文字位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (config.SCREEN_COLS - text_width) // 2
        if sub_text:
            y = (config.SCREEN_ROWS - text_height) // 3
        else:
            y = (config.SCREEN_ROWS - text_height) // 2

        # 绘制主文字（白色）
        draw.text((x, y), text, fill=255, font=font)

        # 如果有副文字，绘制在下方
        if sub_text:
            bbox_sub = draw.textbbox((0, 0), sub_text, font=sub_font)
            sub_width = bbox_sub[2] - bbox_sub[0]
            sub_x = (config.SCREEN_COLS - sub_width) // 2
            sub_y = y + text_height + 2
            draw.text((sub_x, sub_y), sub_text, fill=200, font=sub_font)

        # 显示到LED
        led_matrix.clear()
        for row in range(config.SCREEN_ROWS):
            for col in range(config.SCREEN_COLS):
                pixel = img.getpixel((col, row))
                if pixel > 127:
                    if text == "生成":
                        hue = 0.6 + (col / config.SCREEN_COLS) * 0.1
                    elif text == "等待":
                        hue = 0.3 + (col / config.SCREEN_COLS) * 0.1
                    else:
                        hue = ((col + row) / (config.SCREEN_COLS + config.SCREEN_ROWS)) % 1.0

                    r, g, b = led_matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                    led_matrix.set_pixel(col, row, r, g, b)

        led_matrix.show()
        print(f"[状态] 屏幕显示: {text}", flush=True)

    except Exception as e:
        print(f"[状态] 显示失败: {e}", flush=True)


# ========== PID和清理 ==========
def check_previous_instance():
    """检查是否有之前的实例在运行"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                print(f"发现之前的进程 (PID: {old_pid}) 正在运行，正在关闭...")
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(0.5)
                print("已关闭之前的进程")
            except (OSError, ProcessLookupError):
                pass
        except (ValueError, IOError):
            pass

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def cleanup():
    """程序退出时清理"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def cleanup_leds():
    """关闭所有LED"""
    try:
        led_matrix.clear()
        led_matrix.show()
    except Exception:
        pass


# ========== 任务处理 ==========
def process_task(prompt: str, api_key: str):
    """处理单个任务"""
    try:
        print(f"[任务] 开始处理: {prompt}", flush=True)

        # LED屏幕显示"生成"状态
        show_status_text("生成", "AI绘画中...")

        # 生成图片
        image = generate_led_image(prompt, api_key, threshold=100, contrast=2.5)

        # 保存图片
        os.makedirs("images", exist_ok=True)
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image_path = f"images/{filename}"
        image.save(image_path)
        print(f"[任务] 图片已保存: {image_path}", flush=True)

        # 显示图片（静态模式，关闭动画边框以适配7200颗LED）
        led_matrix.animated_display(image, duration=DEFAULT_DURATION, animated_border=False)

        print(f"[任务] 完成: {prompt}", flush=True)

        # 显示完成后，回到等待状态
        time.sleep(0.5)
        show_status_text("等待", "准备就绪")

    except Exception as e:
        print(f"[任务] 错误: {e}", flush=True)
        # 错误时也显示等待状态
        show_status_text("等待", "准备就绪")


# ========== UDP服务器 ==========
def start_server(api_key: str):
    """启动UDP服务器"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(1.0)

    print("=" * 60)
    print("LED点阵屏服务器启动 - RK3576")
    print("=" * 60)
    print(f"监听地址: {UDP_IP}:{UDP_PORT}")
    print(f"屏幕分辨率: {config.SCREEN_COLS} x {config.SCREEN_ROWS}")
    print(f"总LED数量: {config.TOTAL_LEDS}")
    print(f"默认显示时长: {DEFAULT_DURATION}秒")
    print(f"自动计算宽高比: {config.BEST_ASPECT_RATIO}")
    print("=" * 60)
    print("等待接收图片生成请求...")
    print("提示: 发送JSON格式: {'prompt': 'cute cat'}")
    print("=" * 60)

    # 启动时显示"等待"状态
    show_status_text("等待", "准备就绪")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    request = json.loads(data.decode('utf-8'))
                    prompt = request.get('prompt', '')

                    if not prompt:
                        print(f"[{now}] 来自 {addr[0]}:{addr[1]}: 缺少prompt参数", flush=True)
                        continue

                    print(f"\n{'='*60}")
                    print(f"[{now}] 收到来自 {addr[0]}:{addr[1]} 的请求")
                    print(f"提示词: {prompt}")
                    print(f"{'='*60}\n")

                    # 处理任务
                    process_task(prompt, api_key)

                except json.JSONDecodeError:
                    # 尝试直接作为纯文本处理
                    prompt = data.decode('utf-8', errors='ignore').strip()
                    if prompt:
                        print(f"\n[{now}] 来自 {addr[0]}:{addr[1]} (纯文本): {prompt}\n")
                        process_task(prompt, api_key)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"处理数据时出错: {e}", flush=True)

    except KeyboardInterrupt:
        print("\n\n服务器正在关闭...")
    finally:
        sock.close()
        cleanup_leds()
        cleanup()
        print("服务器已停止")


# ========== 主程序 ==========
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="LED点阵屏服务器 - RK3576 UDP接收版")
    parser.add_argument("--api-key", type=str, help="MiniMax API Key")
    parser.add_argument("--port", type=int, default=UDP_PORT, help=f"UDP端口 (默认{UDP_PORT})")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help=f"显示时长秒数 (默认{DEFAULT_DURATION})")
    parser.add_argument("--brightness", type=float, default=config.DEFAULT_BRIGHTNESS, help=f"亮度 0.1-1.0 (默认{config.DEFAULT_BRIGHTNESS})")

    args = parser.parse_args()

    # 更新配置
    UDP_PORT = args.port
    DEFAULT_DURATION = args.duration
    led_matrix.set_brightness(args.brightness)

    api_key = args.api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("[错误] 请设置 MiniMax API Key (通过--api-key参数或MINIMAX_API_KEY环境变量)")
        print("示例: export MINIMAX_API_KEY=your_api_key_here")
        sys.exit(1)

    check_previous_instance()
    signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup_leds(), cleanup(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda sig, frame: (cleanup_leds(), cleanup(), sys.exit(0)))

    start_server(api_key)
