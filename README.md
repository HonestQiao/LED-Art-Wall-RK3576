# AI智绘光屏 - 源代码说明

## 项目简介

本项目是基于 MYD-LR3576（RK3576）开发板的智能LED点阵显示系统，通过AI大模型生成图像，并实时显示在7200颗LED组成的高清点阵屏上。

## 代码结构

```
.
├── config.py                 # 配置文件（分辨率、SPI参数、网络配置）
├── ws2812b_driver.py        # LED驱动核心（SPI通信、坐标映射）
├── led_matrix_server.py     # UDP服务端（接收请求、AI生成、LED控制）
├── led_matrix_client.py     # UDP客户端（发送显示请求）
├── effect_test.py           # 效果测试脚本（支持42×5和7200两种模式）
├── test_led_matrix.py       # 功能测试脚本
├── requirements.txt         # Python依赖
└── .env.example            # 环境变量示例
```

## 依赖安装

### 系统要求
- MYD-LR3576 开发板（或其他RK3576平台）
- Ubuntu 22.04 / Linux 6.1
- SPI0 接口已启用（详见硬件设计文档）

### Python依赖

```bash
# 安装依赖
sudo pip3 install -r requirements.txt
```

**依赖清单**：
- `spidev>=3.5` - SPI通信库
- `Pillow>=8.0.0` - 图像处理库
- `requests>=2.25.0` - HTTP请求库（用于调用AI API）

## 快速开始

### 1. 配置环境变量

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env，填入你的 MiniMax API Key
nano .env
```

**文件内容**：
```
MINIMAX_API_KEY=你的API密钥
```

> **获取API Key**: 访问 https://www.minimaxi.com/ 注册并获取

### 2. 启动服务端

```bash
# 方式1：使用环境变量
export MINIMAX_API_KEY=你的API密钥
sudo python3 led_matrix_server.py

# 方式2：命令行传参
sudo python3 led_matrix_server.py --api-key 你的API密钥

# 方式3：后台运行
sudo nohup python3 led_matrix_server.py > server.log 2>&1 &
```

**启动参数**：
- `--api-key` - MiniMax API密钥
- `--port` - UDP监听端口（默认12346）
- `--brightness` - LED亮度 0.1-1.0（默认0.4）
- `--duration` - 图片显示时长秒数（默认10.0）

### 3. 发送显示请求

在另一个终端执行：

```bash
# 发送英文提示词
python3 led_matrix_client.py "cute cat"

# 发送中文提示词
python3 led_matrix_client.py "一棵大树"

# 指定服务器IP（从其他设备发送）
python3 led_matrix_client.py "星空夜景" --ip 192.168.1.170
```

**交互模式**：
```bash
python3 led_matrix_client.py -i
```

## 效果测试

### 功能测试

```bash
# 基础功能测试（红绿蓝等）
sudo python3 test_led_matrix.py --test basic

# 图片显示测试
sudo python3 test_led_matrix.py --test image
```

### 效果测试（推荐）

```bash
# 测试42×5模式（210颗LED，适合初期验证）
sudo python3 effect_test.py --config 42x5 --effect all

# 测试完整7200颗模式
sudo python3 effect_test.py --config 144x50 --effect all

# 单独测试特定效果
sudo python3 effect_test.py --effect rainbow    # 彩虹渐变
sudo python3 effect_test.py --effect scanner    # 扫描线
sudo python3 effect_test.py --effect wave       # 波浪
sudo python3 effect_test.py --effect breath     # 呼吸灯
```

## AI模型说明

本项目使用 **MiniMax** 的图像生成服务：

- **模型**: MiniMax image-01
- **API地址**: https://api.minimaxi.com/v1/image_generation
- **调用方式**: HTTP POST，JSON格式请求
- **返回格式**: Base64编码的图片

### 本地部署尝试（失败记录）

在项目初期，我们尝试在RK3576上本地部署智谱的GLM-4V-9B多模态模型：
- FP32版本：内存不足，无法加载
- INT8量化：可加载，但推理一张图需要十几分钟
- INT4量化：速度仍无法接受，图片质量下降严重

**结论**: RK3576资源有限，无法本地运行大模型，最终采用云端API方案。

## 核心算法说明

### SPI时序编码

WS2812B LED需要精确的微秒级时序：
- 0码: 0.4us高 + 0.85us低
- 1码: 0.8us高 + 0.45us低

我们使用SPI0 @ 2.4MHz进行编码：
- 0码 → SPI 0b100 (0x04)
- 1码 → SPI 0b110 (0x06)

每个WS2812B位编码为3个SPI位，通过硬件SPI确保时序精确。

### 坐标映射

10块灯板串联，每块5×144=720颗LED：
- 全局索引 = 板号 × 720 + 板内索引
- 板内采用蛇形扫描（偶数行左→右，奇数行右→左）

## 硬件配置

详见 `../02-技术文档/02-硬件设计.md`，简要参数：

| 参数 | 数值 |
|------|------|
| LED总数 | 7200颗 |
| 分辨率 | 144列 × 50行 |
| SPI速度 | 2.4 MHz |
| 数据量 | ~63KB/帧 |
| 刷新率 | ~3 FPS |

## 常见问题

### Q1: SPI设备不存在？

```bash
# 手动绑定SPI0
echo "spi0.0" | sudo tee /sys/bus/spi/drivers/spidev/bind
sudo chmod 666 /dev/spidev0.0
```

### Q2: LED不亮？

检查清单：
1. SPI0设备是否存在：`ls /dev/spidev0.0`
2. 接线是否正确（Pin19 MOSI, Pin6 GND）
3. 是否共地（LED的GND必须接开发板GND）
4. 供电是否充足（5V/40A推荐）

### Q3: 图片生成失败？

- 检查网络连接
- 确认API Key有效且未过期
- 查看服务端日志：`tail -f server.log`

### Q4: 权限不足？

```bash
sudo chmod 666 /dev/spidev0.0
```

## 性能优化建议

1. **降低亮度**: 减少功耗和发热，建议0.3-0.5
2. **静态显示**: 7200颗LED刷新较慢，适合静态图片
3. **本地缓存**: 重复显示的图片可缓存，减少API调用
4. **分区供电**: 每2-3块板独立供电，避免压降

## 扩展开发

### 添加新效果

在 `effect_test.py` 中添加：

```python
def test_my_effect(self):
    """我的自定义效果"""
    for i in range(100):
        self.matrix.clear()
        # 你的绘图代码
        self.matrix.show()
        time.sleep(0.05)
```

### 接入其他AI模型

修改 `led_matrix_server.py` 中的 `generate_image()` 函数：

```python
def generate_image(prompt: str, api_key: str) -> Image.Image:
    # 替换为其他AI模型的API调用
    # 保持返回PIL Image对象即可
    pass
```

## 开源协议

MIT License

## 联系方式

- 作者: 【需填写：你的名字】
- 邮箱: 【需填写：你的邮箱】
- 项目地址: 【需填写：GitHub链接（如有）】

## 参考资料

- MiniMax API文档: https://www.minimaxi.com/
- WS2812B Datasheet (Worldsemi)
- RK3576 Technical Reference Manual
- Linux SPI Driver Documentation

---

**感谢使用 AI智绘光屏！**
