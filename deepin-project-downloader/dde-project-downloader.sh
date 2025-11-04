#!/bin/bash

# Deepin 项目下载器启动脚本

echo "[启动] 启动 Deepin 项目下载器..."

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
            sudo apt install -y python3 git python3-tk -y
            ;;
        centos|rhel|fedora|rocky)
            sudo yum install -y python3 git tkinter
            ;;
        arch|manjaro)
            sudo pacman -Sy --noconfirm python git tk
            ;;
        opensuse|suse)
            sudo zypper install -y python3 git python3-tk
            ;;
        *)
            echo "[错误] 不支持的Linux发行版: $distro"
            echo "请手动安装以下依赖:"
            echo "  - python3"
            echo "  - git"
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

# 检查并安装Git
if ! command -v git &> /dev/null; then
    echo "[警告] Git 未安装，尝试自动安装..."
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
        echo "[错误] tkinter 安装失败，请手动安装"
        echo "Ubuntu/Debian: sudo apt install python3-tk"
        echo "CentOS/RHEL: sudo yum install tkinter"
        exit 1
    fi
fi

echo "[成功] 环境检查完成"

# 运行Python应用
# 检查是否在安装路径下运行
if [ -f /usr/share/dfm-xmenu-plugins/deepin-project-downloader-backen.py ]; then
    python3 /usr/share/dfm-xmenu-plugins/deepin-project-downloader-backen.py
else
    python3 deepin-project-downloader-backen.py
fi

echo "[完成] 应用已退出"