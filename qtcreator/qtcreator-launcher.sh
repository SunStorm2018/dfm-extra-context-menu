#!/bin/bash

# Qt Creator启动脚本
# 支持从文件管理器右键菜单启动，自动检测qmake和cmake工程
# 当同时存在两种工程类型时提供选择界面

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
        notify-send $urgency_param -a "qtcreator-launcher" -i "$icon" "$summary" "$body"
    else
        echo -e "${RED}[NOTIFY-ERROR]${NC} notify-send 未找到，无法发送桌面通知: $summary - $body"
    fi
}

# 显示选择对话框的函数
show_project_selection_dialog() {
    local target_path="$1"
    
    # 尝试使用zenity显示对话框
    if command -v zenity >/dev/null 2>&1; then
        choice=$(zenity --title="选择工程类型" --text="检测到多种工程类型，请选择要打开的工程：" \
                   --list --radiolist --column="选择" --column="工程类型" \
                   TRUE "qmake工程 (.pro文件)" FALSE "CMake工程 (CMakeLists.txt文件)" \
                   --width=400 --height=300 2>/dev/null)
        
        case "$choice" in
            "qmake工程 (.pro文件)")
                return 1  # 返回1表示选择qmake
                ;;
            "CMake工程 (CMakeLists.txt文件)")
                return 2  # 返回2表示选择cmake
                ;;
            *)
                return 0  # 返回0表示取消
                ;;
        esac
    # 尝试使用kdialog
    elif command -v kdialog >/dev/null 2>&1; then
        choice=$(kdialog --title="选择工程类型" --radiolist "检测到多种工程类型，请选择要打开的工程：" \
                   1 "qmake工程 (.pro文件)" on 2 "CMake工程 (CMakeLists.txt文件)" off 2>/dev/null)
        
        case "$choice" in
            1)
                return 1  # 返回1表示选择qmake
                ;;
            2)
                return 2  # 返回2表示选择cmake
                ;;
            *)
                return 0  # 返回0表示取消
                ;;
        esac
    # 如果没有GUI对话框工具，使用命令行选择
    else
        echo "检测到多种工程类型："
        echo "1) qmake工程 (.pro文件)"
        echo "2) CMake工程 (CMakeLists.txt文件)"
        echo "0) 取消"
        read -p "请选择 (1/2/0): " choice
        
        case "$choice" in
            1)
                return 1
                ;;
            2)
                return 2
                ;;
            *)
                return 0
                ;;
        esac
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
    send_notification "Qt Creator启动错误" "目录不存在: $target_path" "critical" "error"
    exit 1
fi

# 切换到目标目录
cd "$target_path"

# 检测工程类型
has_pro=false
has_cmake=false

# 递归查找.pro文件（最多3层深度）
find_pro=$(find . -maxdepth 3 -name "*.pro" -type f 2>/dev/null | head -1)
if [ -n "$find_pro" ]; then
    has_pro=true
fi

# 递归查找CMakeLists.txt文件（最多3层深度）
find_cmake=$(find . -maxdepth 3 -name "CMakeLists.txt" -type f 2>/dev/null | head -1)
if [ -n "$find_cmake" ]; then
    has_cmake=true
fi

# 根据检测结果决定如何打开
if [ "$has_pro" = true ] && [ "$has_cmake" = false ]; then
    # 只有qmake工程，直接打开
    exec qtcreator "$target_path"
elif [ "$has_pro" = false ] && [ "$has_cmake" = true ]; then
    # 只有CMake工程，直接打开
    exec qtcreator "$target_path"
elif [ "$has_pro" = true ] && [ "$has_cmake" = true ]; then
    # 两种工程都存在，显示选择对话框
    show_project_selection_dialog "$target_path"
    choice_result=$?
    
    case $choice_result in
        1)
            # 选择qmake工程
            exec qtcreator "$target_path"
            ;;
        2)
            # 选择CMake工程
            exec qtcreator "$target_path"
            ;;
        0)
            # 用户取消
            send_notification "Qt Creator" "用户取消了工程选择" "normal" "info"
            exit 0
            ;;
    esac
else
    # 没有检测到任何工程文件
    send_notification "Qt Creator启动错误" "未检测到Qt工程文件\n未找到.pro或CMakeLists.txt文件" "critical" "error"
    exit 1
fi