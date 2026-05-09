#!/usr/bin/env python3
"""
拼豆设计图生成器 - 服务器一键部署脚本
用法: 在项目目录下执行 sudo python3 setup_server.py
"""
import subprocess
import os
import sys


def run(cmd, check=True):
    print(f"  >>> {cmd}")
    result = subprocess.run(cmd, shell=True, check=check)
    return result.returncode == 0


def main():
    if os.geteuid() != 0:
        print("请使用 sudo 运行: sudo python3 setup_server.py")
        sys.exit(1)

    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR = "/var/log/pindou"

    print("=" * 50)
    print("  拼豆设计图生成器 - 一键部署")
    print(f"  项目目录: {APP_DIR}")
    print("=" * 50)

    # 1. 安装系统依赖
    print("\n[1/4] 安装系统依赖...")
    run("apt-get update -qq")
    run("apt-get install -y -qq python3 python3-venv python3-pip")

    # 2. 创建虚拟环境
    print("\n[2/4] 创建 Python 虚拟环境...")
    if not os.path.exists(f"{APP_DIR}/venv"):
        run(f"python3 -m venv {APP_DIR}/venv")
    run(f"{APP_DIR}/venv/bin/pip install --quiet flask Pillow numpy gunicorn")

    # 3. 创建目录 + 权限
    print("\n[3/4] 创建目录与设置权限...")
    os.makedirs(f"{APP_DIR}/uploads", exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    run(f"chown -R www-data:www-data {APP_DIR}/uploads")
    run(f"chown -R www-data:www-data {APP_DIR}/venv")
    run(f"chown -R www-data:www-data {LOG_DIR}")
    run(f"chmod -R o+rX {APP_DIR}")

    # 4. 配置 systemd 服务并启动
    print("\n[4/4] 配置系统服务...")
    service_content = f"""[Unit]
Description=PinDou Bead Pattern Generator
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory={APP_DIR}
ExecStart={APP_DIR}/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/pindou.service", "w") as f:
        f.write(service_content)
    run("systemctl daemon-reload")
    run("systemctl enable pindou")
    run("systemctl restart pindou")

    # 检查状态
    import time
    print("\n检查服务状态（等待3秒）...")
    time.sleep(3)
    result = subprocess.run("systemctl is-active pindou", shell=True, capture_output=True, text=True)
    status = result.stdout.strip()
    print(f"  服务状态: {status}")
    if status != "active":
        print("  服务未正常启动，查看日志：")
        run("journalctl -u pindou -n 20 --no-pager", check=False)

    print("\n" + "=" * 50)
    print("  部署完成！")
    print("  访问: http://<你的服务器IP>:6666")
    print("=" * 50)


if __name__ == "__main__":
    main()
