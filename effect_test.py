#!/usr/bin/env python3
"""
LED点阵屏效果测试脚本
支持多种测试模式和不同规模的LED配置

适用配置:
- 小规模: 42×5 = 210颗LED (单条测试)
- 大规模: 144×50 = 7200颗LED (10块板串联)
"""

import sys
import time
import math
sys.path.insert(0, '/home/myir/Projects/myir-rk3576/led_matrix')

import config
from ws2812b_driver import LEDMatrix
from PIL import Image, ImageDraw, ImageFont


class EffectTester:
    """LED效果测试器"""
    
    def __init__(self, matrix_config=None, brightness=0.4):
        """
        初始化测试器
        
        Args:
            matrix_config: 自定义配置，None则使用config.py默认配置
            brightness: 亮度 0.0-1.0
        """
        if matrix_config is None:
            # 使用默认配置
            self.matrix = LEDMatrix(
                board_rows=config.BOARD_ROWS,
                board_cols=config.BOARD_COLS,
                led_rows_per_board=config.LED_ROWS_PER_BOARD,
                led_cols_per_board=config.LED_COLS_PER_BOARD,
                spi_bus=config.SPI_BUS,
                spi_device=config.SPI_DEVICE,
                brightness=brightness
            )
            self.cols = config.SCREEN_COLS
            self.rows = config.SCREEN_ROWS
        else:
            # 使用自定义配置
            self.matrix = LEDMatrix(
                board_rows=matrix_config['board_rows'],
                board_cols=matrix_config['board_cols'],
                led_rows_per_board=matrix_config['led_rows_per_board'],
                led_cols_per_board=matrix_config['led_cols_per_board'],
                spi_bus=matrix_config.get('spi_bus', 0),
                spi_device=matrix_config.get('spi_device', 0),
                brightness=brightness
            )
            self.cols = matrix_config['board_cols'] * matrix_config['led_cols_per_board']
            self.rows = matrix_config['board_rows'] * matrix_config['led_rows_per_board']
        
        print(f"[EffectTester] 初始化完成: {self.cols}x{self.rows}")
    
    # ============ 基础效果 ============
    
    def test_rainbow_gradient(self, duration=3.0):
        """彩虹渐变效果"""
        print(f"[效果] 彩虹渐变 ({duration}秒)...")
        
        for row in range(self.rows):
            for col in range(self.cols):
                hue = col / self.cols
                r, g, b = self.matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                self.matrix.set_pixel(col, row, r, g, b)
        
        self.matrix.show()
        time.sleep(duration)
    
    def test_scanner(self, cycles=2, delay=0.05):
        """扫描线效果"""
        print(f"[效果] 扫描线 (cycles={cycles})...")
        
        for _ in range(cycles):
            # 水平扫描
            for col in range(self.cols):
                self.matrix.clear()
                for row in range(self.rows):
                    hue = row / self.rows
                    r, g, b = self.matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                    self.matrix.set_pixel(col, row, r, g, b)
                self.matrix.show()
                time.sleep(delay)
            
            # 垂直扫描
            for row in range(self.rows):
                self.matrix.clear()
                for col in range(self.cols):
                    hue = col / self.cols
                    r, g, b = self.matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                    self.matrix.set_pixel(col, row, r, g, b)
                self.matrix.show()
                time.sleep(delay)
    
    def test_wave(self, cycles=3, delay=0.1):
        """波浪效果"""
        print(f"[效果] 波浪 (cycles={cycles})...")
        
        for t in range(int(cycles * 20)):
            self.matrix.clear()
            for row in range(self.rows):
                for col in range(self.cols):
                    # 正弦波计算
                    wave = math.sin(col * 0.3 + t * 0.5) * math.cos(row * 0.3)
                    if wave > 0:
                        hue = (wave + 1) / 2
                        r, g, b = self.matrix.driver.hsv_to_rgb(hue, 1.0, wave)
                        self.matrix.set_pixel(col, row, r, g, b)
            self.matrix.show()
            time.sleep(delay)
    
    def test_checkerboard(self, duration=2.0):
        """棋盘格效果"""
        print(f"[效果] 棋盘格 ({duration}秒)...")
        
        for row in range(self.rows):
            for col in range(self.cols):
                if (row + col) % 2 == 0:
                    self.matrix.set_pixel(col, row, 255, 255, 255)
                else:
                    self.matrix.set_pixel(col, row, 0, 0, 0)
        
        self.matrix.show()
        time.sleep(duration)
    
    def test_breathing(self, color=(255, 0, 0), cycles=3):
        """呼吸灯效果"""
        print(f"[效果] 呼吸灯 RGB{color} (cycles={cycles})...")
        
        steps = 50
        for _ in range(cycles):
            # 渐亮
            for i in range(steps):
                brightness = i / steps
                r, g, b = int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness)
                self.matrix.fill(r, g, b)
                self.matrix.show()
                time.sleep(0.02)
            
            # 渐暗
            for i in range(steps, 0, -1):
                brightness = i / steps
                r, g, b = int(color[0] * brightness), int(color[1] * brightness), int(color[2] * brightness)
                self.matrix.fill(r, g, b)
                self.matrix.show()
                time.sleep(0.02)
    
    # ============ 文字效果 ============
    
    def test_text_scroll(self, text="Hello", speed=0.1):
        """文字滚动效果"""
        print(f"[效果] 文字滚动: \"{text}\"...")
        
        try:
            img = Image.new('L', (self.cols, self.rows), 0)
            draw = ImageDraw.Draw(img)
            
            # 尝试加载字体
            font = None
            for fp in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                       '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, min(self.rows, 20))
                        break
                    except:
                        pass
            
            if font is None:
                font = ImageFont.load_default()
            
            # 获取文字宽度
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 滚动显示
            for offset in range(-text_width, self.cols + 1):
                img = Image.new('L', (self.cols, self.rows), 0)
                draw = ImageDraw.Draw(img)
                draw.text((-offset, (self.rows - bbox[3]) // 2), text, fill=255, font=font)
                
                # 显示到LED
                self.matrix.clear()
                for row in range(self.rows):
                    for col in range(self.cols):
                        if img.getpixel((col, row)) > 128:
                            hue = col / self.cols
                            r, g, b = self.matrix.driver.hsv_to_rgb(hue, 1.0, 1.0)
                            self.matrix.set_pixel(col, row, r, g, b)
                
                self.matrix.show()
                time.sleep(speed)
                
        except Exception as e:
            print(f"[错误] 文字滚动失败: {e}")
    
    # ============ 几何图案 ============
    
    def test_geometric(self, duration=3.0):
        """几何图案效果"""
        print(f"[效果] 几何图案 ({duration}秒)...")
        
        cx, cy = self.cols // 2, self.rows // 2
        max_radius = min(cx, cy)
        
        for row in range(self.rows):
            for col in range(self.cols):
                dx, dy = col - cx, row - cy
                distance = math.sqrt(dx*dx + dy*dy)
                
                # 同心圆
                if int(distance) % 4 == 0:
                    self.matrix.set_pixel(col, row, 255, 255, 255)
                # 十字线
                elif col == cx or row == cy:
                    self.matrix.set_pixel(col, row, 255, 0, 0)
                # 对角线
                elif abs(dx) == abs(dy):
                    self.matrix.set_pixel(col, row, 0, 255, 0)
        
        self.matrix.show()
        time.sleep(duration)
    
    # ============ 综合测试 ============
    
    def run_all_tests(self):
        """运行所有效果测试"""
        print("=" * 60)
        print("LED点阵屏效果测试")
        print("=" * 60)
        
        tests = [
            ("彩虹渐变", lambda: self.test_rainbow_gradient(2.0)),
            ("扫描线", lambda: self.test_scanner(cycles=1, delay=0.03)),
            ("棋盘格", lambda: self.test_checkerboard(1.5)),
            ("呼吸灯(红)", lambda: self.test_breathing((255, 0, 0), cycles=2)),
            ("呼吸灯(绿)", lambda: self.test_breathing((0, 255, 0), cycles=2)),
            ("呼吸灯(蓝)", lambda: self.test_breathing((0, 0, 255), cycles=2)),
            ("波浪", lambda: self.test_wave(cycles=2, delay=0.05)),
            ("几何图案", lambda: self.test_geometric(2.0)),
        ]
        
        # 根据LED数量调整测试
        if self.cols * self.rows <= 500:  # 小规模如42×5
            print(f"[配置] 小规模LED ({self.cols}x{self.rows})，启用全部动画效果")
            tests.append(("文字滚动", lambda: self.test_text_scroll("Hello RK3576", speed=0.05)))
        else:  # 大规模如144×50
            print(f"[配置] 大规模LED ({self.cols}x{self.rows})，减少动画效果")
        
        for name, test_func in tests:
            print(f"\n[{name}] 开始...")
            try:
                test_func()
            except KeyboardInterrupt:
                print(f"[{name}] 用户中断")
                break
            except Exception as e:
                print(f"[{name}] 错误: {e}")
        
        print("\n[完成] 所有测试结束")
        self.matrix.clear()
        self.matrix.show()
    
    def close(self):
        """关闭测试器"""
        self.matrix.close()


# ============ 预设配置 ============

# 42×5 单条配置（用于初期测试）
CONFIG_42x5 = {
    'board_rows': 1,
    'board_cols': 1,
    'led_rows_per_board': 5,
    'led_cols_per_board': 42,
    'spi_bus': 0,
    'spi_device': 0,
}

# 144×50 完整配置（10块板串联）
CONFIG_144x50 = {
    'board_rows': 10,
    'board_cols': 1,
    'led_rows_per_board': 5,
    'led_cols_per_board': 144,
    'spi_bus': 0,
    'spi_device': 0,
}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='LED点阵屏效果测试')
    parser.add_argument('--config', choices=['42x5', '144x50', 'default'], 
                       default='default',
                       help='LED配置: 42x5=单条测试, 144x50=完整10块板, default=使用config.py')
    parser.add_argument('--brightness', type=float, default=0.4,
                       help='亮度 0.1-1.0 (默认0.4)')
    parser.add_argument('--effect', choices=['rainbow', 'scanner', 'wave', 'checker', 
                                            'breath', 'geometric', 'all'],
                       default='all',
                       help='选择特定效果测试')
    
    args = parser.parse_args()
    
    # 选择配置
    if args.config == '42x5':
        matrix_config = CONFIG_42x5
        print("[配置] 使用42×5单条模式")
    elif args.config == '144x50':
        matrix_config = CONFIG_144x50
        print("[配置] 使用144×50完整模式")
    else:
        matrix_config = None
        print("[配置] 使用config.py默认配置")
    
    # 创建测试器
    tester = EffectTester(matrix_config=matrix_config, brightness=args.brightness)
    
    try:
        # 运行指定效果
        if args.effect == 'rainbow':
            tester.test_rainbow_gradient()
        elif args.effect == 'scanner':
            tester.test_scanner()
        elif args.effect == 'wave':
            tester.test_wave()
        elif args.effect == 'checker':
            tester.test_checkerboard()
        elif args.effect == 'breath':
            tester.test_breathing((255, 0, 0), cycles=3)
        elif args.effect == 'geometric':
            tester.test_geometric()
        else:
            tester.run_all_tests()
    
    except KeyboardInterrupt:
        print("\n[中断] 用户停止测试")
    finally:
        tester.close()
        print("[退出] 已清理")


if __name__ == '__main__':
    import os
    main()
