# 拼豆设计图生成器 - 一键部署脚本 (Windows → Linux)
# 用法: .\deploy.ps1 -Host "你的服务器IP" -User "root" [-Port 22] [-Init]
# 示例:
#   首次部署: .\deploy.ps1 -Host 192.168.1.100 -User root -Init
#   更新代码: .\deploy.ps1 -Host 192.168.1.100 -User root

param(
    [Parameter(Mandatory=$true)]
    [string]$HostAddr,

    [Parameter(Mandatory=$false)]
    [string]$User = "root",

    [Parameter(Mandatory=$false)]
    [int]$Port = 22,

    [Parameter(Mandatory=$false)]
    [switch]$Init
)

$ErrorActionPreference = "Stop"
$APP_DIR = "/opt/pindou"
$LOCAL_DIR = $PSScriptRoot

# 需要上传的文件
$FILES = @(
    "app.py",
    "mard_colors.py",
    "gunicorn_config.py",
    "requirements.txt",
    "pindou.service",
    "nginx_pindou.conf",
    "server_setup.sh",
    "templates/index.html"
)

$SCP_TARGET = "${User}@${HostAddr}"
$SSH_CMD = "ssh -p $Port $SCP_TARGET"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  拼豆设计图生成器 - 部署" -ForegroundColor Cyan
Write-Host "  目标: $SCP_TARGET" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 上传文件
Write-Host "`n[1/3] 上传文件到服务器..." -ForegroundColor Yellow

# 确保远程目录存在
ssh -p $Port $SCP_TARGET "mkdir -p $APP_DIR/templates"

foreach ($file in $FILES) {
    $localPath = Join-Path $LOCAL_DIR $file
    $remotePath = "$APP_DIR/$file"
    if (Test-Path $localPath) {
        Write-Host "  上传 $file"
        scp -P $Port $localPath "${SCP_TARGET}:${remotePath}"
    } else {
        Write-Host "  跳过 $file (不存在)" -ForegroundColor DarkGray
    }
}

# 2. 首次初始化
if ($Init) {
    Write-Host "`n[2/3] 首次初始化服务器环境..." -ForegroundColor Yellow
    ssh -p $Port $SCP_TARGET "chmod +x $APP_DIR/server_setup.sh && bash $APP_DIR/server_setup.sh"
} else {
    Write-Host "`n[2/3] 跳过初始化 (非首次部署)" -ForegroundColor DarkGray

    # 更新依赖（如果 requirements.txt 有变化）
    ssh -p $Port $SCP_TARGET "$APP_DIR/venv/bin/pip install --quiet -r $APP_DIR/requirements.txt"
}

# 3. 重启服务
Write-Host "`n[3/3] 重启服务..." -ForegroundColor Yellow
ssh -p $Port $SCP_TARGET "chown -R www-data:www-data $APP_DIR && systemctl restart pindou"

# 验证
Write-Host "`n检查服务状态..." -ForegroundColor Yellow
ssh -p $Port $SCP_TARGET "systemctl is-active pindou"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  部署完成!" -ForegroundColor Green
Write-Host "  访问: http://${HostAddr}" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
