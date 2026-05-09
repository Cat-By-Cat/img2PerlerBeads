#!/bin/bash
# 服务器端初始化脚本 - 在 Linux 服务器上执行
# 用途：首次部署时初始化环境

set -e

APP_DIR="/opt/pindou"
LOG_DIR="/var/log/pindou"

echo "=== 拼豆设计图生成器 - 服务器初始化 ==="

# 安装系统依赖
echo "[1/6] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx

# 创建目录
echo "[2/6] 创建应用目录..."
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/templates
mkdir -p $LOG_DIR

# 创建虚拟环境
echo "[3/6] 创建 Python 虚拟环境..."
python3 -m venv $APP_DIR/venv

# 安装依赖
echo "[4/6] 安装 Python 依赖..."
$APP_DIR/venv/bin/pip install --quiet flask Pillow numpy gunicorn

# 配置 systemd 服务
echo "[5/6] 配置系统服务..."
cp $APP_DIR/pindou.service /etc/systemd/system/pindou.service
systemctl daemon-reload
systemctl enable pindou

# 配置 nginx
echo "[6/6] 配置 Nginx..."
cp $APP_DIR/nginx_pindou.conf /etc/nginx/sites-available/pindou
ln -sf /etc/nginx/sites-available/pindou /etc/nginx/sites-enabled/pindou
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 设置权限
chown -R www-data:www-data $APP_DIR
chown -R www-data:www-data $LOG_DIR

echo "=== 初始化完成 ==="
