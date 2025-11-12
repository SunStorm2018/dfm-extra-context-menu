#!/bin/bash

# Gitk启动脚本
# 支持从文件管理器右键菜单启动，自动定位到Git仓库

# 颜色定义
RED='\033[0;31m'
NC='\033[0m' # No Color

# 通知函数
send_notification() {
    local summary="$1"
    local body="$2"
    local urgency="${3:-normal}"  # low, normal, critical，默认 normal
    local icon="${4:-package}"    # 可选 icon，默认 package

    # 使用notify-send发送桌面通知
    if command -v notify-send >/dev/null 2>&1; then
        local urgency_param=""
        if [ -n "$urgency" ]; then
            urgency_param="-u $urgency"
        fi
        notify-send $urgency_param -a "gitk-launcher" -i "$icon" "$summary" "$body"
    else
        echo -e "${RED}[NOTIFY-ERROR]${NC} notify-send 未找到，无法发送桌面通知: $summary - $body"
    fi
}

# 获取传入的参数
if [ $# -eq 0 ]; then
    # 没有参数时，使用当前目录
    target_path="."
else
    # 有参数时，使用第一个参数
    target_path="$1"
fi

# 如果是文件，获取其所在目录
if [ -f "$target_path" ]; then
    target_path=$(dirname "$target_path")
fi

# 检查目标路径是否存在
if [ ! -d "$target_path" ]; then
    send_notification "Gitk启动错误" "目录不存在: $target_path" "critical" "error"
    exit 1
fi

# 切换到目标目录
cd "$target_path"

# 检查是否为Git仓库（支持子目录）
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    send_notification "Gitk启动警告" "当前目录不是Git仓库: $target_path" "normal" "warning"
fi

# 启动gitk
exec gitk