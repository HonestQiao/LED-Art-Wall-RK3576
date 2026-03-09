"""
WS2812B LED 驱动 - RK3576 SPI0 版本

用于驱动串联的LED灯带，支持坐标映射和颜色控制。
"""

import spidev
import time
import numpy as np
from PIL import Image


class WS2812B:
    """
    WS2812B LED 驱动类
    
    使用 SPI0 接口驱动串联LED灯带，支持：
    - 单点控制
    - 整屏填充
    - 图片显示
    - 亮度调节
    """
    
    # 位编码表：每字节生成3字节SPI数据
    # WS2812B 时序: 0码=0.4us高+0.85us低, 1码=0.8us高+0.45us低
    # SPI@2.4MHz: 每bit=3个SPI bits (0b100=0, 0b110=1)
    _BIT_TABLE = None
    
    def __init__(self, num_leds, spi_bus=0, spi_device=0, speed_hz=2400000):
        """
        初始化 WS2812B 驱动
        
        Args:
            num_leds: LED总数
            spi_bus: SPI总线号 (默认0)
            spi_device: SPI设备号 (默认0)
            speed_hz: SPI时钟频率 (默认2.4MHz)
        """
        self.num_leds = num_leds
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0
        
        # 初始化位编码表
        if WS2812B._BIT_TABLE is None:
            WS2812B._BIT_TABLE = self._init_bit_table()
        
        # LED数据缓冲区 (GRB格式)
        self._buffer = bytearray(num_leds * 3)
        self._brightness = 1.0
        
    def _init_bit_table(self):
        """初始化字节到SPI编码的查找表"""
        table = []
        for i in range(256):
            code = 0
            for bit in range(8):
                b = (i >> (7 - bit)) & 1
                code |= (0x06 if b else 0x04) << (21 - bit * 3)
            table.append(bytes([
                (code >> 16) & 0xFF,
                (code >> 8) & 0xFF,
                code & 0xFF
            ]))
        return table
    
    def _encode_data(self, grb_data):
        """
        将GRB数据编码为SPI传输格式
        
        Args:
            grb_data: GRB格式的字节数组
        Returns:
            编码后的字节数组
        """
        encoded = bytearray()
        for i in range(0, len(grb_data), 3):
            encoded.extend(self._BIT_TABLE[grb_data[i]])      # G
            encoded.extend(self._BIT_TABLE[grb_data[i + 1]])  # R
            encoded.extend(self._BIT_TABLE[grb_data[i + 2]])  # B
        return encoded
    
    def _send_data(self, data):
        """
        发送数据到SPI（处理4096字节限制）
        
        Args:
            data: 要发送的字节数据
        """
        # 添加RESET信号（80us以上低电平 = 1000字节0x00）
        reset = bytes(1000)
        full_data = bytes(data) + reset
        
        # 分块发送（避免4096字节限制）
        for i in range(0, len(full_data), 4096):
            chunk = full_data[i:i + 4096]
            self.spi.xfer3(list(chunk))
    
    def set_pixel(self, index, r, g, b):
        """
        设置单个LED颜色
        
        Args:
            index: LED索引 (0-based)
            r: 红色 (0-255)
            g: 绿色 (0-255)
            b: 蓝色 (0-255)
        """
        if 0 <= index < self.num_leds:
            # 应用亮度
            if self._brightness < 1.0:
                r = int(r * self._brightness)
                g = int(g * self._brightness)
                b = int(b * self._brightness)
            
            idx = index * 3
            self._buffer[idx] = g      # GRB顺序
            self._buffer[idx + 1] = r
            self._buffer[idx + 2] = b
    
    def set_pixel_xy(self, x, y, r, g, b, width):
        """
        通过坐标设置LED颜色（从左到右，从上到下扫描）
        
        假设LED排列为:
        0   1   2   3   ...  width-1
        w   w+1 w+2 ...
        
        Args:
            x: 横坐标 (0-based)
            y: 纵坐标 (0-based)
            r, g, b: 颜色值
            width: 屏幕宽度（列数）
        """
        index = y * width + x
        self.set_pixel(index, r, g, b)
    
    def fill(self, r, g, b):
        """
        填充所有LED为同一颜色
        
        Args:
            r, g, b: 颜色值
        """
        # 应用亮度
        if self._brightness < 1.0:
            r = int(r * self._brightness)
            g = int(g * self._brightness)
            b = int(b * self._brightness)
        
        for i in range(self.num_leds):
            idx = i * 3
            self._buffer[idx] = g
            self._buffer[idx + 1] = r
            self._buffer[idx + 2] = b
    
    def clear(self):
        """清除所有LED（全黑）"""
        self._buffer = bytearray(self.num_leds * 3)
    
    def show(self):
        """刷新显示（将缓冲区数据发送到LED）"""
        encoded = self._encode_data(self._buffer)
        self._send_data(encoded)
    
    def set_brightness(self, brightness):
        """
        设置全局亮度
        
        Args:
            brightness: 亮度值 0.0-1.0
        """
        self._brightness = max(0.0, min(1.0, brightness))
    
    def display_image(self, image, width, height, threshold=128):
        """
        显示PIL图像到LED点阵
        
        Args:
            image: PIL Image对象 (灰度或RGB)
            width: LED屏幕宽度
            height: LED屏幕高度
            threshold: 二值化阈值 (默认128)
        """
        # 转换为灰度图
        if image.mode != 'L':
            img = image.convert('L')
        else:
            img = image.copy()
        
        # 缩放到屏幕尺寸
        img = img.resize((width, height), Image.NEAREST)
        
        # 清空缓冲区
        self.clear()
        
        # 设置像素
        for y in range(height):
            for x in range(width):
                pixel = img.getpixel((x, y))
                if pixel > threshold:
                    # 使用渐变色彩
                    hue = ((x + y) / (width + height)) % 1.0
                    r, g, b = self.hsv_to_rgb(hue, 1.0, 1.0)
                    self.set_pixel_xy(x, y, r, g, b, width)
        
        self.show()
    
    @staticmethod
    def hsv_to_rgb(h, s, v):
        """
        HSV转RGB
        
        Args:
            h: 色相 0.0-1.0
            s: 饱和度 0.0-1.0
            v: 明度 0.0-1.0
        Returns:
            (r, g, b) 元组，0-255
        """
        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = int(v * (1 - s) * 255)
        q = int(v * (1 - f * s) * 255)
        t = int(v * (1 - (1 - f) * s) * 255)
        v_int = int(v * 255)

        if i % 6 == 0:
            return (v_int, t, p)
        elif i % 6 == 1:
            return (q, v_int, p)
        elif i % 6 == 2:
            return (p, v_int, t)
        elif i % 6 == 3:
            return (p, q, v_int)
        elif i % 6 == 4:
            return (t, p, v_int)
        else:
            return (v_int, p, q)
    
    def close(self):
        """关闭SPI设备"""
        self.clear()
        self.show()
        self.spi.close()


class LEDMatrix:
    """
    LED点阵屏控制类
    
    封装了点阵屏的高级功能，包括：
    - 坐标映射（考虑蛇形扫描）
    - 图片显示
    - 文字显示
    - 动画效果
    """
    
    def __init__(self, board_rows, board_cols, 
                 led_rows_per_board, led_cols_per_board,
                 spi_bus=0, spi_device=0, brightness=0.4):
        """
        初始化LED点阵屏
        
        Args:
            board_rows: 垂直方向灯板数量
            board_cols: 水平方向灯板数量
            led_rows_per_board: 每块灯板的行数
            led_cols_per_board: 每块灯板的列数
            spi_bus: SPI总线号
            spi_device: SPI设备号
            brightness: 默认亮度
        """
        self.board_rows = board_rows
        self.board_cols = board_cols
        self.led_rows_per_board = led_rows_per_board
        self.led_cols_per_board = led_cols_per_board
        
        self.screen_cols = board_cols * led_cols_per_board
        self.screen_rows = board_rows * led_rows_per_board
        self.leds_per_board = led_rows_per_board * led_cols_per_board
        self.total_leds = board_rows * board_cols * self.leds_per_board
        
        # 初始化驱动
        self.driver = WS2812B(self.total_leds, spi_bus, spi_device)
        self.driver.set_brightness(brightness)
        
        print(f"[LEDMatrix] 初始化完成: {self.screen_cols}x{self.screen_rows} = {self.total_leds} LEDs")
    
    def get_pixel_index(self, col, row):
        """
        将屏幕坐标转换为LED索引（考虑蛇形扫描）
        
        布局示意图（2x2灯板，每块5x6）：
        板0 (左上) | 板1 (右上)
        板2 (左下) | 板3 (右下)
        
        每块板内部蛇形扫描（从左上开始，偶数行从左到右，奇数行从右到左）
        
        Args:
            col: 列坐标 (0-based)
            row: 行坐标 (0-based)
        Returns:
            LED在串联链中的全局索引
        """
        # 计算所在灯板
        board_row = row // self.led_rows_per_board
        board_col = col // self.led_cols_per_board
        board_index = board_row * self.board_cols + board_col
        
        # 计算在灯板内的位置
        local_row = row % self.led_rows_per_board
        local_col = col % self.led_cols_per_board
        
        # 蛇形扫描：偶数行从左到右，奇数行从右到左
        if local_row % 2 == 0:
            pixel_index = local_row * self.led_cols_per_board + local_col
        else:
            pixel_index = local_row * self.led_cols_per_board + (self.led_cols_per_board - 1 - local_col)
        
        # 计算全局索引
        global_index = board_index * self.leds_per_board + pixel_index
        
        return global_index
    
    def set_pixel(self, col, row, r, g, b):
        """
        设置指定坐标的LED颜色
        
        Args:
            col: 列坐标
            row: 行坐标
            r, g, b: 颜色值 0-255
        """
        index = self.get_pixel_index(col, row)
        self.driver.set_pixel(index, r, g, b)
    
    def fill(self, r, g, b):
        """填充全屏"""
        self.driver.fill(r, g, b)
    
    def clear(self):
        """清除屏幕"""
        self.driver.clear()
    
    def show(self):
        """刷新显示"""
        self.driver.show()
    
    def set_brightness(self, brightness):
        """设置亮度"""
        self.driver.set_brightness(brightness)
    
    def display_image(self, image, threshold=128):
        """
        显示图片
        
        Args:
            image: PIL Image对象
            threshold: 二值化阈值
        """
        # 转换为灰度并缩放
        if image.mode != 'L':
            img = image.convert('L')
        else:
            img = image.copy()
        
        img = img.resize((self.screen_cols, self.screen_rows), Image.NEAREST)
        
        # 设置像素
        self.clear()
        for row in range(self.screen_rows):
            for col in range(self.screen_cols):
                pixel = img.getpixel((col, row))
                if pixel > threshold:
                    # 渐变色彩
                    hue = ((col + row) / (self.screen_cols + self.screen_rows)) % 1.0
                    r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
                    self.set_pixel(col, row, r, g, b)
        
        self.show()
    
    def draw_border(self, hue_offset=0):
        """
        绘制彩色边框
        
        Args:
            hue_offset: 色相偏移，用于动画
        """
        # 上边框
        for col in range(self.screen_cols):
            hue = (col / self.screen_cols + hue_offset) % 1.0
            r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
            self.set_pixel(col, 0, r, g, b)
        
        # 下边框
        for col in range(self.screen_cols):
            hue = (col / self.screen_cols + hue_offset) % 1.0
            r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
            self.set_pixel(col, self.screen_rows - 1, r, g, b)
        
        # 左边框
        for row in range(self.screen_rows):
            hue = (row / self.screen_rows + hue_offset) % 1.0
            r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
            self.set_pixel(0, row, r, g, b)
        
        # 右边框
        for row in range(self.screen_rows):
            hue = (row / self.screen_rows + hue_offset) % 1.0
            r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
            self.set_pixel(self.screen_cols - 1, row, r, g, b)
    
    def show_text(self, text, sub_text=None):
        """
        显示文字（简化版）
        
        Args:
            text: 主文字
            sub_text: 副文字（可选）
        """
        try:
            import os
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建图像
            img = Image.new('L', (self.screen_cols, self.screen_rows), 0)
            draw = ImageDraw.Draw(img)
            
            # 尝试加载字体
            font_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
            
            font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, min(self.screen_rows * 0.5, self.screen_cols / len(text) * 0.8))
                        break
                    except:
                        continue
            
            if font is None:
                font = ImageFont.load_default()
            
            # 计算位置
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (self.screen_cols - text_width) // 2
            y = (self.screen_rows - text_height) // 2
            
            # 绘制文字
            draw.text((x, y), text, fill=255, font=font)
            
            # 显示到LED
            self.clear()
            for row in range(self.screen_rows):
                for col in range(self.screen_cols):
                    if img.getpixel((col, row)) > 127:
                        hue = ((col + row) / (self.screen_cols + self.screen_rows)) % 1.0
                        r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
                        self.set_pixel(col, row, r, g, b)
            
            self.show()
            
        except Exception as e:
            print(f"[LEDMatrix] 显示文字失败: {e}")
    
    def animated_display(self, image, duration=10.0, animated_border=False):
        """
        图片显示（支持可选动画边框）
        
        Args:
            image: PIL Image对象
            duration: 显示时长（秒）
            animated_border: 是否启用动画边框（默认关闭，7200颗LED建议关闭）
        """
        import time
        
        # 准备图片数据
        if image.mode != 'L':
            img = image.convert('L')
        else:
            img = image.copy()
        
        img = img.resize((self.screen_cols, self.screen_rows), Image.NEAREST)
        
        start_time = time.time()
        frame = 0
        
        if animated_border:
            # 动画模式（低帧率，适合少量LED）
            while time.time() - start_time < duration:
                self.clear()
                
                # 绘制图片
                for row in range(self.screen_rows):
                    for col in range(self.screen_cols):
                        pixel = img.getpixel((col, row))
                        if pixel > 127:
                            hue = ((col + row) / (self.screen_cols + self.screen_rows)) % 1.0
                            r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
                            self.set_pixel(col, row, r, g, b)
                
                # 绘制动画边框
                self.draw_border(hue_offset=frame / 30)
                
                self.show()
                time.sleep(0.033)
                frame += 1
        else:
            # 静态模式（推荐7200颗LED使用）
            # 只绘制一次，然后保持显示
            self.clear()
            
            # 绘制图片
            for row in range(self.screen_rows):
                for col in range(self.screen_cols):
                    pixel = img.getpixel((col, row))
                    if pixel > 127:
                        hue = ((col + row) / (self.screen_cols + self.screen_rows)) % 1.0
                        r, g, b = self.driver.hsv_to_rgb(hue, 1.0, 1.0)
                        self.set_pixel(col, row, r, g, b)
            
            # 绘制静态边框
            self.draw_border(hue_offset=0)
            
            # 一次性显示
            self.show()
            print(f"[显示] 静态图片已显示，保持 {duration}秒...")
            
            # 等待期间不刷新，节省CPU
            time.sleep(duration)
    
    def close(self):
        """关闭驱动"""
        self.driver.close()
