#!/usr/bin/env python3
"""
LED点阵屏客户端 - RK3576 适配版

通过UDP发送图片生成请求到 led_matrix_server.py

使用方法:
    python led_matrix_client.py "cute cat"
    python led_matrix_client.py -p "一只可爱的猫咪"
    python led_matrix_client.py -i  # 交互模式
"""

import socket
import json
import sys
import argparse
from datetime import datetime

import config

# 服务器配置（根据实际服务器IP修改）
SERVER_IP = config.DEFAULT_SERVER_IP  # 修改为LED服务器实际IP
SERVER_PORT = config.UDP_PORT  # 与服务器端配置的端口一致


def send_prompt(prompt: str, server_ip: str = SERVER_IP, server_port: int = SERVER_PORT) -> bool:
    """
    发送图片生成请求到LED服务器

    Args:
        prompt: 图片描述提示词
        server_ip: 服务器IP地址
        server_port: 服务器UDP端口

    Returns:
        发送是否成功
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 构建请求数据
    request_data = {
        "prompt": prompt,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    json_str = json.dumps(request_data, ensure_ascii=False)

    try:
        sock.sendto(json_str.encode('utf-8'), (server_ip, server_port))
        print(f"[已发送] 提示词: {prompt}")
        print(f"[目标] {server_ip}:{server_port}")
        return True
    except Exception as e:
        print(f"[发送失败] {e}")
        return False
    finally:
        sock.close()


def send_raw_text(text: str, server_ip: str = SERVER_IP, server_port: int = SERVER_PORT) -> bool:
    """
    发送纯文本到LED服务器（兼容模式）

    Args:
        text: 要发送的文本
        server_ip: 服务器IP地址
        server_port: 服务器UDP端口

    Returns:
        发送是否成功
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(text.encode('utf-8'), (server_ip, server_port))
        print(f"[已发送] {text}")
        print(f"[目标] {server_ip}:{server_port}")
        return True
    except Exception as e:
        print(f"[发送失败] {e}")
        return False
    finally:
        sock.close()


def interactive_mode(server_ip: str, server_port: int):
    """交互模式，循环输入提示词发送"""
    print("=" * 50)
    print("LED点阵屏客户端 - 交互模式")
    print("=" * 50)
    print(f"目标服务器: {server_ip}:{server_port}")
    print("输入图片描述，服务器将生成图片并显示到LED屏幕")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("退出客户端")
                break

            send_prompt(user_input, server_ip, server_port)
            print()

        except KeyboardInterrupt:
            print("\n退出客户端")
            break
        except Exception as e:
            print(f"[错误] {e}")


def main():
    parser = argparse.ArgumentParser(
        description="LED点阵屏客户端 - 发送AI图片生成请求",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python led_matrix_client.py "cute cat"
  python led_matrix_client.py -p "一只可爱的猫咪在草地上玩耍"
  python led_matrix_client.py -i
  python led_matrix_client.py "robot" --ip 192.168.1.100 --port 12346
        """
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="图片描述提示词（例如: 'cute cat'）"
    )

    parser.add_argument(
        "-p", "--prompt-arg",
        dest="prompt_arg",
        help="指定提示词参数（当提示词包含空格时有用）"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式，循环输入提示词"
    )

    parser.add_argument(
        "--ip",
        default=SERVER_IP,
        help=f"服务器IP地址 (默认: {SERVER_IP})"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=SERVER_PORT,
        help=f"服务器UDP端口 (默认: {SERVER_PORT})"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="使用纯文本模式发送（不使用JSON格式）"
    )

    args = parser.parse_args()

    # 确定要使用的提示词
    prompt = args.prompt_arg or args.prompt

    # 交互模式
    if args.interactive:
        interactive_mode(args.ip, args.port)
        return

    # 命令行参数模式
    if prompt:
        if args.raw:
            send_raw_text(prompt, args.ip, args.port)
        else:
            send_prompt(prompt, args.ip, args.port)
    else:
        # 没有参数，显示帮助信息
        parser.print_help()
        print("\n" + "=" * 50)
        print("快捷用法:")
        print("  python led_matrix_client.py \"cute cat\"")
        print("=" * 50)


if __name__ == '__main__':
    main()
