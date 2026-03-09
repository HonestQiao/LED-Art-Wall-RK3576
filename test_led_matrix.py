#!/usr/bin/env python3
"""
LED点阵屏测试脚本

测试基础功能：填充、清除、边框、文字显示
"""

import sys
import time
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from ws2812b_driver import LEDMatrix


def test_basic():
    """测试基础功能"""
    print("=" * 60)
    print("LED点阵屏基础测试")
    print("=" * 60)
    print(f"屏幕尺寸: {config.SCREEN_COLS} x {config.SCREEN_ROWS}")
    print(f"总LED数: {config.TOTAL_LEDS}")
    print("=" * 60)
    
    # 初始化
    print("[测试] 初始化LED点阵屏...")
    matrix = LEDMatrix(
        board_rows=config.BOARD_ROWS,
        board_cols=config.BOARD_COLS,
        led_rows_per_board=config.LED_ROWS_PER_BOARD,
        led_cols_per_board=config.LED_COLS_PER_BOARD,
        spi_bus=config.SPI_BUS,
        spi_device=config.SPI_DEVICE,
        brightness=0.4
    )
    
    try:
        # 测试1: 全红
        print("[测试1] 全红...")
        matrix.fill(255, 0, 0)
        matrix.show()
        time.sleep(1)
        
        # 测试2: 全绿
        print("[测试2] 全绿...")
        matrix.fill(0, 255, 0)
        matrix.show()
        time.sleep(1)
        
        # 测试3: 全蓝
        print("[测试3] 全蓝...")
        matrix.fill(0, 0, 255)
        matrix.show()
        time.sleep(1)
        
        # 测试4: 全白
        print("[测试4] 全白...")
        matrix.fill(255, 255, 255)
        matrix.show()
        time.sleep(1)
        
        # 测试5: 清除
        print("[测试5] 清除...")
        matrix.clear()
        matrix.show()
        time.sleep(0.5)
        
        # 测试6: 单点测试（扫描）
        print("[测试6] 单点扫描...")
        for row in range(config.SCREEN_ROWS):
            for col in range(config.SCREEN_COLS):
                matrix.clear()
                # 根据位置显示不同颜色
                hue = ((col + row) / (config.SCREEN_COLS + config.SCREEN_ROWS)) % 1.0
                r, g, b = matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                matrix.set_pixel(col, row, r, g, b)
                matrix.show()
                time.sleep(0.01)
        
        time.sleep(0.5)
        
        # 测试7: 边框动画
        print("[测试7] 边框动画...")
        for i in range(30):
            matrix.clear()
            matrix.draw_border(hue_offset=i / 30)
            matrix.show()
            time.sleep(0.05)
        
        # 测试8: 渐变彩虹
        print("[测试8] 彩虹渐变...")
        matrix.clear()
        for row in range(config.SCREEN_ROWS):
            for col in range(config.SCREEN_COLS):
                hue = (col / config.SCREEN_COLS) % 1.0
                r, g, b = matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                matrix.set_pixel(col, row, r, g, b)
        matrix.show()
        time.sleep(2)
        
        # 测试9: 文字显示
        print("[测试9] 文字显示...")
        matrix.show_text("HI", "RK3576")
        time.sleep(2)
        
        # 测试完成
        print("[测试] 所有测试完成！")
        matrix.clear()
        matrix.show()
        
    except KeyboardInterrupt:
        print("\n[测试] 用户中断")
    finally:
        matrix.close()
        print("[测试] 已清理，退出")


def test_image():
    """测试图片显示"""
    print("=" * 60)
    print("LED点阵屏图片测试")
    print("=" * 60)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[错误] 需要安装 Pillow: pip3 install Pillow")
        return
    
    # 初始化
    matrix = LEDMatrix(
        board_rows=config.BOARD_ROWS,
        board_cols=config.BOARD_COLS,
        led_rows_per_board=config.LED_ROWS_PER_BOARD,
        led_cols_per_board=config.LED_COLS_PER_BOARD,
        spi_bus=config.SPI_BUS,
        spi_device=config.SPI_DEVICE,
        brightness=0.4
    )
    
    try:
        # 创建测试图片
        print("[测试] 创建测试图片...")
        img = Image.new('L', (config.SCREEN_COLS, config.SCREEN_ROWS), 0)
        draw = ImageDraw.Draw(img)
        
        # 绘制矩形
        draw.rectangle([5, 5, config.SCREEN_COLS-5, config.SCREEN_ROWS-5], outline=255, width=2)
        
        # 绘制对角线
        draw.line([(0, 0), (config.SCREEN_COLS-1, config.SCREEN_ROWS-1)], fill=255, width=1)
        draw.line([(config.SCREEN_COLS-1, 0), (0, config.SCREEN_ROWS-1)], fill=255, width=1)
        
        # 绘制中心点
        cx, cy = config.SCREEN_COLS // 2, config.SCREEN_ROWS // 2
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill=255)
        
        # 显示图片
        print("[测试] 显示测试图片...")
        matrix.display_image(img, threshold=128)
        time.sleep(3)
        
        # 测试动画
        print("[测试] 显示带动画的图片...")
        matrix.animated_display(img, duration=5.0)
        
        # 清除
        matrix.clear()
        matrix.show()
        print("[测试] 图片测试完成！")
        
    except KeyboardInterrupt:
        print("\n[测试] 用户中断")
    finally:
        matrix.close()
        print("[测试] 已清理，退出")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="LED点阵屏测试")
    parser.add_argument("--test", choices=["basic", "image", "all"], default="basic",
                       help="测试类型: basic=基础测试, image=图片测试, all=全部")
    
    args = parser.parse_args()
    
    if args.test == "basic":
        test_basic()
    elif args.test == "image":
        test_image()
    else:
        test_basic()
        test_image()
