#!/usr/bin/env python3
"""
拼豆设计图生成器 - 服务器一键部署脚本
用法: sudo python3 setup_server.py
"""
import subprocess
import os
import sys

APP_DIR = "/opt/pindou"
LOG_DIR = "/var/log/pindou"
REPO_URL = "https://github.com/Cat-By-Cat/img2PerlerBeads.git"


def run(cmd, check=True):
    print(f"  >>> {cmd}")
    result = subprocess.run(cmd, shell=True, check=check)
    return result.returncode == 0


def main():
    if os.geteuid() != 0:
        print("请使用 sudo 运行此脚本: sudo python3 setup_server.py")
        sys.exit(1)

    print("=" * 50)
    print("  拼豆设计图生成器 - 一键部署")
    print("=" * 50)

    # 1. 安装系统依赖
    print("\n[1/7] 安装系统依赖...")
    run("apt-get update -qq")
    run("apt-get install -y -qq python3 python3-venv python3-pip nginx git")

    # 2. 拉取代码
    print("\n[2/7] 拉取代码...")
    if os.path.exists(f"{APP_DIR}/.git"):
        print("  已存在，拉取最新代码...")
        run(f"cd {APP_DIR} && git pull")
    else:
        if os.path.exists(APP_DIR):
            run(f"rm -rf {APP_DIR}")
        run(f"git clone {REPO_URL} {APP_DIR}")

    # 3. 创建虚拟环境
    print("\n[3/7] 创建 Python 虚拟环境...")
    if not os.path.exists(f"{APP_DIR}/venv"):
        run(f"python3 -m venv {APP_DIR}/venv")
    run(f"{APP_DIR}/venv/bin/pip install --quiet flask Pillow numpy gunicorn")

    # 4. 创建目录
    print("\n[4/7] 创建目录...")
    os.makedirs(f"{APP_DIR}/uploads", exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # 5. 配置 systemd
    print("\n[5/7] 配置系统服务...")
    run(f"cp {APP_DIR}/pindou.service /etc/systemd/system/pindou.service")
    run("systemctl daemon-reload")
    run("systemctl enable pindou")

    # 6. 配置 nginx
    print("\n[6/7] 配置 Nginx...")
    run(f"cp {APP_DIR}/nginx_pindou.conf /etc/nginx/sites-available/pindou")
    run("ln -sf /etc/nginx/sites-available/pindou /etc/nginx/sites-enabled/pindou")
    run("rm -f /etc/nginx/sites-enabled/default")
    if run("nginx -t"):
        run("systemctl reload nginx")

    # 7. 设置权限并启动
    print("\n[7/7] 启动服务...")
    run(f"chown -R www-data:www-data {APP_DIR}")
    run(f"chown -R www-data:www-data {LOG_DIR}")
    run("systemctl restart pindou")

    # 检查状态
    print("\n检查服务状态...")
    run("systemctl is-active pindou")

    print("\n" + "=" * 50)
    print("  部署完成！")
    print("  访问: http://<你的服务器IP>")
    print("=" * 50)


if __name__ == "__main__":
    main()
