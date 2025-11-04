#!/bin/bash

# Gitk启动脚本
# 支持从文件管理器右键菜单启动，自动定位到Git仓库

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
    echo "错误：目录不存在: $target_path"
    exit 1
fi

# 切换到目标目录
cd "$target_path"

# 检查是否为Git仓库（支持子目录）
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "警告：当前目录不是Git仓库: $target_path"
fi

# 启动gitk
exec gitk