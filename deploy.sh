#!/bin/bash
# 拼豆设计图生成器 - 一键部署脚本 (本地 → Linux)
# 用法:
#   首次部署: bash deploy.sh root@192.168.1.100 --init
#   更新代码: bash deploy.sh root@192.168.1.100
#   指定端口: bash deploy.sh root@192.168.1.100 -p 2222

set -e

# 解析参数
TARGET=""
SSH_PORT=22
INIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --init) INIT=true; shift ;;
        -p)     SSH_PORT="$2"; shift 2 ;;
        *)      TARGET="$1"; shift ;;
    esac
done

if [ -z "$TARGET" ]; then
    echo "用法: bash deploy.sh user@host [--init] [-p port]"
    echo "  首次部署: bash deploy.sh root@192.168.1.100 --init"
    echo "  更新代码: bash deploy.sh root@192.168.1.100"
    exit 1
fi

APP_DIR="/opt/pindou"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSH="ssh -p $SSH_PORT $TARGET"
SCP="scp -P $SSH_PORT"

echo "========================================"
echo "  拼豆设计图生成器 - 部署"
echo "  目标: $TARGET (端口: $SSH_PORT)"
echo "========================================"

# 1. 上传文件
echo ""
echo "[1/3] 上传文件到服务器..."
$SSH "mkdir -p $APP_DIR/templates"

FILES=(
    "app.py"
    "mard_colors.py"
    "gunicorn_config.py"
    "requirements.txt"
    "pindou.service"
    "nginx_pindou.conf"
    "server_setup.sh"
    "templates/index.html"
)

for f in "${FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        echo "  上传 $f"
        $SCP "$SCRIPT_DIR/$f" "$TARGET:$APP_DIR/$f"
    else
        echo "  跳过 $f (不存在)"
    fi
done

# 2. 首次初始化
if [ "$INIT" = true ]; then
    echo ""
    echo "[2/3] 首次初始化服务器环境..."
    $SSH "chmod +x $APP_DIR/server_setup.sh && bash $APP_DIR/server_setup.sh"
else
    echo ""
    echo "[2/3] 跳过初始化 (非首次部署)"
    $SSH "$APP_DIR/venv/bin/pip install --quiet -r $APP_DIR/requirements.txt"
fi

# 3. 重启服务
echo ""
echo "[3/3] 重启服务..."
$SSH "chown -R www-data:www-data $APP_DIR && systemctl restart pindou"

# 验证
echo ""
echo "检查服务状态..."
$SSH "systemctl is-active pindou"

HOST_IP=$(echo "$TARGET" | cut -d'@' -f2)
echo ""
echo "========================================"
echo "  部署完成!"
echo "  访问: http://$HOST_IP"
echo "========================================"
