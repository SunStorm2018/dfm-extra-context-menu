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
    
    # 设置构建环境
    export DEB_BUILD_OPTIONS="parallel=$(nproc)"
    
    # 执行构建命令
    log "执行: dpkg-buildpackage -us -uc -b"
    
    if dpkg-buildpackage -us -uc -b; then
        success "DEB包构建成功!"
        
        # 显示构建产物
        log "构建产物:"
        ls -la ../*.deb 2>/dev/null || true
        
    else
        error "DEB包构建失败!"
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