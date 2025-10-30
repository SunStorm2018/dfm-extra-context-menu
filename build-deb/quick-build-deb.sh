#!/bin/bash

# 快速DEB包构建脚本
# 使用方法: ./quick-build-deb.sh [源码目录]

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# D-Bus通知函数
send_notification() {
    local summary="$1"
    local body="$2"
    local urgency="$3"  # low, normal, critical
    
    # 使用notify-send发送桌面通知
    if command -v notify-send >/dev/null 2>&1; then
        local urgency_param=""
        if [ -n "$urgency" ]; then
            urgency_param="-u $urgency"
        fi
        
        notify-send $urgency_param -a "quick-build-deb" -i "package" "$summary" "$body"
    else
        # 如果notify-send不可用，使用dbus-send
        if command -v dbus-send >/dev/null 2>&1; then
            local timeout=5000  # 5秒
            dbus-send --session --dest=org.freedesktop.Notifications \
                --type=method_call /org/freedesktop/Notifications \
                org.freedesktop.Notifications.Notify \
                string:"quick-build-deb" \
                uint32:0 \
                string:"package" \
                string:"$summary" \
                string:"$body" \
                array:string:"" \
                dict:string:string:"urgency","$urgency" \
                int32:$timeout >/dev/null 2>&1 || true
        fi
    fi
}

# 显示构建产物路径
show_built_packages() {
    local source_dir="$1"
    local deb_files=$(ls -1 ../*.deb 2>/dev/null || true)
    
    if [ -n "$deb_files" ]; then
        log "构建产物:"
        ls -la ../*.deb
        echo "$deb_files"
    else
        error "未找到构建产物"
    fi
}

# 主函数
main() {
    local source_dir="${1:-.}"
    
    echo "=========================================="
    echo "        快速DEB包构建"
    echo "=========================================="
    echo
    
    # 检查源码目录
    if [ ! -d "$source_dir" ]; then
        error "源码目录不存在: $source_dir"
        exit 1
    fi
    
    if [ ! -d "$source_dir/debian" ]; then
        error "缺少debian目录: $source_dir/debian"
        exit 1
    fi
    
    # 切换到源码目录
    cd "$source_dir"
    
    log "开始构建DEB包..."
    log "源码目录: $(pwd)"
    
    # 发送开始构建通知
    send_notification "开始构建DEB包" "正在构建: $(basename "$(pwd)")" "low"
    
    # 设置构建环境
    export DEB_BUILD_OPTIONS="parallel=$(nproc)"
    
    # 执行构建命令
    log "执行: dpkg-buildpackage -us -uc -b"
    
    if dpkg-buildpackage -us -uc -b; then
        success "DEB包构建成功!"
        
        # 显示构建产物
        show_built_packages "$source_dir"
        
        # 发送成功通知
        local deb_files=$(ls -1 ../*.deb 2>/dev/null | head -1)
        if [ -n "$deb_files" ]; then
            local deb_name=$(basename "$deb_files")
            send_notification "DEB包构建完成" "成功构建: $deb_name" "normal"
        else
            send_notification "DEB包构建完成" "构建成功，但未找到构建产物" "normal"
        fi
        
    else
        error "DEB包构建失败!"
        
        # 发送失败通知
        send_notification "DEB包构建失败" "构建过程中出现错误，请检查构建日志" "critical"
        exit 1
    fi
}

# 显示帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat << EOF
快速DEB包构建脚本

用法: $0 [源码目录]

参数:
    源码目录    包含debian目录的源码路径 (默认: 当前目录)

示例:
    $0                    # 在当前目录构建
    $0 /path/to/source    # 在指定目录构建

EOF
    exit 0
fi

# 执行主函数
main "$@" 