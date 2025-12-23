#!/bin/bash

# DEB包保存器启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
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
        notify-send $urgency_param -a "deb-saver" -i "$icon" "$summary" "$body"
    else
        echo -e "${RED}[NOTIFY-ERROR]${NC} notify-send 未找到，无法发送桌面通知: $summary - $body"
    fi
}

echo "[启动] 启动 DEB包保存器..."

# 检测系统发行版
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    elif type lsb_release >/dev/null 2>&1; then
        echo $(lsb_release -si | tr '[:upper:]' '[:lower:]')
    else
        echo "unknown"
    fi
}

# 安装依赖函数
install_dependencies() {
    local distro=$1
    
    echo "[信息] 检测到系统: $distro"
    
    case $distro in
        debian|ubuntu|deepin|linuxmint|uos)
            sudo apt update
            sudo apt install -y python3 python3-tk -y
            ;;
        centos|rhel|fedora|rocky)
            sudo yum install -y python3 tkinter
            ;;
        arch|manjaro)
            sudo pacman -Sy --noconfirm python tk
            ;;
        opensuse|suse)
            sudo zypper install -y python3 python3-tk
            ;;
        *)
            send_notification "系统不兼容" "不支持的Linux发行版: $distro\n请手动安装依赖: python3, tkinter" "critical" "error"
            echo "[错误] 不支持的Linux发行版: $distro"
            echo "请手动安装以下依赖:"
            echo "  - python3"
            echo "  - tkinter (python3-tk/python3-tkinter)"
            exit 1
            ;;
    esac
}

# 检查并安装Python3
if ! command -v python3 &> /dev/null; then
    echo "[警告] Python3 未安装，尝试自动安装..."
    distro=$(detect_distro)
    install_dependencies $distro
fi

# 检查tkinter是否可用
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] tkinter 不可用，尝试自动安装..."
    distro=$(detect_distro)
    install_dependencies $distro
    
    # 再次检查
    python3 -c "import tkinter" 2>/dev/null
    if [ $? -ne 0 ]; then
        send_notification "依赖安装失败" "tkinter 安装失败，请手动安装\nUbuntu/Debian: sudo apt install python3-tk\nCentOS/RHEL: sudo yum install tkinter" "critical" "error"
        echo "[错误] tkinter 安装失败，请手动安装"
        echo "Ubuntu/Debian: sudo apt install python3-tk"
        echo "CentOS/RHEL: sudo yum install tkinter"
        exit 1
    fi
fi

echo "[成功] 环境检查完成"

# 运行Python应用
# 检查是否在安装路径下运行
if [ -f /usr/share/dfm-xmenu-plugins/deb-saver.py ]; then
    python3 /usr/share/dfm-xmenu-plugins/deb-saver.py
else
    python3 deb-saver.py
fi

echo "[完成] 应用已退出"