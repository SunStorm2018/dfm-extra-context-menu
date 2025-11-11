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

# 清理构建缓存函数
clean_build_cache() {
    local source_dir="$1"
    
    log "开始清理构建缓存..."
    
    # 切换到源码目录执行清理
    cd "$source_dir"
    
    # 使用dh_clean清理构建缓存
    if command -v dh_clean >/dev/null 2>&1; then
        log "执行: dh_clean"
        if dh_clean; then
            success "使用dh_clean清理构建缓存成功!"
        else
            error "使用dh_clean清理构建缓存失败!"
            return 1
        fi
    else
        error "dh_clean命令未找到，请确保已安装debhelper包"
        return 1
    fi
    
    # 额外清理debian构建目录
    log "清理debian构建目录..."
    rm -rf debian/.debhelper/
    rm -rf debian/dfm-xmenu-*/
    rm -f debian/files debian/debhelper-build-stamp
    rm -f debian/*.log debian/*.substvars
    
    success "构建缓存清理完成!"
    
    # 发送清理完成通知
    send_notification "构建缓存清理完成" "已清理: $(basename "$source_dir")" "normal"
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
    local clean_after_build="${2:-yes}"  # 默认构建后清理
    local parallel_jobs="${3:-auto}"     # 并行任务数，默认自动检测
    
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
    
    # 确定并行任务数
    local cpu_count=$(nproc)
    local parallel_num
    
    if [ "$parallel_jobs" = "auto" ]; then
        parallel_num=$cpu_count
    elif [ "$parallel_jobs" = "half" ]; then
        parallel_num=$((cpu_count / 2))
        if [ $parallel_num -lt 1 ]; then
            parallel_num=1
        fi
    elif [[ "$parallel_jobs" =~ ^[0-9]+$ ]]; then
        parallel_num=$parallel_jobs
    else
        error "无效的并行任务数: $parallel_jobs"
        exit 1
    fi
    
    log "开始构建DEB包..."
    log "源码目录: $(pwd)"
    log "构建后清理: $clean_after_build"
    log "系统CPU核心数: $cpu_count"
    log "使用并行任务数: $parallel_num"
    
    # 发送开始构建通知
    send_notification "开始构建DEB包" "正在构建: $(basename "$(pwd)") (并行: $parallel_num)" "low"
    
    # 设置构建环境
    export DEB_BUILD_OPTIONS="parallel=$parallel_num"
    
    # 验证debian/rules是否支持并行构建
    log "验证debian/rules配置..."
    if grep -q "parallel" debian/rules; then
        success "debian/rules已配置并行构建支持"
    else
        log "警告: debian/rules可能未正确配置并行构建"
        log "当前DEB_BUILD_OPTIONS=$DEB_BUILD_OPTIONS"
    fi
    
    # 执行构建命令
    log "执行: dpkg-buildpackage -us -uc -b"
    log "构建选项: DEB_BUILD_OPTIONS=$DEB_BUILD_OPTIONS"
    
    # 构建结果标志
    local build_success=false
    
    # 记录构建开始时间
    local build_start_time=$(date +%s)
    
    if dpkg-buildpackage -us -uc -b; then
        local build_end_time=$(date +%s)
        local build_duration=$((build_end_time - build_start_time))
        local build_minutes=$((build_duration / 60))
        local build_seconds=$((build_duration % 60))
        
        build_success=true
        success "DEB包构建成功!"
        success "构建耗时: ${build_minutes}分${build_seconds}秒 (并行任务数: $parallel_num)"
        
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
    fi
    
    # 无论构建成功还是失败，都执行清理（如果设置了清理选项）
    if [ "$clean_after_build" = "yes" ]; then
        echo ""
        if [ "$build_success" = true ]; then
            log "开始清理构建缓存..."
        else
            log "构建失败，开始清理构建缓存..."
        fi
        clean_build_cache "$source_dir"
    else
        log "跳过构建缓存清理"
    fi
    
    # 如果构建失败，退出码为1
    if [ "$build_success" = false ]; then
        exit 1
    fi
}

# 显示帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat << EOF
快速DEB包构建脚本

用法: $0 [源码目录] [构建后清理选项] [并行任务数]

参数:
    源码目录        包含debian目录的源码路径 (默认: 当前目录)
    构建后清理选项  yes/no (默认: yes，构建完成后自动清理构建缓存)
    并行任务数      auto/half/数字 (默认: auto)
                    auto  - 自动使用所有CPU核心
                    half  - 使用一半CPU核心
                    数字  - 指定具体的并行任务数

示例:
    $0                           # 在当前目录构建并清理，使用所有CPU核心
    $0 /path/to/source           # 在指定目录构建并清理，使用所有CPU核心
    $0 . no                      # 在当前目录构建但不清理，使用所有CPU核心
    $0 . yes half                # 在当前目录构建并清理，使用一半CPU核心
    $0 . yes 8                   # 在当前目录构建并清理，使用8个并行任务
    $0 /path/to/source no 4      # 在指定目录构建但不清理，使用4个并行任务

功能特性:
    - 灵活的并行构建选项 (auto/half/指定数字)
    - 自动检测CPU核心数 (使用nproc命令)
    - 构建完成后自动使用dh_clean清理构建缓存
    - 桌面通知提示构建状态
    - 显示构建产物信息
    - DEB_BUILD_OPTIONS环境变量正确设置

环境变量:
    DEB_BUILD_OPTIONS  自动设置为 parallel=N，其中N为并行任务数

EOF
    exit 0
fi

# 执行主函数
main "$@" 