#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
from pathlib import Path
import queue
import time
import concurrent.futures
import json
import shutil
import glob


class ScrollableFrame(ttk.Frame):
    """可滚动的Frame组件"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # 创建Canvas和Scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._on_frame_configure()
        )
        
        # 创建Canvas窗口
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 绑定Canvas大小变化事件
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # 初始绑定滚动事件
        self._bind_mouse_scroll()
        
        # 布局
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置网格权重
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # 配置Canvas滚动
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
    
    def _on_frame_configure(self):
        """Frame内容变化时更新滚动区域并重新绑定事件"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # 内容变化后重新绑定所有子组件的滚动事件
        self.after_idle(self._bind_all_children)
    
    def _on_canvas_configure(self, event):
        """Canvas大小变化时调整scrollable_frame宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _bind_mouse_scroll(self):
        """绑定鼠标滚轮事件"""
        # 绑定Canvas和主Frame
        self._bind_mousewheel_to_widget(self.canvas)
        self._bind_mousewheel_to_widget(self.scrollable_frame)
        self._bind_mousewheel_to_widget(self)
        
    def _bind_mousewheel_to_widget(self, widget):
        """为单个组件绑定鼠标滚轮事件"""
        # Windows滚轮事件
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        # Linux滚轮事件
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
    
    def _bind_all_children(self):
        """递归绑定所有子组件的鼠标滚轮事件"""
        def bind_recursive(widget):
            self._bind_mousewheel_to_widget(widget)
            for child in widget.winfo_children():
                bind_recursive(child)
        
        bind_recursive(self.scrollable_frame)
    
    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        # Linux系统兼容性处理
        if hasattr(event, 'delta') and event.delta:
            # Windows系统
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            # Linux系统
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
    
    def get_frame(self):
        """获取可滚动的frame"""
        return self.scrollable_frame
    
    def bind_scrolling(self):
        """手动触发绑定所有子组件滚动事件（用于表格创建后）"""
        self.after_idle(self._bind_all_children)

class DeepinProjectDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Deepin 项目下载器")
        self.root.geometry("1200x1000")
        self.root.minsize(1000, 700)
        
        # 设置主题样式
        self.setup_styles()
        
        # 注册程序退出时的清理函数（移除自动清理）
        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.expanduser("~"), ".deepin_project_downloader.json")
        # 配置文件路径
        self.config_file = os.path.join(os.path.expanduser("~"), ".deepin_project_downloader.json")

        
        # 消息队列用于线程间通信
        self.message_queue = queue.Queue()
        
        # 源选择变量
        self.source_var = tk.StringVar(value="gitee")
        
        # 保存路径变量
        self.save_path = tk.StringVar(value=os.path.expanduser("~/debug"))
        
        # 项目选择变量字典
        self.project_vars = {}
        
        # 分支选择变量字典
        self.branch_vars = {}
        
        # 分支选择框字典
        self.branch_combos = {}
        
        # 软件包选择变量字典
        self.package_vars = {}
        
        # 软件包状态标签字典
        self.package_status_labels = {}
        
        # 分支切换状态跟踪
        self.branch_switching = {}
        
        # 进度条字典
        self.progress_bars = {}
        
        # 初始化消息列表
        self.init_messages = []
        
        # 界面控件启用状态管理
        self.controls_enabled = False
        self.project_controls = []  # 存储需要管理的项目控件
        
        # 项目仓库URL配置
        self.project_repos = {
            "deepin-screen-recorder": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-screen-recorder.git",
                "github": "https://github.com/linuxdeepin/deepin-screen-recorder.git"
            },
            "deepin-devicemanager": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-devicemanager.git", 
                "github": "https://github.com/linuxdeepin/deepin-devicemanager.git"
            },
            "deepin-movie-reborn": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-movie-reborn.git",
                "github": "https://github.com/linuxdeepin/deepin-movie-reborn.git"
            },
            "deepin-camera": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-camera.git",
                "github": "https://github.com/linuxdeepin/deepin-camera.git"
            },
            "deepin-editor": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-editor.git", 
                "github": "https://github.com/linuxdeepin/deepin-editor.git"
            },
            "deepin-music": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-music.git", 
                "github": "https://github.com/linuxdeepin/deepin-music.git"
            },
            "deepin-voice-note": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-voice-note.git", 
                "github": "https://github.com/linuxdeepin/deepin-voice-note.git"
            },
            "deepin-compressor": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-compressor.git", 
                "github": "https://github.com/linuxdeepin/deepin-compressor.git"
            }, 
            "deepin-manual": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-manual.git", 
                "github": "https://github.com/linuxdeepin/deepin-manual.git"
            },           
            "deepin-ocr": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-ocr.git", 
                "github": "https://github.com/linuxdeepin/deepin-ocr.git"
            },           
            "deepin-pdfium": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-pdfium.git", 
                "github": "https://github.com/linuxdeepin/deepin-pdfium.git"
            },        
            "deepin-picker": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-picker.git", 
                "github": "https://github.com/linuxdeepin/deepin-picker.git"
            },           
            "deepin-scanner": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-scanner.git", 
                "github": "https://github.com/linuxdeepin/deepin-scanner.git"
            },
            "deepin-reader": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-reader.git", 
                "github": "https://github.com/linuxdeepin/deepin-reader.git"
            },
            "dde-device-formatter": {
                "gitee": "https://gitee.com/linuxdeepin/dde-device-formatter.git", 
                "github": "https://github.com/linuxdeepin/dde-device-formatter.git"
            },
            "deepin-draw": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-draw.git", 
                "github": "https://github.com/linuxdeepin/deepin-draw.git"
            },
            "deepin-log-viewer": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-log-viewer.git", 
                "github": "https://github.com/linuxdeepin/deepin-log-viewer.git"
            },
            "deepin-terminal": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-terminal.git", 
                "github": "https://github.com/linuxdeepin/deepin-terminal.git"
            },
            "deepin-system-monitor": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-system-monitor.git", 
                "github": "https://github.com/linuxdeepin/deepin-system-monitor.git"
            },
            "deepin-downloader": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-downloader.git", 
                "github": "https://github.com/linuxdeepin/deepin-downloader.git"
            },
            "deepin-image-viewer": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-image-viewer.git", 
                "github": "https://github.com/linuxdeepin/deepin-image-viewer.git"
            },
            "image-editor": {
                "gitee": "https://gitee.com/linuxdeepin/image-editor.git", 
                "github": "https://github.com/linuxdeepin/image-editor.git"
            },
            "deepin-font-manager": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-font-manager.git", 
                "github": "https://github.com/linuxdeepin/deepin-font-manager.git"
            },
            "deepin-deb-installer": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-deb-installer.git", 
                "github": "https://github.com/linuxdeepin/deepin-deb-installer.git"
            },
            "deepin-diskmanager": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-diskmanager.git", 
                "github": "https://github.com/linuxdeepin/deepin-diskmanager.git"
            },
            "deepin-album": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-album.git", 
                "github": "https://github.com/linuxdeepin/deepin-album.git"
            },
            "dde-cooperation": {
                "gitee": "https://gitee.com/linuxdeepin/dde-cooperation.git", 
                "github": "https://github.com/linuxdeepin/dde-cooperation.git"
            },
            "dde-grand-search": {
                "gitee": "https://gitee.com/linuxdeepin/dde-grand-search.git", 
                "github": "https://github.com/linuxdeepin/dde-grand-search.git"
            },
            "dde-file-manager": {
                "gitee": "https://gitee.com/linuxdeepin/dde-file-manager.git", 
                "github": "https://github.com/linuxdeepin/dde-file-manager.git"
            },
            "deepin-calculator": {
                "gitee": "https://gitee.com/linuxdeepin/deepin-calculator.git", 
                "github": "https://github.com/linuxdeepin/deepin-calculator.git"
            },
            "media-debuger": {
                "gitee": "https://gitee.com/sunstom/media-debuger.git", 
                "github": "https://github.com/SunStorm2018/media-debuger.git"
            },
            "os-config": {
                "gitee": "https://gerrit.uniontech.com/base/os-config.git",
                "github": "https://gerrit.uniontech.com/base/os-config.git"
            }
        }
        
        # 软件包列表
        self.packages = {
            "gdb": "GUN调试工具",
            "strace": "进程追踪器",
            "git": "Git版本控制系统",
            "gitk": "Git图形化工具",
            "sshfs": "SSH文件系统",
            "git-cola": "Git-cola图形化工具",
            "qtcreator": "Qt Creator IDE",
            "qt5-default": "Qt5开发环境",
            "dde-dconfig-editor": "DDE配置编辑器",
            "d-feet": "D-Bus调试工具",
            "v4l-utils": "Video4Linux工具集",
            "edid-decode": "显示器edid文件解码器",
            "pavucontrol": "pulseaudio控制器",
            "sqlitebrowser": "sqlite数据库管理工具",
            "vainfo": "Video Acceleration (VA) API 信息工具",
            "vdpauinfo": "Video Decode and Presentation API for Unix 信息工具",
            "usbview": "以树形结构USB总线设备查看工具"
        }
        
        # 初始化变量
        for project_name in self.project_repos.keys():
            self.project_vars[project_name] = tk.BooleanVar()
            self.branch_vars[project_name] = tk.StringVar(value="master")
            self.branch_switching[project_name] = False
            
        for package_name in self.packages.keys():
            self.package_vars[package_name] = tk.BooleanVar(value=True)
        
        # 创建界面
        self.create_widgets()
        
        # 加载配置
        self.load_config()
        
        # 更新所有项目的状态显示（在配置加载后）
        self.root.after(100, self.refresh_all_project_status)
        
        # 启动消息队列处理
        self.process_queue()
        
        # 初始状态禁用项目管理控件
        self.root.after(100, lambda: self.set_project_controls_enabled(False))
        
        # 延迟显示初始消息和自动查询分支
        self.root.after(1000, self.show_init_messages)
        self.root.after(1500, self.auto_query_branches_and_enable)
        
        # 绑定滚动事件（延迟执行以确保界面创建完成）
        self.root.after(100, self._bind_all_scroll_events)
    
        # 延迟加载软件源文件（确保日志组件已创建）
        self.root.after(200, self.load_sources_files)
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 18, 'bold'), foreground='#2c3e50')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Info.TLabel', font=('Arial', 10), foreground='#7f8c8d')
        style.configure('Status.TLabel', font=('Arial', 10), foreground='orange')
        
        # 按钮样式 - 使用协调的蓝色调配色
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'), background='#F8F8F8')
        style.configure('Success.TButton', font=('Arial', 10, 'bold'), background='#E4E4E4')
        style.configure('Warning.TButton', font=('Arial', 10, 'bold'), background='#E4E4E4')
        style.configure('Danger.TButton', font=('Arial', 10, 'bold'), background='#d9534f')
        
        # 框架样式
        style.configure('Card.TFrame', relief='solid', borderwidth=1, background='#ecf0f1')
        style.configure('Section.TFrame', relief='groove', borderwidth=2, background='#f8f9fa')
        
        # 标签框架样式
        style.configure('Title.TLabelframe', font=('Arial', 11, 'bold'), foreground='#2c3e50')
        style.configure('Title.TLabelframe.Label', font=('Arial', 11, 'bold'), foreground='#2c3e50')
        
        # 进度条样式
        style.configure('Custom.Horizontal.TProgressbar', 
                       background='#4a90e2', 
                       troughcolor='#ecf0f1',
                       borderwidth=0,
                       lightcolor='#4a90e2',
                       darkcolor='#357abd')
        
        # 树形视图样式
        style.configure('Treeview', font=('Arial', 9), rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), foreground='#2c3e50')
        
        # 选项卡样式
        style.configure('TNotebook', background='#ecf0f1')
        style.configure('TNotebook.Tab', font=('Arial', 10, 'bold'), padding=[10, 5])
        
        # 输入框样式
        style.configure('TEntry', font=('Arial', 10), fieldbackground='#ffffff')
        style.configure('TCombobox', font=('Arial', 10))
        
        # 复选框样式
        style.configure('TCheckbutton', font=('Arial', 10))
        
        # 滚动条样式
        style.configure('TScrollbar', background='#bdc3c7', troughcolor='#ecf0f1', width=12)
    
    def set_project_controls_enabled(self, enabled):
        """设置项目管理控件的启用/禁用状态"""
        self.controls_enabled = enabled
        
        # 设置项目checkbox状态
        if hasattr(self, 'project_checkboxes'):
            for project_name, checkbox in self.project_checkboxes.items():
                checkbox.config(state=tk.NORMAL if enabled else tk.DISABLED)
        
        # 设置分支combobox状态
        for project_name, combo in self.branch_combos.items():
            combo.config(state="readonly" if enabled else "disabled")
        
        # 设置操作按钮状态
        if hasattr(self, 'operation_buttons'):
            for button in self.operation_buttons:
                button.config(state=tk.NORMAL if enabled else tk.DISABLED)
        
        # 更新状态提示
        if enabled:
            self.log_message("[就绪] 界面控件已启用，可以进行操作")
        else:
            self.log_message("[等待] 界面控件已禁用，正在加载数据...")
    
    def auto_query_branches_and_enable(self):
        """自动查询分支并在完成后启用控件"""
        def query_and_enable_task():
            try:
                # 先自动查询分支
                self.auto_query_branches()
                
                # 等待查询完成（简单延迟，实际应该用更好的同步机制）
                import time
                time.sleep(3)
                
                # 应用保存的分支配置
                self.apply_saved_branches()
                
                # 启用控件
                self.message_queue.put(("enable_controls", True))
                self.message_queue.put(("log", "[完成] 分支查询和配置加载完成，界面已就绪"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 自动查询和启用过程出错: {str(e)}"))
                # 即使出错也要启用控件
                self.message_queue.put(("enable_controls", True))
        
        # 在后台线程执行
        threading.Thread(target=query_and_enable_task, daemon=True).start()
    
    def _bind_all_scroll_events(self):
        """绑定所有滚动区域的鼠标事件"""
        if hasattr(self, 'project_scroll'):
            self.project_scroll.bind_scrolling()
        if hasattr(self, 'package_scroll'):
            self.package_scroll.bind_scrolling()
        if hasattr(self, 'config_scroll'):
            self.config_scroll.bind_scrolling()
        
    def get_current_projects(self):
        """根据当前选择的源获取项目URL字典"""
        source = self.source_var.get()
        return {name: repos[source] for name, repos in self.project_repos.items()}
    
    def get_auth_credentials(self, project_name, url):
        """获取认证凭据对话框"""
        try:
            # 创建对话框
            dialog = tk.Toplevel(self.root)
            dialog.title(f"项目 {project_name} 需要认证")
            dialog.geometry("600x350")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.resizable(False, False)
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.root.winfo_rootx() + 50,
                self.root.winfo_rooty() + 50
            ))
            
            result = {'username': None, 'password': None, 'cancelled': False}
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text=f"项目 {project_name} 需要Git认证", font=("Arial", 12, "bold"))
            title_label.pack(pady=(0, 10))
            
            # URL显示
            url_label = ttk.Label(main_frame, text=f"仓库地址: {url}", foreground="gray")
            url_label.pack(pady=(0, 15))
            
            # 用户名输入
            ttk.Label(main_frame, text="用户名:").pack(anchor="w")
            username_var = tk.StringVar(value="ut005769")
            username_entry = ttk.Entry(main_frame, textvariable=username_var, width=30)
            username_entry.pack(fill=tk.X, pady=(2, 10))
            
            # 密码输入
            ttk.Label(main_frame, text="密码:").pack(anchor="w")
            password_var = tk.StringVar()
            password_entry = ttk.Entry(main_frame, textvariable=password_var, show="*", width=30)
            password_entry.pack(fill=tk.X, pady=(2, 15))
            
            # 提示
            tip_label = ttk.Label(main_frame, text="请输入Gerrit认证信息", foreground="orange")
            tip_label.pack(pady=(0, 15))
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            def on_ok():
                if not password_var.get().strip():
                    messagebox.showwarning("警告", "密码不能为空！")
                    return
                result['username'] = username_var.get().strip()
                result['password'] = password_var.get().strip()
                dialog.destroy()
            
            def on_cancel():
                result['cancelled'] = True
                dialog.destroy()
            
            # 确定按钮
            ok_btn = ttk.Button(button_frame, text="确定", command=on_ok)
            ok_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            # 取消按钮  
            cancel_btn = ttk.Button(button_frame, text="取消", command=on_cancel)
            cancel_btn.pack(side=tk.RIGHT)
            
            # 设置焦点到密码输入框
            password_entry.focus_set()
            
            # 绑定Enter键
            password_entry.bind('<Return>', lambda e: on_ok())
            username_entry.bind('<Return>', lambda e: password_entry.focus_set())
            
            # 等待对话框关闭
            dialog.wait_window()
            
            return result
            
        except Exception as e:
            self.log_message(f"[错误] 获取认证凭据失败: {str(e)}")
            return {'username': None, 'password': None, 'cancelled': True}
    
    def build_authenticated_url(self, url, username, password):
        """构建带认证信息的URL"""
        try:
            from urllib.parse import urlparse, urlunparse, quote
            
            parsed = urlparse(url)
            
            # URL编码用户名和密码，特别是处理特殊字符如@
            encoded_username = quote(username, safe='')
            encoded_password = quote(password, safe='')
            
            # 构建带认证信息的URL
            auth_url = urlunparse((
                parsed.scheme,
                f"{encoded_username}:{encoded_password}@{parsed.netloc}",
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            return auth_url
            
        except Exception as e:
            self.log_message(f"[错误] 构建认证URL失败: {str(e)}")
            return url
    
    def requires_auth(self, project_name, url):
        """检测项目是否需要认证"""
        # 目前只有os-config项目需要认证
        return project_name == "os-config" and "gerrit.uniontech.com" in url
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 加载保存路径
                if 'save_path' in config:
                    old_path = self.save_path.get()
                    self.save_path.set(config['save_path'])
                    self.init_messages = [f"[配置] 保存路径已加载: {old_path} -> {config['save_path']}"]
                else:
                    self.init_messages = [f"[配置] 使用默认保存路径: {self.save_path.get()}"]
                
                # 加载源选择
                if 'source' in config:
                    old_source = self.source_var.get()
                    self.source_var.set(config['source'])
                    self.init_messages.append(f"[配置] 下载源已加载: {old_source} -> {config['source']}")
                else:
                    self.init_messages.append(f"[配置] 使用默认下载源: {self.source_var.get()}")
                
                # 存储分支配置用于稍后应用
                self.saved_branches = config.get('branches', {})
                branch_count = len(self.saved_branches)
                self.init_messages.append(f"[配置] 分支配置已加载: {branch_count} 个项目的分支设置")
                if branch_count > 0:
                    for project, branch in self.saved_branches.items():
                        self.init_messages.append(f"[配置] - {project}: {branch}")
                
                # 加载SSHFS配置
                if 'sshfs' in config:
                    sshfs_config = config['sshfs']
                    if 'host' in sshfs_config:
                        self.sshfs_host_var.set(sshfs_config.get('host', ''))
                    if 'username' in sshfs_config:
                        self.sshfs_username_var.set(sshfs_config.get('username', ''))
                    if 'remote_path' in sshfs_config:
                        self.sshfs_remote_path_var.set(sshfs_config.get('remote_path', '/'))
                    if 'local_path' in sshfs_config:
                        self.sshfs_local_path_var.set(sshfs_config.get('local_path', ''))
                    
                    sshfs_count = sum(1 for v in sshfs_config.values() if v)
                    self.init_messages.append(f"[配置] SSHFS配置已加载: {sshfs_count} 个参数")
                else:
                    self.init_messages.append("[配置] 使用默认SSHFS配置")
                
                self.init_messages.append("[配置] 配置文件加载完成")
            else:
                self.saved_branches = {}
                self.init_messages = [f"[配置] 配置文件不存在: {self.config_file}"]
                self.init_messages.append("[配置] 使用默认配置")
        except Exception as e:
            self.saved_branches = {}
            self.init_messages = [f"[错误] 加载配置失败: {str(e)}"]
            self.init_messages.append("[配置] 将使用默认配置")
    
    def save_config(self):
        """保存配置文件"""
        try:
            self.log_message("[配置] 开始保存配置文件...")
            
            config = {
                'save_path': self.save_path.get(),
                'source': self.source_var.get(),
                'branches': {},
                'sshfs': {
                    'host': self.sshfs_host_var.get(),
                    'username': self.sshfs_username_var.get(),
                    'remote_path': self.sshfs_remote_path_var.get(),
                    'local_path': self.sshfs_local_path_var.get()
                }
            }
            
            # 保存当前分支选择
            branch_count = 0
            for project_name, branch_var in self.branch_vars.items():
                branch = branch_var.get()
                config['branches'][project_name] = branch
                branch_count += 1
                self.log_message(f"[配置] 保存分支设置: {project_name} -> {branch}")
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"[配置] 配置已保存到: {self.config_file}")
            self.log_message(f"[配置] 保存路径: {config['save_path']}")
            self.log_message(f"[配置] 下载源: {config['source']}")
            self.log_message(f"[配置] 分支设置: {branch_count} 个项目")
            
            # 记录SSHFS配置保存
            sshfs_config = config['sshfs']
            sshfs_count = sum(1 for v in sshfs_config.values() if v)
            self.log_message(f"[配置] SSHFS配置已保存: {sshfs_count} 个参数")
            if sshfs_config['host']:
                self.log_message(f"[配置] SSHFS主机: {sshfs_config['host']}")
            if sshfs_config['username']:
                self.log_message(f"[配置] SSHFS用户名: {sshfs_config['username']}")
            if sshfs_config['remote_path']:
                self.log_message(f"[配置] SSHFS远程路径: {sshfs_config['remote_path']}")
            if sshfs_config['local_path']:
                self.log_message(f"[配置] SSHFS本地路径: {sshfs_config['local_path']}")
            
        except Exception as e:
            self.log_message(f"[错误] 保存配置失败: {str(e)}")
            self.log_message(f"[错误] 配置文件路径: {self.config_file}")
    
    def batch_delete_selected(self):
        """批量删除选中的项目文件夹"""
        selected_projects = [name for name, var in self.project_vars.items() if var.get()]
        
        if not selected_projects:
            messagebox.showwarning("警告", "请至少选择一个项目进行删除")
            return
        
        # 确认删除操作
        response = messagebox.askyesno(
            "确认批量删除",
            f"是否确认删除以下 {len(selected_projects)} 个项目的文件夹？\n\n" +
            "\n".join([f"• {name}" for name in selected_projects]) +
            f"\n\n删除路径: {self.save_path.get()}\n\n此操作不可恢复！",
            icon="warning"
        )
        
        if not response:
            return
        
        def delete_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("log", f"[开始] 批量删除 {len(selected_projects)} 个项目文件夹"))
                
                success_count = 0
                error_count = 0
                
                for project_name in selected_projects:
                    try:
                        project_path = os.path.join(self.save_path.get(), project_name)
                        
                        if os.path.exists(project_path):
                            import shutil
                            shutil.rmtree(project_path)
                            self.message_queue.put(("log", f"[成功] 已删除 {project_name} 文件夹"))
                            # 更新项目状态显示
                            self.message_queue.put(("update_project_status", project_name))
                            success_count += 1
                        else:
                            self.message_queue.put(("log", f"[跳过] {project_name} 文件夹不存在"))
                    except Exception as e:
                        self.message_queue.put(("log", f"[失败] {project_name} 删除失败: {str(e)}"))
                        error_count += 1
                
                self.message_queue.put(("log", f"[完成] 批量删除完成! 成功: {success_count}, 失败: {error_count}"))
                self.message_queue.put(("status", "批量删除完成"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 批量删除过程中出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=delete_task, daemon=True).start()
    
    def detect_local_branches(self):
        """检测本地仓库的所有分支并更新分支选择选项"""
        def detect_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在检测本地项目分支..."))
                
                detected_count = 0
                not_found_count = 0
                error_count = 0
                
                for project_name in self.project_repos.keys():
                    project_path = os.path.join(self.save_path.get(), project_name)
                    
                    if os.path.exists(project_path):
                        if os.path.exists(os.path.join(project_path, ".git")):
                            try:
                                # 获取所有本地分支
                                local_result = subprocess.run(
                                    ["git", "branch", "-a"],
                                    capture_output=True, text=True, cwd=project_path
                                )
                                
                                # 获取当前分支
                                current_result = subprocess.run(
                                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                    capture_output=True, text=True, cwd=project_path
                                )
                                
                                if local_result.returncode == 0 and current_result.returncode == 0:
                                    current_branch = current_result.stdout.strip()
                                    
                                    # 解析所有分支
                                    all_branches = set()
                                    for line in local_result.stdout.strip().split('\n'):
                                        if line.strip():
                                            # 清理分支名称
                                            branch = line.strip().replace('* ', '').replace('  ', '')
                                            if branch.startswith('remotes/origin/'):
                                                # 远程分支，去掉前缀
                                                branch = branch.replace('remotes/origin/', '')
                                            if branch and branch != 'HEAD' and '->' not in branch:
                                                all_branches.add(branch)
                                    
                                    # 转换为列表并排序
                                    branch_list = sorted(list(all_branches))
                                    
                                    if branch_list:
                                        # 更新分支选择框的选项
                                        self.message_queue.put(("branches", project_name, branch_list))
                                        
                                        # 设置当前分支为选中项（避免触发分支切换事件）
                                        if current_branch and current_branch in branch_list:
                                            old_branch = self.branch_vars[project_name].get()
                                            # 临时禁用事件绑定，避免触发分支切换
                                            combo = self.branch_combos[project_name]
                                            combo.unbind('<<ComboboxSelected>>')
                                            
                                            self.branch_vars[project_name].set(current_branch)
                                            
                                            # 重新绑定事件
                                            combo.bind('<<ComboboxSelected>>', 
                                                     lambda e, name=project_name: self.on_branch_changed(e, name))
                                            
                                            self.message_queue.put(("log", f"[检测] {project_name} 分支选项已更新，当前分支: {current_branch}"))
                                            self.message_queue.put(("log", f"[检测] {project_name} 可用分支: {', '.join(branch_list)}"))
                                        else:
                                            self.message_queue.put(("log", f"[检测] {project_name} 当前分支未知，可用分支: {', '.join(branch_list)}"))
                                        
                                        detected_count += 1
                                    else:
                                        self.message_queue.put(("log", f"[检测] {project_name} 没有找到可用分支"))
                                        error_count += 1
                                else:
                                    self.message_queue.put(("log", f"[检测] {project_name} Git命令执行失败"))
                                    error_count += 1
                            
                            except Exception as e:
                                self.message_queue.put(("log", f"[错误] 检测 {project_name} 分支失败: {str(e)}"))
                                error_count += 1
                        else:
                            self.message_queue.put(("log", f"[检测] {project_name} 目录存在但不是Git仓库"))
                            not_found_count += 1
                    else:
                        self.message_queue.put(("log", f"[检测] {project_name} 本地目录不存在: {project_path}"))
                        not_found_count += 1
                
                # 输出检测结果统计
                total_projects = len(self.project_repos)
                self.message_queue.put(("log", f"[检测] 本地分支检测完成: 总计 {total_projects} 个项目"))
                self.message_queue.put(("log", f"[检测] 检测成功: {detected_count} 个，未找到: {not_found_count} 个，错误: {error_count} 个"))
                self.message_queue.put(("status", "本地分支检测完成"))
                    
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 批量检测本地分支失败: {str(e)}"))
                import traceback
                self.message_queue.put(("log", f"[错误] 详细错误信息: {traceback.format_exc()}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=detect_task, daemon=True).start()
        
    def apply_saved_branches(self):
        """应用保存的分支配置"""
        try:
            self.log_message("[配置] 开始应用保存的分支配置...")
            
            if hasattr(self, 'saved_branches') and self.saved_branches:
                self.log_message(f"[配置] 找到 {len(self.saved_branches)} 个项目的分支配置")
                
                applied_count = 0
                skipped_count = 0
                
                for project_name, saved_branch in self.saved_branches.items():
                    if project_name in self.branch_vars and project_name in self.branch_combos:
                        combo = self.branch_combos[project_name]
                        available_branches = list(combo['values']) if combo['values'] else []
                        
                        if saved_branch in available_branches:
                            old_branch = self.branch_vars[project_name].get()
                            if old_branch != saved_branch:
                                # 临时禁用事件绑定，避免触发分支切换
                                combo.unbind('<<ComboboxSelected>>')
                                
                                self.branch_vars[project_name].set(saved_branch)
                                
                                # 重新绑定事件
                                combo.bind('<<ComboboxSelected>>', 
                                         lambda e, name=project_name: self.on_branch_changed(e, name))
                                
                                self.log_message(f"[配置] {project_name} 分支配置已应用: {old_branch} -> {saved_branch}")
                                applied_count += 1
                            else:
                                self.log_message(f"[配置] {project_name} 分支配置已是当前分支: {saved_branch}")
                                applied_count += 1
                        else:
                            self.log_message(f"[警告] {project_name} 保存的分支 '{saved_branch}' 不在可用分支列表中")
                            if available_branches:
                                self.log_message(f"[提示] {project_name} 可用分支: {', '.join(available_branches)}")
                            skipped_count += 1
                    else:
                        self.log_message(f"[错误] {project_name} 项目不存在或分支选择框未初始化，跳过分支配置")
                        skipped_count += 1
                
                self.log_message(f"[配置] 分支配置应用完成: 成功 {applied_count} 个，跳过 {skipped_count} 个")
            else:
                self.log_message("[配置] 没有找到保存的分支配置")
            
            self.log_message("[配置] 分支配置应用流程完成")
                            
        except Exception as e:
            self.log_message(f"[错误] 应用分支配置失败: {str(e)}")
            import traceback
            self.log_message(f"[错误] 详细错误信息: {traceback.format_exc()}")
    
    def show_init_messages(self):
        """显示初始化过程中的消息"""
        if hasattr(self, 'init_messages'):
            for message in self.init_messages:
                self.log_message(message)
            # 清除消息避免重复显示
            delattr(self, 'init_messages')
    
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 创建Tab页管理器
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        main_frame.rowconfigure(0, weight=3)  # 给Tab页更大权重
        
        # 配置Tab页
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="基础配置")
        config_tab.columnconfigure(0, weight=1)
        config_tab.rowconfigure(0, weight=1)
        
        # 为基础配置添加滚动区域
        self.config_scroll = ScrollableFrame(config_tab)
        self.config_scroll.grid(row=0, column=0, sticky="nsew")
        
        # 实际的配置内容框架
        config_content_frame = self.config_scroll.scrollable_frame
        config_content_frame.columnconfigure(0, weight=1)
        
        # 源选择区域（可折叠）
        source_container = ttk.Frame(config_content_frame)
        source_container.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        source_container.columnconfigure(0, weight=1)
        
        # 源选择标题栏（包含折叠按钮）
        source_header_frame = ttk.Frame(source_container, relief="ridge", borderwidth=1)
        source_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        source_header_frame.columnconfigure(1, weight=1)
        
        # 折叠按钮
        self.source_collapsed = tk.BooleanVar(value=True)  # 默认折叠
        self.source_toggle_btn = ttk.Button(source_header_frame, text="▶", width=3, 
                                           command=self.toggle_source_section)
        self.source_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # 源选择标题
        ttk.Label(source_header_frame, text="源选择", font=("", 9, "bold")).grid(
            row=0, column=1, padx=(0, 5), pady=5, sticky="w"
        )
        
        # 源选择内容区域
        self.source_content_frame = ttk.Frame(source_container, relief="ridge", borderwidth=1)
        self.source_content_frame.columnconfigure(2, weight=1)
        # 默认不显示内容区域（折叠状态）
        
        ttk.Label(self.source_content_frame, text="选择下载源:").grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
        source_combo = ttk.Combobox(self.source_content_frame, textvariable=self.source_var, 
                                   values=("gitee", "github"), state="readonly", width=15)
        source_combo.grid(row=0, column=1, padx=(0, 10), pady=(5, 2), sticky="w")
        source_combo.bind('<<ComboboxSelected>>', self.on_source_changed)
        
        ttk.Label(self.source_content_frame, text="(优先推荐使用 Gitee 源，速度更快)", 
                 foreground="gray").grid(row=0, column=2, padx=(0, 10), pady=(5, 2), sticky="w")
        
        # 在源选择区域添加保存按钮
        ttk.Button(self.source_content_frame, text="保存配置", command=self.save_config, style='Success.TButton').grid(
            row=0, column=3, padx=(5, 10), pady=(5, 2), sticky="e"
        )
        
        # 保存路径选择区域（可折叠）
        path_container = ttk.Frame(config_content_frame)
        path_container.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        path_container.columnconfigure(0, weight=1)
        
        # 保存路径标题栏（包含折叠按钮）
        path_header_frame = ttk.Frame(path_container, relief="ridge", borderwidth=1)
        path_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        path_header_frame.columnconfigure(1, weight=1)
        
        # 折叠按钮
        self.path_collapsed = tk.BooleanVar(value=False)  # 默认展开
        self.path_toggle_btn = ttk.Button(path_header_frame, text="▼", width=3, 
                                         command=self.toggle_path_section)
        self.path_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # 保存路径标题
        ttk.Label(path_header_frame, text="保存路径", font=("", 9, "bold")).grid(
            row=0, column=1, padx=(0, 5), pady=5, sticky="w"
        )
        
        # 保存路径内容区域
        self.path_content_frame = ttk.Frame(path_container, relief="ridge", borderwidth=1)
        self.path_content_frame.grid(row=1, column=0, sticky="ew")  # 默认显示（展开状态）
        self.path_content_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(self.path_content_frame, textvariable=self.save_path, state="readonly").grid(
            row=0, column=0, sticky="ew", padx=(10, 5), pady=(5, 10)
        )
        ttk.Button(self.path_content_frame, text="选择路径", command=self.select_path, style='Primary.TButton').grid(
            row=0, column=1, padx=(5, 5), pady=(5, 10)
        )
        ttk.Button(self.path_content_frame, text="一键清理", command=self.cleanup_all, style='Warning.TButton').grid(
            row=0, column=2, padx=(5, 10), pady=(5, 10)
        )
        
        # Git初始化区域（可折叠）
        git_container = ttk.Frame(config_content_frame)
        git_container.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        git_container.columnconfigure(0, weight=1)
        
        # Git标题栏（包含折叠按钮）
        git_header_frame = ttk.Frame(git_container, relief="ridge", borderwidth=1)
        git_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        git_header_frame.columnconfigure(1, weight=1)
        
        # 折叠按钮
        self.git_collapsed = tk.BooleanVar(value=True)  # 默认折叠
        self.git_toggle_btn = ttk.Button(git_header_frame, text="▶", width=3, 
                                        command=self.toggle_git_section)
        self.git_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # Git标题（可更新状态）
        self.git_title_var = tk.StringVar(value="Git 初始化 - 未配置")
        self.git_title_label = ttk.Label(git_header_frame, textvariable=self.git_title_var, font=("", 9, "bold"))
        self.git_title_label.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        
        # Git内容区域
        self.git_content_frame = ttk.Frame(git_container, relief="ridge", borderwidth=1)
        self.git_content_frame.columnconfigure(1, weight=1)
        # 默认不显示内容区域（折叠状态）
        
        # Git用户名
        ttk.Label(self.git_content_frame, text="用户名:").grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
        self.git_name_var = tk.StringVar(value="zhanghongyuan")
        git_name_entry = ttk.Entry(self.git_content_frame, textvariable=self.git_name_var, width=30)
        git_name_entry.grid(row=0, column=1, padx=(0, 10), pady=(5, 2), sticky="ew")
        
        # Git邮箱
        ttk.Label(self.git_content_frame, text="邮箱:").grid(row=1, column=0, padx=(10, 5), pady=2, sticky="w")
        self.git_email_var = tk.StringVar(value="zhanghongyuan@uniontech.com")
        git_email_entry = ttk.Entry(self.git_content_frame, textvariable=self.git_email_var, width=30)
        git_email_entry.grid(row=1, column=1, padx=(0, 10), pady=2, sticky="ew")
        
        # 应用按钮
        ttk.Button(self.git_content_frame, text="应用配置", command=self.apply_git_config, style='Success.TButton').grid(
            row=0, column=2, rowspan=2, padx=(5, 10), pady=(5, 2)
        )
        
        # 状态标签
        self.git_status_var = tk.StringVar(value="未配置")
        self.git_status_label = ttk.Label(self.git_content_frame, textvariable=self.git_status_var, foreground="orange")
        self.git_status_label.grid(row=2, column=0, columnspan=3, padx=(10, 10), pady=(5, 10), sticky="w")
        
        # 确保默认折叠状态（内容区域隐藏）
        # Git内容区域默认不显示，直到用户点击展开
        
        # 自动应用Git配置
        self.root.after(1000, self.apply_git_config)
        
        # SSH配置区域（可折叠）
        ssh_container = ttk.Frame(config_content_frame)
        ssh_container.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        ssh_container.columnconfigure(0, weight=1)
        
        # SSH标题栏（包含折叠按钮）
        ssh_header_frame = ttk.Frame(ssh_container, relief="ridge", borderwidth=1)
        ssh_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        ssh_header_frame.columnconfigure(1, weight=1)
        
        # SSH折叠按钮
        self.ssh_collapsed = tk.BooleanVar(value=True)  # 默认折叠
        self.ssh_toggle_btn = ttk.Button(ssh_header_frame, text="▶", width=3, 
                                        command=self.toggle_ssh_section)
        self.ssh_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # SSH标题（可更新状态）
        self.ssh_title_var = tk.StringVar(value="SSH 配置 - 检测中...")
        self.ssh_title_label = ttk.Label(ssh_header_frame, textvariable=self.ssh_title_var, font=("", 9, "bold"))
        self.ssh_title_label.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        
        # SSH内容区域
        self.ssh_content_frame = ttk.Frame(ssh_container, relief="ridge", borderwidth=1)
        self.ssh_content_frame.columnconfigure(1, weight=1)
        # 默认不显示内容区域（折叠状态）
        
        # SSH服务状态
        ttk.Label(self.ssh_content_frame, text="SSH状态:").grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
        self.ssh_status_var = tk.StringVar(value="检测中...")
        ttk.Label(self.ssh_content_frame, textvariable=self.ssh_status_var, foreground="orange").grid(
            row=0, column=1, padx=(0, 5), pady=(5, 2), sticky="w"
        )
        
        # SSH操作按钮
        ssh_btn_frame = ttk.Frame(self.ssh_content_frame)
        ssh_btn_frame.grid(row=0, column=2, padx=(5, 10), pady=(5, 2), sticky="e")
        
        ttk.Button(ssh_btn_frame, text="安装SSH", command=self.install_ssh_server, style='Success.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(ssh_btn_frame, text="启动SSH", command=self.start_ssh_service, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(ssh_btn_frame, text="检查状态", command=self.check_ssh_status, style='Primary.TButton').pack(
            side=tk.LEFT
        )
        
        # SSH连接信息
        ttk.Label(self.ssh_content_frame, text="SSH地址:").grid(row=1, column=0, padx=(10, 5), pady=2, sticky="w")
        self.ssh_address_var = tk.StringVar(value="获取中...")
        ssh_address_entry = ttk.Entry(self.ssh_content_frame, textvariable=self.ssh_address_var, state="readonly")
        ssh_address_entry.grid(row=1, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 复制按钮
        ttk.Button(self.ssh_content_frame, text="复制", command=self.copy_ssh_address, style='Primary.TButton').grid(
            row=1, column=2, padx=(5, 10), pady=2
        )
        
        # 刷新SSH信息
        self.root.after(1500, self.refresh_ssh_info)
        
        # SSHFS配置区域（可折叠）
        sshfs_container = ttk.Frame(config_content_frame)
        sshfs_container.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        sshfs_container.columnconfigure(0, weight=1)
        
        # SSHFS标题栏（包含折叠按钮）
        sshfs_header_frame = ttk.Frame(sshfs_container, relief="ridge", borderwidth=1)
        sshfs_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        sshfs_header_frame.columnconfigure(1, weight=1)
        
        # SSHFS折叠按钮
        self.sshfs_collapsed = tk.BooleanVar(value=True)  # 默认折叠
        self.sshfs_toggle_btn = ttk.Button(sshfs_header_frame, text="▶", width=3, 
                                          command=self.toggle_sshfs_section)
        self.sshfs_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # SSHFS标题（可更新状态）
        self.sshfs_title_var = tk.StringVar(value="SSHFS 配置 - 检测中...")
        self.sshfs_title_label = ttk.Label(sshfs_header_frame, textvariable=self.sshfs_title_var, font=("", 9, "bold"))
        self.sshfs_title_label.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        
        # SSHFS内容区域
        self.sshfs_content_frame = ttk.Frame(sshfs_container, relief="ridge", borderwidth=1)
        self.sshfs_content_frame.columnconfigure(1, weight=1)
        # 默认不显示内容区域（折叠状态）
        
        # SSHFS状态
        ttk.Label(self.sshfs_content_frame, text="SSHFS状态:").grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
        self.sshfs_status_var = tk.StringVar(value="检测中...")
        ttk.Label(self.sshfs_content_frame, textvariable=self.sshfs_status_var, foreground="orange").grid(
            row=0, column=1, padx=(0, 5), pady=(5, 2), sticky="w"
        )
        
        # SSHFS操作按钮
        sshfs_btn_frame = ttk.Frame(self.sshfs_content_frame)
        sshfs_btn_frame.grid(row=0, column=2, padx=(5, 10), pady=(5, 2), sticky="e")
        
        ttk.Button(sshfs_btn_frame, text="安装sshfs", command=self.install_sshfs, style='Success.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(sshfs_btn_frame, text="检查状态", command=self.check_sshfs_status, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(sshfs_btn_frame, text="打开文件夹", command=self.open_sshfs_folder, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(sshfs_btn_frame, text="挂载", command=self.mount_sshfs, style='Success.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(sshfs_btn_frame, text="取消挂载", command=self.umount_sshfs, style='Warning.TButton').pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(sshfs_btn_frame, text="强退SSHFS", command=self.force_kill_sshfs, style='Danger.TButton').pack(
            side=tk.LEFT
        )
        
        # SSHFS命令
        ttk.Label(self.sshfs_content_frame, text="SSHFS命令:").grid(row=1, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_command_var = tk.StringVar(value="")
        sshfs_command_entry = ttk.Entry(self.sshfs_content_frame, textvariable=self.sshfs_command_var, state="readonly")
        sshfs_command_entry.grid(row=1, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 复制命令按钮
        ttk.Button(self.sshfs_content_frame, text="复制", command=self.copy_sshfs_command, style='Primary.TButton').grid(
            row=1, column=2, padx=(5, 10), pady=2
        )
        
        # 主机地址
        ttk.Label(self.sshfs_content_frame, text="主机地址:").grid(row=2, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_host_var = tk.StringVar(value="")
        sshfs_host_entry = ttk.Entry(self.sshfs_content_frame, textvariable=self.sshfs_host_var)
        sshfs_host_entry.grid(row=2, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 用户名
        ttk.Label(self.sshfs_content_frame, text="用户名:").grid(row=3, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_username_var = tk.StringVar(value="")
        sshfs_username_entry = ttk.Entry(self.sshfs_content_frame, textvariable=self.sshfs_username_var)
        sshfs_username_entry.grid(row=3, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 远程路径
        ttk.Label(self.sshfs_content_frame, text="远程路径:").grid(row=4, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_remote_path_var = tk.StringVar(value="/")
        sshfs_remote_path_entry = ttk.Entry(self.sshfs_content_frame, textvariable=self.sshfs_remote_path_var)
        sshfs_remote_path_entry.grid(row=4, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 本地路径
        ttk.Label(self.sshfs_content_frame, text="本地路径:").grid(row=5, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_local_path_var = tk.StringVar(value="")
        sshfs_local_path_entry = ttk.Entry(self.sshfs_content_frame, textvariable=self.sshfs_local_path_var)
        sshfs_local_path_entry.grid(row=5, column=1, padx=(0, 5), pady=2, sticky="ew")
        
        # 选择路径按钮
        ttk.Button(self.sshfs_content_frame, text="选择路径", command=self.select_sshfs_local_path, style='Primary.TButton').grid(
            row=5, column=2, padx=(5, 10), pady=2
        )
        
        # 终端语言选择
        ttk.Label(self.sshfs_content_frame, text="终端语言:").grid(row=6, column=0, padx=(10, 5), pady=2, sticky="w")
        self.sshfs_language_var = tk.StringVar(value="English")
        language_combo = ttk.Combobox(self.sshfs_content_frame, textvariable=self.sshfs_language_var, 
                                     values=["English", "中文"], state="readonly", width=10)
        language_combo.grid(row=6, column=1, padx=(0, 5), pady=2, sticky="w")
        language_combo.bind('<<ComboboxSelected>>', self.on_language_changed)
        
        # 初始化SSHFS配置
        self.root.after(2000, self.init_sshfs_config)
        
        # SSHFS状态检查控制标志
        self.sshfs_status_checking = False
        
        # SSHFS密码缓存变量
        self.sshfs_password_cache = None
        
        # SSHFS挂载命令缓存变量
        self.sshfs_mount_cmd_cache = None
        
        # 系统信息区域（可折叠）
        system_info_container = ttk.Frame(config_content_frame)
        system_info_container.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        system_info_container.columnconfigure(0, weight=1)
        
        # 系统信息标题栏（包含折叠按钮）
        system_info_header_frame = ttk.Frame(system_info_container, relief="ridge", borderwidth=1)
        system_info_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        system_info_header_frame.columnconfigure(1, weight=1)
        
        # 折叠按钮
        self.system_info_collapsed = tk.BooleanVar(value=False)  # 默认展开
        self.system_info_toggle_btn = ttk.Button(system_info_header_frame, text="▼", width=3, 
                                                command=self.toggle_system_info_section)
        self.system_info_toggle_btn.grid(row=0, column=0, padx=(5, 5), pady=5)
        
        # 系统信息标题
        ttk.Label(system_info_header_frame, text="系统信息", font=("", 9, "bold")).grid(
            row=0, column=1, padx=(0, 5), pady=5, sticky="w"
        )
        
        # 系统信息内容区域
        self.system_info_content_frame = ttk.Frame(system_info_container, relief="ridge", borderwidth=1)
        self.system_info_content_frame.grid(row=1, column=0, sticky="ew")  # 默认显示（展开状态）
        self.system_info_content_frame.columnconfigure(1, weight=1)
        
        # 机型信息
        ttk.Label(self.system_info_content_frame, text="机型信息:").grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="w")
        self.hardware_var = tk.StringVar(value="检测中...")
        ttk.Label(self.system_info_content_frame, textvariable=self.hardware_var, foreground="orange").grid(row=0, column=1, padx=(0, 10), pady=(5, 2), sticky="w")
        
        # 显示协议
        ttk.Label(self.system_info_content_frame, text="显示协议:").grid(row=1, column=0, padx=(10, 5), pady=2, sticky="w")
        self.display_protocol_var = tk.StringVar(value="检测中...")
        ttk.Label(self.system_info_content_frame, textvariable=self.display_protocol_var, foreground="orange").grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        
        # 刷新按钮
        ttk.Button(self.system_info_content_frame, text="刷新信息", command=self.refresh_system_info, style='Primary.TButton').grid(
            row=0, column=2, rowspan=4, padx=(5, 10), pady=(5, 2)
        )
        
        # 产品信息区域（动态添加）
        self.product_info_start_row = 4  # 产品信息从第4行开始显示
        
        # 自动获取系统信息
        self.root.after(500, self.refresh_system_info)
        
        # 项目管理Tab页
        project_tab = ttk.Frame(notebook)
        notebook.add(project_tab, text="项目管理")
        project_tab.columnconfigure(0, weight=1)
        project_tab.rowconfigure(0, weight=1)  # 表格区域占主要空间
        
        # 项目选择区域 - 直接在tab页中
        project_frame = ttk.Frame(project_tab, padding="5")
        project_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))
        project_frame.columnconfigure(0, weight=1)
        project_frame.rowconfigure(0, weight=1)
        
        # 项目选择表格
        self.branch_combos = {}
        self.create_project_table(project_frame)
        
        # 固定的操作按钮区域（不滚动）
        operations_frame = ttk.Frame(project_tab)
        operations_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        operations_frame.columnconfigure(0, weight=1)
        operations_frame.columnconfigure(1, weight=1)
        
        # 分支操作按钮区域
        branch_ops_frame = ttk.LabelFrame(operations_frame, text="分支操作", padding="8", style='Title.TLabelframe')
        branch_ops_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        branch_buttons = [
            ("查询远程分支", self.query_all_branches, 'Primary.TButton'),
            ("检测本地分支", self.detect_local_branches, 'Primary.TButton'), 
            ("合并查询分支", self.query_and_detect_branches, 'Primary.TButton')
        ]
        
        for i, (text, command, style_name) in enumerate(branch_buttons):
            btn = ttk.Button(branch_ops_frame, text=text, command=command, style=style_name)
            btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 项目操作按钮区域
        project_ops_frame = ttk.LabelFrame(operations_frame, text="项目操作", padding="8", style='Title.TLabelframe') 
        project_ops_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        project_buttons = [
            ("下载选中项目", self.download_selected, 'Success.TButton'),
            ("安装选中依赖", self.install_dependencies, 'Success.TButton'),
            ("批量删除选中", self.batch_delete_selected, 'Danger.TButton'),
            ("打开下载目录", self.open_download_dir, 'Primary.TButton')
        ]
        
        # 存储需要管理的操作按钮
        self.operation_buttons = []
        
        for i, (text, command, style_name) in enumerate(project_buttons):
            btn = ttk.Button(project_ops_frame, text=text, command=command, style=style_name)
            btn.pack(side=tk.LEFT, padx=5, pady=2)
            self.operation_buttons.append(btn)
        
        # 将分支操作按钮也加入管理列表
        for i, (text, command, style_name) in enumerate(branch_buttons):
            btn_widgets = branch_ops_frame.winfo_children()
            if i < len(btn_widgets):
                self.operation_buttons.append(btn_widgets[i])
        
        # 软件包管理Tab页
        package_tab = ttk.Frame(notebook)
        notebook.add(package_tab, text="软件包管理")
        package_tab.columnconfigure(0, weight=1)
        package_tab.rowconfigure(0, weight=1)  # 表格区域占主要空间
        
        # 软件包管理区域 - 直接在tab页中
        package_frame = ttk.Frame(package_tab, padding="5")
        package_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))
        package_frame.columnconfigure(0, weight=1)
        package_frame.rowconfigure(0, weight=1)
        
        # 软件包选择区域
        self.create_package_table(package_frame)
        
        # 固定的软件包操作按钮区域（不滚动）
        package_ops_frame = ttk.Frame(package_tab)
        package_ops_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # 选择操作区域
        select_ops_frame = ttk.LabelFrame(package_ops_frame, text="选择操作", padding="8", style='Title.TLabelframe')
        select_ops_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(select_ops_frame, text="全选", command=self.select_all_packages, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        ttk.Button(select_ops_frame, text="全不选", command=self.deselect_all_packages, style='Warning.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        ttk.Button(select_ops_frame, text="反选", command=self.invert_package_selection, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        ttk.Button(select_ops_frame, text="检查状态", command=self.check_package_status, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        
        # 包管理操作区域
        manage_ops_frame = ttk.LabelFrame(package_ops_frame, text="包管理操作", padding="8", style='Title.TLabelframe')
        manage_ops_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(manage_ops_frame, text="安装选中", command=self.install_packages, style='Success.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        ttk.Button(manage_ops_frame, text="移除选中", command=self.remove_packages, style='Danger.TButton').pack(
            side=tk.LEFT, padx=(0, 5), pady=2
        )
        
        # 软件源管理Tab页
        sources_tab = ttk.Frame(notebook)
        notebook.add(sources_tab, text="软件源管理")
        sources_tab.columnconfigure(0, weight=1)
        sources_tab.rowconfigure(0, weight=1)
        
        # 创建软件源管理界面
        self.create_sources_management(sources_tab)

        # Host管理标签页
        host_tab = ttk.Frame(notebook)
        notebook.add(host_tab, text="Host管理")
        host_tab.columnconfigure(0, weight=1)
        host_tab.rowconfigure(0, weight=1)
        
        # 创建Host管理界面
        self.create_host_management(host_tab)

        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10", style='Title.TLabelframe')
        log_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        # 为日志区域设置权重和最小高度，防止被完全挤压
        main_frame.rowconfigure(1, weight=1, minsize=250)
        
        # 日志文本框（适当调整高度）
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.NORMAL, 
                                                 font=('Consolas', 9), 
                                                 background='#f8f9fa',
                                                 foreground='#2c3e50',
                                                 insertbackground='#4a90e2')
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 绑定事件阻止编辑，但允许选择和复制
        self.log_text.bind("<KeyPress>", self._on_key_press)  # 控制键盘输入
        self.log_text.bind("<Button-2>", lambda e: "break")  # 阻止中键粘贴
        self.log_text.bind("<Button-3>", self._show_log_context_menu)  # 右键菜单
        
        # 在日志区域添加清空日志按钮
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        ttk.Button(log_button_frame, text="清空日志", command=self.clear_log, style='Warning.TButton').pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', style='Custom.Horizontal.TProgressbar')
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel')
        status_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
    def apply_git_config(self):
        """应用Git配置"""
        try:
            name = self.git_name_var.get().strip()
            email = self.git_email_var.get().strip()
            
            if not name or not email:
                self.git_status_var.set("用户名和邮箱不能为空")
                self.git_title_var.set("Git 初始化 - 用户名和邮箱不能为空")
                self.git_status_label.config(foreground="red")
                return
            
            # 设置Git全局配置
            result1 = subprocess.run(
                ["git", "config", "--global", "user.name", name],
                capture_output=True, text=True, timeout=10
            )
            
            result2 = subprocess.run(
                ["git", "config", "--global", "user.email", email],
                capture_output=True, text=True, timeout=10
            )
            
            if result1.returncode == 0 and result2.returncode == 0:
                self.git_status_var.set(f"Git配置成功 - {name} <{email}>")
                self.git_title_var.set(f"Git 初始化 - 配置成功")
                self.git_status_label.config(foreground="green")
                self.log_message(f"[Git] Git全局配置已设置: {name} <{email}>")
            else:
                error_msg = result1.stderr or result2.stderr or "未知错误"
                self.git_status_var.set(f"Git配置失败: {error_msg}")
                self.git_title_var.set("Git 初始化 - 配置失败")
                self.git_status_label.config(foreground="red")
                self.log_message(f"[Git] Git配置失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            self.git_status_var.set("Git配置超时")
            self.git_title_var.set("Git 初始化 - 配置超时")
            self.git_status_label.config(foreground="red")
            self.log_message("[Git] Git配置操作超时")
        except FileNotFoundError:
            self.git_status_var.set("未找到Git命令")
            self.git_title_var.set("Git 初始化 - 未找到Git命令")
            self.git_status_label.config(foreground="red")
            self.log_message("[Git] 系统中未找到Git命令，请先安装Git")
        except Exception as e:
            self.git_status_var.set(f"Git配置异常: {str(e)}")
            self.git_title_var.set("Git 初始化 - 配置异常")
            self.git_status_label.config(foreground="red")
            self.log_message(f"[Git] Git配置过程中出错: {str(e)}")

    def toggle_git_section(self):
        """切换Git配置区域的折叠/展开状态"""
        if self.git_collapsed.get():
            # 当前是折叠状态，展开
            self.git_content_frame.grid(row=1, column=0, sticky="ew")
            self.git_toggle_btn.config(text="▼")
            self.git_collapsed.set(False)
            self.log_message("[界面] Git配置区域已展开")
        else:
            # 当前是展开状态，折叠
            self.git_content_frame.grid_remove()
            self.git_toggle_btn.config(text="▶")
            self.git_collapsed.set(True)
            self.log_message("[界面] Git配置区域已折叠")
    
    def toggle_source_section(self):
        """切换源选择区域的折叠/展开状态"""
        if self.source_collapsed.get():
            # 当前是折叠状态，展开
            self.source_content_frame.grid(row=1, column=0, sticky="ew")
            self.source_toggle_btn.config(text="▼")
            self.source_collapsed.set(False)
            self.log_message("[界面] 源选择区域已展开")
        else:
            # 当前是展开状态，折叠
            self.source_content_frame.grid_remove()
            self.source_toggle_btn.config(text="▶")
            self.source_collapsed.set(True)
            self.log_message("[界面] 源选择区域已折叠")
    
    def toggle_path_section(self):
        """切换保存路径区域的折叠/展开状态"""
        if self.path_collapsed.get():
            # 当前是折叠状态，展开
            self.path_content_frame.grid(row=1, column=0, sticky="ew")
            self.path_toggle_btn.config(text="▼")
            self.path_collapsed.set(False)
            self.log_message("[界面] 保存路径区域已展开")
        else:
            # 当前是展开状态，折叠
            self.path_content_frame.grid_remove()
            self.path_toggle_btn.config(text="▶")
            self.path_collapsed.set(True)
            self.log_message("[界面] 保存路径区域已折叠")
    
    def toggle_ssh_section(self):
        """切换SSH区域的折叠/展开状态"""
        if self.ssh_collapsed.get():
            # 当前是折叠状态，展开
            self.ssh_content_frame.grid(row=1, column=0, sticky="ew")
            self.ssh_toggle_btn.config(text="▼")
            self.ssh_collapsed.set(False)
            self.log_message("[界面] SSH配置区域已展开")
        else:
            # 当前是展开状态，折叠
            self.ssh_content_frame.grid_remove()
            self.ssh_toggle_btn.config(text="▶")
            self.ssh_collapsed.set(True)
            self.log_message("[界面] SSH配置区域已折叠")

    def toggle_system_info_section(self):
        """切换系统信息区域的折叠/展开状态"""
        if self.system_info_collapsed.get():
            # 当前是折叠状态，展开
            self.system_info_content_frame.grid(row=1, column=0, sticky="ew")
            self.system_info_toggle_btn.config(text="▼")
            self.system_info_collapsed.set(False)
            self.log_message("[界面] 系统信息区域已展开")
        else:
            # 当前是展开状态，折叠
            self.system_info_content_frame.grid_remove()
            self.system_info_toggle_btn.config(text="▶")
            self.system_info_collapsed.set(True)
            self.log_message("[界面] 系统信息区域已折叠")

    def refresh_system_info(self):
        """刷新系统信息"""
        def info_task():
            try:
                # 获取机型信息
                hardware_info = self.get_hardware_info()
                self.hardware_var.set(hardware_info)
                
                # 获取显示协议
                display_info = self.get_display_protocol()
                self.display_protocol_var.set(display_info)
                
                # 获取产品信息并动态添加到界面
                self.update_product_info()
                
                self.log_message("[系统信息] 系统信息获取完成")
                
            except Exception as e:
                self.log_message(f"[系统信息] 获取系统信息时出错: {str(e)}")
        
        threading.Thread(target=info_task, daemon=True).start()
    

    def get_hardware_info(self):
        """获取机型信息"""
        try:
            # 尝试使用dmidecode获取机型信息
            result = subprocess.run(['dmidecode', '-t', '1'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                manufacturer = ""
                product = ""
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Manufacturer:'):
                        manufacturer = line.split(':', 1)[1].strip()
                    elif line.startswith('Product Name:'):
                        product = line.split(':', 1)[1].strip()
                
                if manufacturer and product:
                    return f"{manufacturer} {product}"
                elif manufacturer:
                    return manufacturer
                elif product:
                    return product
                else:
                    return "未知机型"
            else:
                # 没有dmidecode权限时的备用方案
                return self.get_hardware_info_fallback()
        except subprocess.TimeoutExpired:
            return "检测超时"
        except FileNotFoundError:
            return self.get_hardware_info_fallback()
        except Exception:
            return "获取失败"
    
    def get_hardware_info_fallback(self):
        """获取机型信息的备用方案"""
        try:
            # 尝试读取/sys/class/dmi/id/下的信息
            try:
                with open('/sys/class/dmi/id/sys_vendor', 'r') as f:
                    vendor = f.read().strip()
                with open('/sys/class/dmi/id/product_name', 'r') as f:
                    product = f.read().strip()
                return f"{vendor} {product}"
            except:
                # 最后的备用方案
                import platform
                return platform.node() or "未知机型"
        except Exception:
            return "获取失败"
    

    def get_display_protocol(self):
        """获取显示协议信息"""
        try:
            import os
            
            # 检查XDG_SESSION_TYPE环境变量
            session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
            wayland_display = os.environ.get('WAYLAND_DISPLAY', '')
            display = os.environ.get('DISPLAY', '')
            
            if session_type == 'wayland' or wayland_display:
                return "Wayland"
            elif session_type == 'x11' or display:
                return "X11"
            elif session_type:
                return session_type.upper()
            else:
                # 尝试检测运行中的显示服务器
                try:
                    # 检查是否有wayland相关进程
                    result_wayland = subprocess.run(['pgrep', '-f', 'wayland'], capture_output=True, timeout=3)
                    if result_wayland.returncode == 0:
                        return "Wayland (推测)"
                    
                    # 检查是否有X11相关进程
                    result_x11 = subprocess.run(['pgrep', '-f', 'Xorg'], capture_output=True, timeout=3)
                    if result_x11.returncode == 0:
                        return "X11 (推测)"
                    
                    return "未知协议"
                except Exception:
                    return "检测失败"
        except Exception:
            return "获取失败"

    def get_product_info(self):
        """获取产品信息"""
        try:
            product_info = {}
            with open('/etc/product-info', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")  # 去掉引号
                        product_info[key] = value if value else "空"
            return product_info
        except FileNotFoundError:
            self.log_message("[系统信息] /etc/product-info 文件不存在")
            return {}
        except Exception as e:
            self.log_message(f"[系统信息] 读取产品信息失败: {str(e)}")
            return {}
    
    def get_product_key_translation(self):
        """获取产品信息键名的中文翻译"""
        return {
            'PRODUCT_NAME': '产品名称',
            'PRODUCT_VERSION': '产品版本',
            'PRODUCT_EDITION': '产品版本',
            'PRODUCT_TYPE': '产品类型',
            'MANUFACTURER': '制造商',
            'VENDOR': '厂商',
            'MODEL': '型号',
            'BOARD': '主板',
            'CPU': 'CPU',
            'MEMORY': '内存',
            'DISK': '硬盘',
            'GRAPHICS': '显卡',
            'NETWORK': '网卡',
            'AUDIO': '声卡',
            'BIOS_VERSION': 'BIOS版本',
            'BIOS_DATE': 'BIOS日期',
            'KERNEL_VERSION': '内核版本',
            'BUILD_DATE': '构建日期',
            'BUILD_TIME': '构建时间',
            'BUILD_HOST': '构建主机',
            'BUILD_USER': '构建用户',
            'COMPILER': '编译器',
            'ARCH': '架构',
            'RELEASE': '发行版',
            'CODENAME': '代号',
            'DESCRIPTION': '描述',
            'ID': '标识符',
            'ID_LIKE': '类似标识',
            'VERSION_ID': '版本ID',
            'VERSION_CODENAME': '版本代号',
            'PRETTY_NAME': '完整名称',
            'HOME_URL': '主页',
            'SUPPORT_URL': '支持页面',
            'BUG_REPORT_URL': '错误报告页面',
            'SystemName': '系统名称',
            'ProductName': '产品名称',
            'EditionName': '版本名称',
            'MajorVersion': '主版本号',
            'MinorVersion': '次版本号',
            'PatchVersion': '补丁版本号',
            'BuildVersion': '构建版本号',
            'BuildTime': '构建时间',
            'BuildHost': '构建主机',
            'OEM': '定制化',
            'Arch': '架构'
        }
    
    def update_product_info(self):
        """更新产品信息到界面"""
        try:
            # 清除旧的产品信息控件
            if hasattr(self, 'product_info_labels'):
                for label_pair in self.product_info_labels:
                    for label in label_pair:
                        label.destroy()
            
            # 获取产品信息
            product_info = self.get_product_info()
            key_translations = self.get_product_key_translation()
            
            if not product_info:
                return
            
            # 创建产品信息标签
            self.product_info_labels = []
            row = self.product_info_start_row
            
            for key, value in product_info.items():
                # 获取中文键名，如果没有翻译就使用原键名
                chinese_key = key_translations.get(key, key)
                
                # 创建键标签
                key_label = ttk.Label(self.system_info_content_frame, text=f"{chinese_key}:")
                key_label.grid(row=row, column=0, padx=(10, 5), pady=2, sticky="w")
                
                # 创建值标签
                value_label = ttk.Label(self.system_info_content_frame, text=value, foreground="orange")
                value_label.grid(row=row, column=1, padx=(0, 10), pady=2, sticky="w")
                
                self.product_info_labels.append([key_label, value_label])
                row += 1
            
            # 更新刷新按钮的rowspan以覆盖所有行
            total_rows = row - self.product_info_start_row + 4  # 包含基本信息的4行
            refresh_btn = None
            for child in self.system_info_content_frame.winfo_children():
                if isinstance(child, ttk.Button) and child['text'] == '刷新信息':
                    refresh_btn = child
                    break
            
            if refresh_btn:
                refresh_btn.grid_configure(rowspan=total_rows)
            
            self.log_message(f"[系统信息] 已加载 {len(product_info)} 项产品信息")
            
        except Exception as e:
            self.log_message(f"[系统信息] 更新产品信息失败: {str(e)}")

    def refresh_ssh_info(self):
        """刷新SSH信息"""
        def ssh_info_task():
            try:
                # 检查SSH服务状态
                ssh_status = self.get_ssh_service_status()
                self.ssh_status_var.set(ssh_status)
                self.ssh_title_var.set(f"SSH 配置 - {ssh_status}")
                
                # 获取SSH连接地址
                ssh_address = self.get_ssh_address()
                self.ssh_address_var.set(ssh_address)
                
                self.log_message("[SSH] SSH信息获取完成")
                
            except Exception as e:
                self.log_message(f"[SSH] 获取SSH信息时出错: {str(e)}")
        
        threading.Thread(target=ssh_info_task, daemon=True).start()
    
    def get_ssh_service_status(self):
        """获取SSH服务状态"""
        try:
            # 检查SSH服务是否运行
            result = subprocess.run(["systemctl", "is-active", "ssh"], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip() == "active":
                return "运行中"
            
            # 检查openssh-server是否安装
            result = subprocess.run(["dpkg", "-l", "openssh-server"], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "已安装，未启动"
            else:
                return "未安装"
                
        except subprocess.TimeoutExpired:
            return "检测超时"
        except Exception as e:
            return f"检测失败: {str(e)}"
    
    def get_ssh_address(self):
        """获取SSH连接地址"""
        try:
            # 获取当前用户名
            username = os.getenv('USER') or os.getenv('USERNAME') or 'user'
            
            # 获取本机IP地址
            ip_address = self.get_local_ip()
            
            if ip_address and ip_address != "获取失败":
                return f"{username}@{ip_address}"
            else:
                return f"{username}@localhost"
                
        except Exception as e:
            return f"获取失败: {str(e)}"
    
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            # 尝试通过连接外部地址获取本机IP
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                # 备选方法：通过hostname获取
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                if ip.startswith("127."):
                    # 如果是localhost，尝试其他方法
                    result = subprocess.run(["hostname", "-I"], 
                                           capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        ips = result.stdout.strip().split()
                        if ips:
                            return ips[0]
                return ip
            except Exception:
                return "获取失败"
    
    def install_ssh_server(self):
        """安装SSH服务器"""
        def install_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在安装SSH服务器..."))
                self.message_queue.put(("log", "[SSH] [开始] 开始安装openssh-server"))
                
                # 更新软件包列表
                self.message_queue.put(("log", "[SSH] [步骤1] 正在更新软件包列表..."))
                update_process = subprocess.Popen(
                    ["pkexec", "apt", "update"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                while True:
                    output = update_process.stdout.readline()
                    if output == '' and update_process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line and not line.startswith('WARNING:'):
                            self.message_queue.put(("log", f"[SSH] [apt update] {line}"))
                
                update_returncode = update_process.wait(timeout=60)
                if update_returncode != 0:
                    stderr_output = update_process.stderr.read()
                    if "cancelled" in stderr_output.lower():
                        self.message_queue.put(("log", "[SSH] [取消] 用户取消了权限授权"))
                        return
                    else:
                        self.message_queue.put(("log", f"[SSH] [警告] 更新软件包列表失败: {stderr_output.strip()}"))
                
                # 安装openssh-server
                self.message_queue.put(("log", "[SSH] [步骤2] 正在安装openssh-server..."))
                install_process = subprocess.Popen(
                    ["pkexec", "apt", "install", "-y", "openssh-server"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                while True:
                    output = install_process.stdout.readline()
                    if output == '' and install_process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line:
                            if "Setting up" in line:
                                self.message_queue.put(("log", f"[SSH] [安装] {line}"))
                            elif "Reading" in line or "Building" in line:
                                self.message_queue.put(("log", f"[SSH] [准备] {line}"))
                            elif not line.startswith('WARNING:'):
                                self.message_queue.put(("log", f"[SSH] [安装] {line}"))
                
                install_returncode = install_process.wait(timeout=120)
                if install_returncode == 0:
                    self.message_queue.put(("log", "[SSH] [成功] openssh-server安装完成"))
                    # 刷新SSH信息
                    self.refresh_ssh_info()
                else:
                    stderr_output = install_process.stderr.read()
                    if "cancelled" in stderr_output.lower():
                        self.message_queue.put(("log", "[SSH] [取消] 用户取消了安装"))
                    else:
                        self.message_queue.put(("log", f"[SSH] [失败] 安装失败: {stderr_output.strip()}"))
                
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[SSH] [超时] 安装过程超时"))
            except Exception as e:
                self.message_queue.put(("log", f"[SSH] [错误] 安装过程出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "SSH安装操作完成"))
        
        threading.Thread(target=install_task, daemon=True).start()
    
    def start_ssh_service(self):
        """启动SSH服务"""
        def start_task():
            try:
                self.message_queue.put(("status", "正在启动SSH服务..."))
                self.message_queue.put(("log", "[SSH] [开始] 开始启动SSH服务"))
                
                # 启动SSH服务
                result = subprocess.run(
                    ["pkexec", "systemctl", "start", "ssh"], 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                if result.returncode == 0:
                    self.message_queue.put(("log", "[SSH] [成功] SSH服务启动成功"))
                    
                    # 设置开机自启
                    enable_result = subprocess.run(
                        ["pkexec", "systemctl", "enable", "ssh"], 
                        capture_output=True, 
                        text=True, 
                        timeout=30
                    )
                    
                    if enable_result.returncode == 0:
                        self.message_queue.put(("log", "[SSH] [成功] SSH服务已设置为开机自启"))
                    else:
                        self.message_queue.put(("log", f"[SSH] [警告] 设置开机自启失败: {enable_result.stderr.strip()}"))
                    
                    # 刷新SSH信息
                    self.refresh_ssh_info()
                else:
                    if "cancelled" in result.stderr.lower():
                        self.message_queue.put(("log", "[SSH] [取消] 用户取消了权限授权"))
                    else:
                        self.message_queue.put(("log", f"[SSH] [失败] SSH服务启动失败: {result.stderr.strip()}"))
                
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[SSH] [超时] 启动SSH服务超时"))
            except Exception as e:
                self.message_queue.put(("log", f"[SSH] [错误] 启动SSH服务时出错: {str(e)}"))
            finally:
                self.message_queue.put(("status", "SSH服务操作完成"))
        
        threading.Thread(target=start_task, daemon=True).start()
    
    def check_ssh_status(self):
        """检查SSH状态"""
        self.refresh_ssh_info()
        self.log_message("[SSH] 已刷新SSH状态信息")
    
    def copy_ssh_address(self):
        """复制SSH地址到剪贴板"""
        try:
            ssh_address = self.ssh_address_var.get()
            if ssh_address and ssh_address != "获取中..." and ssh_address != "获取失败":
                # 复制到剪贴板
                self.root.clipboard_clear()
                self.root.clipboard_append(ssh_address)
                self.root.update()  # 确保剪贴板更新
                self.log_message(f"[SSH] 已复制SSH地址到剪贴板: {ssh_address}")
            else:
                self.log_message("[SSH] SSH地址无效，无法复制")
        except Exception as e:
            self.log_message(f"[SSH] 复制失败: {str(e)}")

    # SSHFS相关方法
    def toggle_sshfs_section(self):
        """切换SSHFS配置区域的展开/折叠状态"""
        if self.sshfs_collapsed.get():
            # 展开
            self.sshfs_content_frame.grid(row=1, column=0, sticky="ew")
            self.sshfs_toggle_btn.config(text="▼")
            self.sshfs_collapsed.set(False)
        else:
            # 折叠
            self.sshfs_content_frame.grid_remove()
            self.sshfs_toggle_btn.config(text="▶")
            self.sshfs_collapsed.set(True)

    def init_sshfs_config(self):
        """初始化SSHFS配置"""
        try:
            # 只在没有保存的配置时才设置默认值
            if not self.sshfs_host_var.get().strip():
                host = self.get_local_ip()
                self.sshfs_host_var.set(host)
            
            if not self.sshfs_local_path_var.get().strip():
                default_local_path = os.path.join(self.save_path.get(), "mount", "remote")
                self.sshfs_local_path_var.set(default_local_path)
            
            # 绑定变量变化事件，自动更新SSHFS命令
            self.sshfs_host_var.trace_add("write", self.update_sshfs_command)
            self.sshfs_username_var.trace_add("write", self.update_sshfs_command)
            self.sshfs_remote_path_var.trace_add("write", self.update_sshfs_command)
            self.sshfs_local_path_var.trace_add("write", self.update_sshfs_command)
            
            # 手动触发一次命令更新
            self.update_sshfs_command()
            
            # 检查SSHFS状态
            self.check_sshfs_status()
            
        except Exception as e:
            self.log_message(f"[SSHFS] 初始化配置失败: {str(e)}")

    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            import socket
            # 创建一个UDP套接字连接到外部地址来获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def update_sshfs_command(self, *args):
        """更新SSHFS命令"""
        try:
            host = self.sshfs_host_var.get().strip()
            username = self.sshfs_username_var.get().strip()
            remote_path = self.sshfs_remote_path_var.get().strip()
            local_path = self.sshfs_local_path_var.get().strip()
            
            if host and remote_path and local_path:
                if username:
                    command = f"sshfs {username}@{host}:{remote_path} {local_path}"
                else:
                    command = f"sshfs {host}:{remote_path} {local_path}"
                self.sshfs_command_var.set(command)
            else:
                self.sshfs_command_var.set("")
        except Exception as e:
            self.log_message(f"[SSHFS] 更新命令失败: {str(e)}")

    def install_sshfs(self):
        """安装SSHFS"""
        def install_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在安装SSHFS..."))
                self.message_queue.put(("log", "[SSHFS] [开始] 安装SSHFS"))
                
                # 步骤1: 更新软件源
                self.message_queue.put(("log", "[SSHFS] [步骤1] 正在更新软件源..."))
                update_cmd = ["pkexec", "apt", "update"]
                
                # 使用Popen实时输出更新过程
                update_process = subprocess.Popen(
                    update_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                # 实时读取输出
                while True:
                    output = update_process.stdout.readline()
                    if output == '' and update_process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line and not line.startswith('WARNING:'):
                            self.message_queue.put(("log", f"[SSHFS] [apt update] {line}"))
                
                # 读取错误输出
                stderr_output = update_process.stderr.read()
                update_returncode = update_process.wait(timeout=60)
                
                if update_returncode != 0:
                    if "cancelled" in stderr_output.lower():
                        self.message_queue.put(("log", "[SSHFS] [取消] 用户取消了更新权限授权"))
                        return
                    else:
                        self.message_queue.put(("log", f"[SSHFS] [失败] 软件源更新失败: {stderr_output.strip()}"))
                        return
                
                # 步骤2: 安装SSHFS
                self.message_queue.put(("log", "[SSHFS] [步骤2] 正在安装SSHFS..."))
                install_cmd = ["pkexec", "apt", "install", "-y", "sshfs"]
                
                # 使用Popen实时输出安装过程
                install_process = subprocess.Popen(
                    install_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                # 实时读取输出
                while True:
                    output = install_process.stdout.readline()
                    if output == '' and install_process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line and not line.startswith('WARNING:'):
                            self.message_queue.put(("log", f"[SSHFS] [apt install] {line}"))
                
                # 读取错误输出
                stderr_output = install_process.stderr.read()
                install_returncode = install_process.wait(timeout=120)
                
                if install_returncode == 0:
                    self.message_queue.put(("log", "[SSHFS] [成功] SSHFS安装完成"))
                    self.message_queue.put(("sshfs_status", "已安装"))
                    self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已安装"))
                else:
                    if "cancelled" in stderr_output.lower():
                        self.message_queue.put(("log", "[SSHFS] [取消] 用户取消了安装权限授权"))
                    else:
                        self.message_queue.put(("log", f"[SSHFS] [失败] SSHFS安装失败: {stderr_output.strip()}"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [错误] 安装SSHFS时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "SSHFS安装完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认安装SSHFS",
            "此操作将安装SSHFS工具。\n\n"
            "是否继续？",
            icon="info"
        )
        
        if response:
            threading.Thread(target=install_task, daemon=True).start()

    def check_sshfs_status(self):
        """检查SSHFS状态"""
        def check_task():
            try:
                self.message_queue.put(("sshfs_status", "检测中..."))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 检测中..."))
                
                # 检查sshfs命令是否存在
                result = subprocess.run(["which", "sshfs"], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.message_queue.put(("sshfs_status", "已安装"))
                    self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已安装"))
                    self.message_queue.put(("log", "[SSHFS] [信息] SSHFS已安装"))
                else:
                    self.message_queue.put(("sshfs_status", "未安装"))
                    self.message_queue.put(("sshfs_title", "SSHFS 配置 - 未安装"))
                    self.message_queue.put(("log", "[SSHFS] [信息] SSHFS未安装"))
                
            except Exception as e:
                self.message_queue.put(("sshfs_status", "检测失败"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 检测失败"))
                self.message_queue.put(("log", f"[SSHFS] [错误] 检测SSHFS状态时出错: {str(e)}"))
        
        threading.Thread(target=check_task, daemon=True).start()

    def open_sshfs_folder(self):
        """打开SSHFS挂载文件夹"""
        try:
            local_path = self.sshfs_local_path_var.get().strip()
            if not local_path:
                messagebox.showwarning("警告", "请先设置本地路径")
                return
            
            if not os.path.exists(local_path):
                messagebox.showwarning("警告", f"路径不存在: {local_path}")
                return
            
            # 使用系统默认文件管理器打开文件夹
            subprocess.run(["xdg-open", local_path], check=True)
            self.log_message(f"[SSHFS] 已打开文件夹: {local_path}")
            
        except Exception as e:
            self.log_message(f"[SSHFS] 打开文件夹失败: {str(e)}")

    def mount_sshfs(self):
        """挂载SSHFS"""
        def mount_task():
            try:
                host = self.sshfs_host_var.get().strip()
                username = self.sshfs_username_var.get().strip()
                remote_path = self.sshfs_remote_path_var.get().strip()
                local_path = self.sshfs_local_path_var.get().strip()
                
                if not host or not remote_path or not local_path:
                    self.message_queue.put(("log", "[SSHFS] [错误] 请填写完整的主机地址、远程路径和本地路径"))
                    return
                
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在挂载SSHFS..."))
                self.message_queue.put(("log", f"[SSHFS] [开始] 挂载 {host}:{remote_path} 到 {local_path}"))
                
                # 创建本地目录
                if not os.path.exists(local_path):
                    os.makedirs(local_path, exist_ok=True)
                    self.message_queue.put(("log", f"[SSHFS] [信息] 已创建本地目录: {local_path}"))
                
                # 检查是否已经挂载
                if os.path.ismount(local_path):
                    self.message_queue.put(("log", "[SSHFS] [警告] 该路径已经挂载，请先取消挂载"))
                    return
                
                # 执行挂载命令 - 使用交互式终端方法
                if username:
                    mount_cmd = ["sshfs", f"{username}@{host}:{remote_path}", local_path]
                else:
                    mount_cmd = ["sshfs", f"{host}:{remote_path}", local_path]
                self.message_queue.put(("log", f"[SSHFS] [执行] 命令: {' '.join(mount_cmd)}"))
                
                # 使用交互式终端方法
                self.execute_interactive_sshfs(mount_cmd)
                
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [错误] 挂载SSHFS时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "SSHFS挂载完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认挂载SSHFS",
            "此操作将挂载远程目录到本地。\n\n"
            "是否继续？",
            icon="info"
        )
        
        if response:
            threading.Thread(target=mount_task, daemon=True).start()

    def fallback_mount_sshfs(self, mount_cmd):
        """回退挂载方法 - 使用缓存的密码执行sshfs命令"""
        try:
            self.message_queue.put(("log", "[SSHFS] [回退] 尝试使用缓存密码直接执行挂载命令"))
            
            # 检查是否有缓存的密码
            if not hasattr(self, 'sshfs_password_cache') or self.sshfs_password_cache is None:
                self.message_queue.put(("log", "[SSHFS] [错误] 回退挂载失败：没有可用的密码"))
                return
            
            password = self.sshfs_password_cache
            
            # 使用expect脚本作为回退方案
            self.message_queue.put(("log", "[SSHFS] [回退] 使用expect脚本作为回退方案..."))
            self.execute_with_expect(mount_cmd, password)
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 回退挂载失败: {str(e)}"))

    def show_password_dialog(self, host, username):
        """显示密码输入对话框（完全非阻塞版本）"""
        try:
            # 创建密码输入对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("SSH密码输入")
            dialog.geometry("400x200")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (200 // 2)
            dialog.geometry(f"400x200+{x}+{y}")
            
            # 连接信息
            info_text = f"连接到: {username}@{host}" if username else f"连接到: {host}"
            ttk.Label(dialog, text=info_text, font=("", 10, "bold")).pack(pady=(20, 10))
            
            # 密码输入框
            ttk.Label(dialog, text="请输入SSH密码:").pack(pady=(10, 5))
            password_var = tk.StringVar()
            password_entry = ttk.Entry(dialog, textvariable=password_var, show="*", width=30)
            password_entry.pack(pady=(0, 20))
            password_entry.focus()
            
            # 按钮框架
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=(0, 20))
            
            # 使用回调机制，不阻塞
            def on_ok():
                """确定按钮回调"""
                password = password_var.get().strip()
                if not password:
                    messagebox.showwarning("警告", "密码不能为空", parent=dialog)
                    return
                
                # 将密码存储到缓存变量
                self.sshfs_password_cache = password
                self.message_queue.put(("log", "[SSHFS] [信息] 密码已获取，开始执行挂载..."))
                
                # 关闭对话框
                dialog.destroy()
                
                # 异步执行挂载（避免阻塞）
                self.root.after(100, self.execute_cached_mount)
            
            def on_cancel():
                """取消按钮回调"""
                self.message_queue.put(("log", "[SSHFS] [取消] 用户取消了密码输入"))
                dialog.destroy()
            
            # 确定和取消按钮
            ttk.Button(button_frame, text="确定", command=on_ok).pack(side="left", padx=(0, 10))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side="left")
            
            # 绑定回车键和ESC键
            password_entry.bind('<Return>', lambda e: on_ok())
            dialog.bind('<Escape>', lambda e: on_cancel())
            
            # 设置对话框为模态
            dialog.focus_force()
            dialog.grab_set()
            
            # 不等待，直接返回对话框对象
            return dialog
            
        except Exception as e:
            self.log_message(f"[SSHFS] 密码对话框创建失败: {str(e)}")
            return None



    def execute_sshfs_with_password(self, mount_cmd, password):
        """使用密码执行SSHFS挂载"""
        try:
            self.message_queue.put(("log", "[SSHFS] [信息] 正在使用密码执行挂载..."))
            
            # 使用sshpass来传递密码（如果可用）
            if self.check_sshpass_available():
                self.execute_with_sshpass(mount_cmd, password)
            else:
                # 回退到使用expect脚本
                self.execute_with_expect(mount_cmd, password)
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 密码挂载失败: {str(e)}"))
            # 回退到原来的方法
            self.fallback_mount_sshfs(mount_cmd)
    
    def execute_sshfs_with_cached_password(self, mount_cmd):
        """使用缓存的密码执行SSHFS挂载"""
        try:
            if not hasattr(self, 'sshfs_password_cache') or self.sshfs_password_cache is None:
                self.message_queue.put(("log", "[SSHFS] [错误] 密码缓存为空，无法执行挂载"))
                return
            
            password = self.sshfs_password_cache
            self.message_queue.put(("log", "[SSHFS] [信息] 使用缓存的密码执行挂载..."))
            
            # 首先尝试使用sshpass
            if self.check_sshpass_available():
                self.execute_with_sshpass(mount_cmd, password)
            else:
                # 如果没有sshpass，使用expect脚本
                self.execute_with_expect(mount_cmd, password)
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 使用缓存密码执行SSHFS挂载失败: {str(e)}"))
            # 最后尝试回退方法
            self.fallback_mount_sshfs(mount_cmd)
        finally:
            # 清除密码缓存（安全考虑）
            self.sshfs_password_cache = None
    
    def execute_interactive_sshfs(self, mount_cmd):
        """执行交互式SSHFS挂载（在终端中）"""
        try:
            self.message_queue.put(("log", "[SSHFS] [信息] 启动交互式SSHFS挂载..."))
            
            # 检查用户是否设置了中文显示
            use_chinese = getattr(self, 'sshfs_use_chinese', False)
            
            # 检查可用的终端模拟器
            terminal_emulators = [
                "gnome-terminal",
                "konsole", 
                "xfce4-terminal",
                "lxterminal",
                "mate-terminal",
                "terminator",
                "xterm"
            ]
            
            terminal_cmd = None
            for terminal in terminal_emulators:
                try:
                    result = subprocess.run(["which", terminal], capture_output=True, text=True)
                    if result.returncode == 0:
                        terminal_cmd = terminal
                        break
                except:
                    continue
            
            if not terminal_cmd:
                self.message_queue.put(("log", "[SSHFS] [错误] 未找到可用的终端模拟器"))
                return False
            
            self.message_queue.put(("log", f"[SSHFS] [信息] 使用终端: {terminal_cmd}"))
            
            # 构建在终端中执行的命令
            sshfs_cmd_str = ' '.join(mount_cmd)
            
            # 根据语言设置创建脚本
            if use_chinese:
                # 中文版本
                terminal_script = f"""
echo "=== SSHFS 挂载进程 ==="
echo "命令: {sshfs_cmd_str}"
echo ""
echo "请输入SSH密码:"

# 执行sshfs命令，让用户输入密码
{sshfs_cmd_str} &
sshfs_pid=$!

echo ""
echo "SSHFS进程已启动 (PID: $sshfs_pid)"
echo "等待挂载完成..."

# 等待挂载完成
sleep 4

# 检查挂载状态
if mountpoint -q "{mount_cmd[-1]}"; then
    echo "成功: 挂载完成!"
    echo "挂载点: {mount_cmd[-1]}"
    echo "进程ID: $sshfs_pid"
    echo ""
    echo "正在处理进程分离..."
    
    # 使用disown让进程不依赖终端
    disown $sshfs_pid 2>/dev/null || echo "注意: disown命令不可用，但挂载可能仍然有效"
    
    echo "进程分离完成!"
    echo "现在可以安全关闭此终端窗口。"
    echo "挂载将保持有效。"
    
else
    echo "失败: 挂载验证失败，请检查:"
    echo "  1. 网络连接"
    echo "  2. SSH用户名和密码"
    echo "  3. 远程服务器可访问性"
    echo "  4. 本地挂载目录权限"
    echo ""
    echo "进程状态:"
    if kill -0 $sshfs_pid 2>/dev/null; then
        echo "  SSHFS进程仍在运行，可能需要更多时间"
        echo "  请稍后在主程序中检查挂载状态"
    else
        echo "  SSHFS进程已退出，挂载失败"
    fi
fi

echo ""
echo "按回车键关闭此窗口..."
read
"""
            else:
                # 英文版本
                terminal_script = f"""
echo "=== SSHFS Mount Process ==="
echo "Command: {sshfs_cmd_str}"
echo ""
echo "Please enter SSH password:"

# Execute sshfs command with user password input
{sshfs_cmd_str} &
sshfs_pid=$!

echo ""
echo "SSHFS process started (PID: $sshfs_pid)"
echo "Waiting for mount to complete..."

# Wait for mount to complete
sleep 4

# Check mount status
if mountpoint -q "{mount_cmd[-1]}"; then
    echo "SUCCESS: Mount completed successfully!"
    echo "Mount point: {mount_cmd[-1]}"
    echo "Process ID: $sshfs_pid"
    echo ""
    echo "Processing detachment..."
    
    # Use disown to detach process from terminal
    disown $sshfs_pid 2>/dev/null || echo "Note: disown command not available, but mount may still persist"
    
    echo "Process detachment completed!"
    echo "You can now safely close this terminal window."
    echo "The mount will remain active."
    
else
    echo "FAILED: Mount verification failed. Please check:"
    echo "  1. Network connection"
    echo "  2. SSH username and password"
    echo "  3. Remote server accessibility"
    echo "  4. Local mount directory permissions"
    echo ""
    echo "Process status:"
    if kill -0 $sshfs_pid 2>/dev/null; then
        echo "  SSHFS process is still running, may need more time"
        echo "  Please check mount status later in the main program"
    else
        echo "  SSHFS process has exited, mount failed"
    fi
fi

echo ""
echo "Press Enter to close this window..."
read
"""
            
            # 根据不同的终端模拟器使用不同的参数
            # 设置UTF-8环境变量以支持中文显示
            env_vars = "export LANG=zh_CN.UTF-8; export LC_ALL=zh_CN.UTF-8; "
            full_script = env_vars + terminal_script
            
            if terminal_cmd == "gnome-terminal":
                cmd = [terminal_cmd, "--", "bash", "-c", full_script]
            elif terminal_cmd == "konsole":
                cmd = [terminal_cmd, "-e", "bash", "-c", full_script]
            elif terminal_cmd in ["xfce4-terminal", "mate-terminal"]:
                cmd = [terminal_cmd, "-e", f"bash -c '{full_script}'"]
            elif terminal_cmd == "terminator":
                cmd = [terminal_cmd, "-e", f"bash -c '{full_script}'"]
            else:  # xterm等
                cmd = [terminal_cmd, "-e", "bash", "-c", full_script]
            
            self.message_queue.put(("log", f"[SSHFS] [信息] 启动终端命令: {' '.join(cmd)}"))
            
            # 在新终端中执行
            process = subprocess.Popen(cmd)
            
            self.message_queue.put(("log", "[SSHFS] [信息] 终端已启动，请在终端中输入密码"))
            self.message_queue.put(("log", "[SSHFS] [信息] 等待用户在终端中完成操作..."))
            
            # 等待终端进程完成（用户输入密码并完成操作）
            process.wait()
            
            # 检查挂载状态
            self.root.after(2000, lambda: self.verify_mount_status(mount_cmd))
            
            return True
            
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 交互式挂载失败: {str(e)}"))
            return False

    def execute_cached_mount(self):
        """执行缓存的挂载命令"""
        try:
            if not hasattr(self, 'sshfs_mount_cmd_cache') or self.sshfs_mount_cmd_cache is None:
                self.message_queue.put(("log", "[SSHFS] [错误] 挂载命令缓存为空"))
                return
            
            if not hasattr(self, 'sshfs_password_cache') or self.sshfs_password_cache is None:
                self.message_queue.put(("log", "[SSHFS] [错误] 密码缓存为空"))
                return
            
            mount_cmd = self.sshfs_mount_cmd_cache
            password = self.sshfs_password_cache
            
            self.message_queue.put(("log", "[SSHFS] [信息] 开始执行缓存的挂载命令..."))
            
            # 使用缓存的密码执行挂载
            self.execute_sshfs_with_password(mount_cmd, password)
            
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 执行缓存挂载失败: {str(e)}"))
        finally:
            # 清除缓存
            self.sshfs_mount_cmd_cache = None
            self.sshfs_password_cache = None

    def check_sshpass_available(self):
        """检查sshpass是否可用"""
        try:
            result = subprocess.run(["which", "sshpass"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    def execute_with_sshpass(self, mount_cmd, password):
        """使用sshpass执行挂载"""
        try:
            # 构建sshpass命令
            sshpass_cmd = ["sshpass", "-p", password] + mount_cmd
            
            self.message_queue.put(("log", "[SSHFS] [信息] 使用sshpass执行挂载..."))
            
            # 执行命令
            result = subprocess.run(sshpass_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.message_queue.put(("log", "[SSHFS] [成功] SSHFS挂载成功"))
                self.message_queue.put(("sshfs_status", "已挂载"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已挂载"))
                
                # 启动状态检查
                self.sshfs_status_checking = True
                self.root.after(3000, self.check_mount_status)
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.message_queue.put(("log", f"[SSHFS] [失败] SSHFS挂载失败: {error_msg}"))
                
                # 如果sshpass失败，尝试使用expect
                self.message_queue.put(("log", "[SSHFS] [回退] sshpass失败，尝试使用expect..."))
                self.execute_with_expect(mount_cmd, password)
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] sshpass执行失败: {str(e)}"))
            # 回退到expect方法
            self.execute_with_expect(mount_cmd, password)

    def execute_with_expect(self, mount_cmd, password):
        """使用expect脚本执行挂载"""
        try:
            self.message_queue.put(("log", "[SSHFS] [信息] 使用expect脚本执行挂载..."))
            
            # 创建expect脚本
            expect_script = self.create_expect_script(mount_cmd, password)
            if not expect_script:
                self.message_queue.put(("log", "[SSHFS] [错误] 无法创建expect脚本"))
                return
            
            self.message_queue.put(("log", f"[SSHFS] [调试] expect脚本路径: {expect_script}"))
            
            # 检查expect命令是否可用
            try:
                expect_check = subprocess.run(["which", "expect"], capture_output=True, text=True, timeout=5)
                if expect_check.returncode != 0:
                    self.message_queue.put(("log", "[SSHFS] [错误] expect命令不可用，请安装expect包"))
                    return
                self.message_queue.put(("log", f"[SSHFS] [调试] expect命令路径: {expect_check.stdout.strip()}"))
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [错误] 检查expect命令失败: {str(e)}"))
                return
            
            # 执行expect脚本
            self.message_queue.put(("log", f"[SSHFS] [调试] 执行命令: expect {expect_script}"))
            result = subprocess.run(["expect", expect_script], capture_output=True, text=True, timeout=60)
            
            # 详细记录输出
            self.message_queue.put(("log", f"[SSHFS] [调试] expect返回码: {result.returncode}"))
            if result.stdout:
                self.message_queue.put(("log", f"[SSHFS] [调试] expect输出: {result.stdout.strip()}"))
            if result.stderr:
                self.message_queue.put(("log", f"[SSHFS] [调试] expect错误: {result.stderr.strip()}"))
            
            if result.returncode == 0:
                self.message_queue.put(("log", "[SSHFS] [成功] expect脚本执行成功"))
                
                # 验证挂载是否真的成功
                self.message_queue.put(("log", "[SSHFS] [信息] 验证挂载状态..."))
                self.verify_mount_status(mount_cmd)
                
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.message_queue.put(("log", f"[SSHFS] [失败] expect挂载失败: {error_msg}"))
                
                # expect失败，不再回退，避免无限循环
                self.message_queue.put(("log", "[SSHFS] [失败] expect挂载失败，请检查网络和SSH配置"))
                self.message_queue.put(("sshfs_status", "挂载失败"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 挂载失败"))
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] expect执行失败: {str(e)}"))
            # expect执行异常，不再回退
            self.message_queue.put(("sshfs_status", "挂载失败"))
            self.message_queue.put(("sshfs_title", "SSHFS 配置 - 挂载失败"))

    def create_expect_script(self, mount_cmd, password):
        """创建expect脚本"""
        try:
            # 创建临时expect脚本，使用原始字符串避免转义问题
            script_content = f"""#!/usr/bin/expect -f
set timeout 120
log_user 1
puts "Starting SSHFS mount..."

spawn {' '.join(mount_cmd)}
puts "Spawned command: {' '.join(mount_cmd)}"

expect {{
    "password:" {{
        puts "Got password prompt, sending password..."
        send "{password}\\r"
        exp_continue
    }}
    "Password:" {{
        puts "Got Password prompt, sending password..."
        send "{password}\\r"
        exp_continue
    }}
    "yes/no" {{
        puts "Got yes/no prompt, sending yes..."
        send "yes\\r"
        exp_continue
    }}
    "Are you sure you want to continue connecting" {{
        puts "Got connection prompt, sending yes..."
        send "yes\\r"
        exp_continue
    }}
    "Connection refused" {{
        puts "Connection refused by server"
        exit 1
    }}
    "Permission denied" {{
        puts "Permission denied - wrong password or user"
        exit 1
    }}
    timeout {{
        puts "Timeout waiting for completion"
        exit 1
    }}
    eof {{
        puts "Command completed"
    }}
}}

# Wait for the spawned process to finish and get exit code
catch {{wait}} result
if {{[llength $result] >= 4}} {{
    set exit_code [lindex $result 3]
    puts "Process exit code: $exit_code"
    exit $exit_code
}} else {{
    puts "Process completed successfully"
    exit 0
}}
"""
            
            # 写入临时文件
            import tempfile
            script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False)
            script_file.write(script_content)
            script_file.close()
            
            # 设置执行权限
            os.chmod(script_file.name, 0o755)
            
            return script_file.name
            
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 创建expect脚本失败: {str(e)}"))
            return None

    def verify_mount_status(self, mount_cmd):
        """验证挂载状态"""
        try:
            self.message_queue.put(("log", "[SSHFS] [信息] 验证挂载状态..."))
            
            # 等待一下让挂载完成
            import time
            time.sleep(3)
            
            # 检查挂载状态
            local_path = self.sshfs_local_path_var.get().strip()
            if not local_path:
                self.message_queue.put(("log", "[SSHFS] [错误] 本地路径为空"))
                return
            
            self.message_queue.put(("log", f"[SSHFS] [调试] 检查本地路径: {local_path}"))
            
            # 检查路径是否存在
            if not os.path.exists(local_path):
                self.message_queue.put(("log", f"[SSHFS] [调试] 本地路径不存在: {local_path}"))
            else:
                self.message_queue.put(("log", f"[SSHFS] [调试] 本地路径存在: {local_path}"))
            
            # 使用多种方法检查挂载状态
            is_mounted = False
            
            # 方法1: 检查是否为挂载点
            try:
                if os.path.ismount(local_path):
                    is_mounted = True
                    self.message_queue.put(("log", "[SSHFS] [成功] 方法1检测到挂载成功"))
                else:
                    self.message_queue.put(("log", f"[SSHFS] [调试] 方法1: {local_path} 不是挂载点"))
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [调试] 方法1检查失败: {str(e)}"))
            
            # 方法2: 检查mount命令输出
            if not is_mounted:
                try:
                    mount_result = subprocess.run(["mount"], capture_output=True, text=True, timeout=10)
                    if mount_result.returncode == 0:
                        mount_output = mount_result.stdout
                        self.message_queue.put(("log", f"[SSHFS] [调试] mount命令输出: {mount_output}"))
                        if local_path in mount_output and "sshfs" in mount_output:
                            is_mounted = True
                            self.message_queue.put(("log", "[SSHFS] [成功] 方法2检测到挂载成功"))
                        else:
                            self.message_queue.put(("log", f"[SSHFS] [调试] 方法2: mount输出中未找到 {local_path} 或 sshfs"))
                    else:
                        self.message_queue.put(("log", f"[SSHFS] [调试] mount命令失败: {mount_result.stderr}"))
                except Exception as e:
                    self.message_queue.put(("log", f"[SSHFS] [调试] mount命令检查失败: {str(e)}"))
            
            # 方法3: 检查/proc/mounts
            if not is_mounted:
                try:
                    with open("/proc/mounts", "r") as f:
                        mounts_content = f.read()
                        self.message_queue.put(("log", f"[SSHFS] [调试] /proc/mounts内容: {mounts_content}"))
                        if local_path in mounts_content and "sshfs" in mounts_content:
                            is_mounted = True
                            self.message_queue.put(("log", "[SSHFS] [成功] 方法3检测到挂载成功"))
                        else:
                            self.message_queue.put(("log", f"[SSHFS] [调试] 方法3: /proc/mounts中未找到 {local_path} 或 sshfs"))
                except Exception as e:
                    self.message_queue.put(("log", f"[SSHFS] [调试] /proc/mounts检查失败: {str(e)}"))
            
            if is_mounted:
                self.message_queue.put(("log", "[SSHFS] [成功] SSHFS挂载验证成功"))
                self.message_queue.put(("sshfs_status", "已挂载"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已挂载"))
                
                # 启动状态检查
                self.sshfs_status_checking = True
                self.root.after(3000, self.check_mount_status)
            else:
                self.message_queue.put(("log", "[SSHFS] [失败] 挂载验证失败，expect脚本可能没有真正挂载成功"))
                self.message_queue.put(("sshfs_status", "挂载失败"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 挂载失败"))
                
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 验证挂载状态失败: {str(e)}"))
            self.message_queue.put(("sshfs_status", "挂载失败"))
            self.message_queue.put(("sshfs_title", "SSHFS 配置 - 挂载失败"))

    def check_mount_status(self):
        """检查挂载状态"""
        try:
            # 如果状态检查被停止，则不继续检查
            if not self.sshfs_status_checking:
                return
                
            local_path = self.sshfs_local_path_var.get().strip()
            
            # 使用多种方法检查挂载状态
            is_mounted = False
            
            # 方法1: 检查是否为挂载点
            if local_path and os.path.ismount(local_path):
                is_mounted = True
            
            # 方法2: 检查mount命令输出
            if not is_mounted and local_path:
                try:
                    mount_result = subprocess.run(["mount"], capture_output=True, text=True, timeout=10)
                    if mount_result.returncode == 0:
                        mount_output = mount_result.stdout
                        if local_path in mount_output and "sshfs" in mount_output:
                            is_mounted = True
                except:
                    pass
            
            # 方法3: 检查/proc/mounts
            if not is_mounted and local_path:
                try:
                    with open("/proc/mounts", "r") as f:
                        mounts_content = f.read()
                        if local_path in mounts_content and "sshfs" in mounts_content:
                            is_mounted = True
                except:
                    pass
            
            if is_mounted:
                self.message_queue.put(("log", "[SSHFS] [成功] 检测到挂载成功"))
                self.message_queue.put(("sshfs_status", "已挂载"))
                self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已挂载"))
                # 挂载成功后停止检查
                self.sshfs_status_checking = False
            else:
                self.message_queue.put(("log", "[SSHFS] [信息] 挂载状态检查中..."))
                # 5秒后再次检查
                self.root.after(5000, self.check_mount_status)
        except Exception as e:
            self.message_queue.put(("log", f"[SSHFS] [错误] 检查挂载状态失败: {str(e)}"))
            # 出错时也停止检查
            self.sshfs_status_checking = False

    def umount_sshfs(self):
        """取消挂载SSHFS"""
        def umount_task():
            try:
                local_path = self.sshfs_local_path_var.get().strip()
                
                if not local_path:
                    self.message_queue.put(("log", "[SSHFS] [错误] 请先设置本地路径"))
                    return
                
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在取消挂载SSHFS..."))
                self.message_queue.put(("log", f"[SSHFS] [开始] 取消挂载: {local_path}"))
                
                # 执行取消挂载命令
                umount_cmd = ["fusermount", "-u", local_path]
                result = subprocess.run(umount_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.message_queue.put(("log", "[SSHFS] [成功] SSHFS取消挂载成功"))
                    self.message_queue.put(("sshfs_status", "已安装"))
                    self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已安装"))
                    # 停止状态检查
                    self.sshfs_status_checking = False
                else:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    self.message_queue.put(("log", f"[SSHFS] [失败] SSHFS取消挂载失败: {error_msg}"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [错误] 取消挂载SSHFS时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "SSHFS取消挂载完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认取消挂载SSHFS",
            "此操作将取消挂载远程目录。\n\n"
            "是否继续？",
            icon="warning"
        )
        
        if response:
            threading.Thread(target=umount_task, daemon=True).start()

    def force_kill_sshfs(self):
        """强制终止SSHFS进程"""
        def kill_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在强制终止SSHFS进程..."))
                self.message_queue.put(("log", "[SSHFS] [开始] 强制终止SSHFS进程"))
                
                # 查找并终止sshfs进程
                kill_cmd = ["pkill", "-f", "sshfs"]
                result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.message_queue.put(("log", "[SSHFS] [成功] SSHFS进程已终止"))
                    self.message_queue.put(("sshfs_status", "已安装"))
                    self.message_queue.put(("sshfs_title", "SSHFS 配置 - 已安装"))
                    # 停止状态检查
                    self.sshfs_status_checking = False
                else:
                    self.message_queue.put(("log", "[SSHFS] [信息] 未找到SSHFS进程或已终止"))
                    # 停止状态检查
                    self.sshfs_status_checking = False
                
            except Exception as e:
                self.message_queue.put(("log", f"[SSHFS] [错误] 强制终止SSHFS进程时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "SSHFS进程终止完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认强制终止SSHFS",
            "此操作将强制终止所有SSHFS进程。\n\n"
            "是否继续？",
            icon="warning"
        )
        
        if response:
            threading.Thread(target=kill_task, daemon=True).start()

    def copy_sshfs_command(self):
        """复制SSHFS命令到剪贴板"""
        try:
            command = self.sshfs_command_var.get()
            if command:
                # 复制到剪贴板
                self.root.clipboard_clear()
                self.root.clipboard_append(command)
                self.root.update()  # 确保剪贴板更新
                self.log_message(f"[SSHFS] 已复制命令到剪贴板: {command}")
            else:
                self.log_message("[SSHFS] SSHFS命令为空，无法复制")
        except Exception as e:
            self.log_message(f"[SSHFS] 复制失败: {str(e)}")

    def select_sshfs_local_path(self):
        """选择SSHFS本地路径"""
        try:
            from tkinter import filedialog
            
            # 获取当前路径作为初始目录
            current_path = self.sshfs_local_path_var.get().strip()
            if not current_path:
                current_path = self.save_path.get()
            
            # 打开文件夹选择对话框
            selected_path = filedialog.askdirectory(
                title="选择SSHFS本地挂载路径",
                initialdir=current_path
            )
            
            if selected_path:
                self.sshfs_local_path_var.set(selected_path)
                self.log_message(f"[SSHFS] 已选择本地路径: {selected_path}")
            
        except Exception as e:
            self.log_message(f"[SSHFS] 选择路径失败: {str(e)}")
    
    def on_language_changed(self, event=None):
        """语言选择变化时的处理"""
        try:
            language = self.sshfs_language_var.get()
            self.sshfs_use_chinese = (language == "中文")
            self.log_message(f"[SSHFS] 终端语言已切换为: {language}")
        except Exception as e:
            self.log_message(f"[SSHFS] 语言切换失败: {str(e)}")

    def create_sources_management(self, parent):
        """创建软件源管理界面"""
        # 主框架
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 顶部按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Button(button_frame, text="保存&应用软件源", command=self.save_and_apply_sources, style='Success.TButton').pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(button_frame, text="重新加载", command=self.reload_sources_files, style='Primary.TButton').pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(button_frame, text="备份当前配置", command=self.backup_sources, style='Primary.TButton').pack(
            side=tk.LEFT
        )
        
        # 软件源文件Tab页
        self.sources_notebook = ttk.Notebook(main_frame)
        self.sources_notebook.grid(row=1, column=0, sticky="nsew")
        
        # 存储文本编辑器
        self.sources_editors = {}
        
        # 延迟加载软件源文件，等待界面完全初始化完成
    
    def load_sources_files(self):
        """加载软件源文件"""
        try:
            # 清空现有tab页
            for tab_id in self.sources_notebook.tabs():
                self.sources_notebook.forget(tab_id)
            self.sources_editors.clear()
            
            sources_files = []
            
            # 添加主配置文件
            main_sources = "/etc/apt/sources.list"
            if os.path.exists(main_sources):
                sources_files.append(("sources.list", main_sources))
            
            # 添加sources.list.d目录下的.list文件
            sources_dir = "/etc/apt/sources.list.d"
            if os.path.exists(sources_dir):
                try:
                    for filename in sorted(os.listdir(sources_dir)):
                        if filename.endswith('.list'):
                            file_path = os.path.join(sources_dir, filename)
                            sources_files.append((filename, file_path))
                except PermissionError:
                    self.log_message("[软件源] 无权限访问 /etc/apt/sources.list.d 目录")
            
            # 为每个文件创建tab页
            for tab_name, file_path in sources_files:
                self.create_source_file_tab(tab_name, file_path)
            
            if sources_files:
                self.log_message(f"[软件源] 已加载 {len(sources_files)} 个软件源文件")
            else:
                self.log_message("[软件源] 未找到软件源文件")
                
        except Exception as e:
            self.log_message(f"[软件源] 加载软件源文件失败: {str(e)}")
    
    def create_source_file_tab(self, tab_name, file_path):
        """为单个软件源文件创建tab页"""
        try:
            # 创建tab框架
            tab_frame = ttk.Frame(self.sources_notebook)
            self.sources_notebook.add(tab_frame, text=tab_name)
            tab_frame.columnconfigure(0, weight=1)
            tab_frame.rowconfigure(1, weight=1)
            
            # 文件路径标签
            path_label = ttk.Label(tab_frame, text=f"文件: {file_path}", foreground="gray")
            path_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
            
            # 文本编辑器
            text_frame = ttk.Frame(tab_frame)
            text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            text_frame.columnconfigure(0, weight=1)
            text_frame.rowconfigure(0, weight=1)
            
            # 创建文本编辑器带滚动条
            text_editor = tk.Text(text_frame, wrap=tk.NONE, font=("Courier", 10))
            v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_editor.yview)
            h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_editor.xview)
            
            text_editor.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # 布局
            text_editor.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            # 读取文件内容
            content = self.read_source_file(file_path)
            text_editor.delete(1.0, tk.END)
            text_editor.insert(1.0, content)
            
            # 存储编辑器引用
            self.sources_editors[file_path] = text_editor
            
            # 状态栏显示行号和列号
            status_frame = ttk.Frame(tab_frame)
            status_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 5))
            
            status_label = ttk.Label(status_frame, text="行: 1, 列: 1", foreground="gray")
            status_label.pack(side=tk.RIGHT)
            
            # 绑定事件更新状态栏
            def update_cursor_position(event=None):
                cursor_pos = text_editor.index(tk.INSERT)
                line, col = cursor_pos.split('.')
                status_label.config(text=f"行: {line}, 列: {int(col)+1}")
            
            text_editor.bind('<KeyRelease>', update_cursor_position)
            text_editor.bind('<ButtonRelease>', update_cursor_position)
            
        except Exception as e:
            self.log_message(f"[软件源] 创建 {tab_name} tab页失败: {str(e)}")
    
    def read_source_file(self, file_path):
        """读取软件源文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except PermissionError:
            return f"# 无权限读取文件: {file_path}\n# 请使用管理员权限运行程序"
        except FileNotFoundError:
            return f"# 文件不存在: {file_path}"
        except Exception as e:
            return f"# 读取文件失败: {str(e)}"
    
    def save_and_apply_sources(self):
        """保存并应用软件源"""
        def save_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在保存并应用软件源..."))
                self.message_queue.put(("log", "[软件源] [开始] 开始保存并应用软件源"))
                
                # 创建临时目录存放所有临时文件
                import tempfile
                temp_dir = tempfile.mkdtemp()
                temp_files = []
                
                try:
                    # 准备所有临时文件
                    for file_path, editor in self.sources_editors.items():
                        try:
                            # 获取编辑器内容
                            content = editor.get(1.0, tk.END).rstrip('\n')
                            
                            # 创建临时文件
                            temp_path = os.path.join(temp_dir, os.path.basename(file_path))
                            with open(temp_path, 'w') as temp_file:
                                temp_file.write(content)
                            temp_files.append((temp_path, file_path))
                            
                        except Exception as e:
                            self.message_queue.put(("log", f"[软件源] [错误] 准备 {os.path.basename(file_path)} 时出错: {str(e)}"))
                    
                    if not temp_files:
                        self.message_queue.put(("log", "[软件源] [失败] 没有文件需要保存"))
                        return
                    
                    # 一次性复制所有文件（只需要一次鉴权）
                    self.message_queue.put(("log", "[软件源] [步骤1] 正在保存所有文件..."))
                    
                    # 构建正确的复制命令
                    copy_commands = []
                    for temp_path, file_path in temp_files:
                        copy_commands.append(f"cp '{temp_path}' '{file_path}'")
                    
                    # 使用pkexec一次性执行所有复制命令
                    copy_script = " && ".join(copy_commands)
                    copy_cmd = ["pkexec", "sh", "-c", copy_script]
                    result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        saved_files = [file_path for _, file_path in temp_files]
                        self.message_queue.put(("log", f"[软件源] [成功] 已保存 {len(saved_files)} 个文件"))
                        for file_path in saved_files:
                            self.message_queue.put(("log", f"[软件源] [成功] 已保存: {os.path.basename(file_path)}"))
                    else:
                        if "cancelled" in result.stderr.lower():
                            self.message_queue.put(("log", "[软件源] [取消] 用户取消了权限授权"))
                            return
                        else:
                            self.message_queue.put(("log", f"[软件源] [失败] 保存文件失败: {result.stderr}"))
                            return
                    
                    # 更新软件源
                    self.message_queue.put(("log", "[软件源] [步骤2] 正在更新软件源..."))
                    update_cmd = ["pkexec", "apt", "update"]
                    
                    # 使用Popen实时输出
                    update_process = subprocess.Popen(
                        update_cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True, 
                        bufsize=1, 
                        universal_newlines=True
                    )
                    
                    # 实时读取输出
                    while True:
                        output = update_process.stdout.readline()
                        if output == '' and update_process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            if line and not line.startswith('WARNING:'):
                                self.message_queue.put(("log", f"[软件源] [apt update] {line}"))
                    
                    # 读取错误输出
                    stderr_output = update_process.stderr.read()
                    update_returncode = update_process.wait(timeout=120)
                    
                    if update_returncode == 0:
                        self.message_queue.put(("log", "[软件源] [成功] 软件源更新完成"))
                        self.message_queue.put(("log", f"[软件源] [完成] 已保存 {len(saved_files)} 个文件并更新软件源"))
                    else:
                        if "cancelled" in stderr_output.lower():
                            self.message_queue.put(("log", "[软件源] [取消] 用户取消了软件源更新"))
                        else:
                            self.message_queue.put(("log", f"[软件源] [警告] 软件源更新失败: {stderr_output.strip()}"))
                
                finally:
                    # 清理临时文件和目录
                    for temp_path, _ in temp_files:
                        try:
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                        except:
                            pass
                    try:
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
                    except:
                        pass
                
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[软件源] [超时] 更新软件源超时"))
            except Exception as e:
                self.message_queue.put(("log", f"[软件源] [错误] 保存应用过程出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "软件源操作完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认保存软件源",
            "此操作将保存所有修改的软件源文件并更新软件源。\n\n"
            "[注意] 错误的软件源配置可能导致系统无法正常更新软件！\n\n"
            "是否继续？",
            icon="warning"
        )
        
        if response:
            threading.Thread(target=save_task, daemon=True).start()
    
    def reload_sources_files(self):
        """重新加载软件源文件"""
        self.load_sources_files()
        self.log_message("[软件源] 已重新加载软件源文件")
    
    def backup_sources(self):
        """备份当前软件源配置"""
        def backup_task():
            try:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = f"/tmp/sources_backup_{timestamp}"
                
                # 创建备份目录
                os.makedirs(backup_dir, exist_ok=True)
                
                # 备份主配置文件
                main_sources = "/etc/apt/sources.list"
                if os.path.exists(main_sources):
                    subprocess.run(["cp", main_sources, backup_dir], check=True)
                
                # 备份sources.list.d目录
                sources_dir = "/etc/apt/sources.list.d"
                if os.path.exists(sources_dir):
                    backup_sources_dir = os.path.join(backup_dir, "sources.list.d")
                    subprocess.run(["cp", "-r", sources_dir, backup_sources_dir], check=True)
                
                self.log_message(f"[软件源] [成功] 配置已备份到: {backup_dir}")
                
                # 询问是否打开备份目录
                response = messagebox.askyesno(
                    "备份完成", 
                    f"软件源配置已备份到:\n{backup_dir}\n\n是否打开备份目录？"
                )
                if response:
                    subprocess.Popen(["xdg-open", backup_dir])
                
            except Exception as e:
                self.log_message(f"[软件源] [失败] 备份失败: {str(e)}")
        
        threading.Thread(target=backup_task, daemon=True).start()
        
    def check_project_exists(self, project_name):
        """检查项目在本地是否存在"""
        project_path = os.path.join(self.save_path.get(), project_name)
        return os.path.exists(project_path)
    
    def update_project_status(self, project_name):
        """更新项目状态显示"""
        if hasattr(self, 'project_status_labels') and project_name in self.project_status_labels:
            exists = self.check_project_exists(project_name)
            label = self.project_status_labels[project_name]
            if exists:
                label.config(text="已下载", foreground="green")
            else:
                label.config(text="未下载", foreground="red")
    
    def refresh_all_project_status(self):
        """刷新所有项目的状态显示"""
        for project_name in self.project_repos.keys():
            self.update_project_status(project_name)
    
    def create_project_table(self, parent):
        """创建项目表格"""
        # 创建主容器
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 固定标题框架
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 配置标题列权重
        header_frame.columnconfigure(0, weight=1, minsize=80)   # 选择列
        header_frame.columnconfigure(1, weight=3, minsize=200)  # 项目列  
        header_frame.columnconfigure(2, weight=2, minsize=100)  # 状态列
        header_frame.columnconfigure(3, weight=3, minsize=200)  # 分支列
        header_frame.columnconfigure(4, weight=2, minsize=150)  # 进度列
        header_frame.columnconfigure(5, weight=2, minsize=120)  # 操作列
        
        # 表格标题行
        headers = ["选择", "项目名称", "本地状态", "分支选择", "下载进度", "操作"]
        for i, header in enumerate(headers):
            label = ttk.Label(header_frame, text=header, style='Header.TLabel')
            label.grid(row=0, column=i, sticky="ew", padx=2, pady=5)
        
        # 添加分隔线
        separator = ttk.Separator(header_frame, orient="horizontal")
        separator.grid(row=1, column=0, columnspan=len(headers), sticky="ew", pady=2)
        
        # 创建可滚动的内容框架
        content_scroll = ScrollableFrame(main_container)
        content_scroll.pack(fill=tk.BOTH, expand=True)
        
        # 获取内容框架
        content_frame = content_scroll.get_frame()
        content_frame.columnconfigure(0, weight=1, minsize=80)   # 选择列
        content_frame.columnconfigure(1, weight=3, minsize=200)  # 项目列  
        content_frame.columnconfigure(2, weight=2, minsize=100)  # 状态列
        content_frame.columnconfigure(3, weight=3, minsize=200)  # 分支列
        content_frame.columnconfigure(4, weight=2, minsize=150)  # 进度列
        content_frame.columnconfigure(5, weight=2, minsize=120)  # 操作列
        
        # 项目行
        self.project_checkboxes = {}  # 存储checkbox引用
        self.project_status_labels = {}  # 存储状态标签引用
        row = 0
        for project_name in self.project_repos.keys():
            # 选择框
            cb = ttk.Checkbutton(content_frame, variable=self.project_vars[project_name])
            cb.grid(row=row, column=0, padx=5, pady=2)
            self.project_checkboxes[project_name] = cb
            
            # 项目名称
            ttk.Label(content_frame, text=project_name, style='Info.TLabel').grid(row=row, column=1, sticky="w", padx=5, pady=3)
            
            # 本地状态
            exists = self.check_project_exists(project_name)
            status_text = "已下载" if exists else "未下载"
            status_color = "green" if exists else "red"
            status_label = ttk.Label(content_frame, text=status_text, foreground=status_color)
            status_label.grid(row=row, column=2, sticky="w", padx=5, pady=2)
            self.project_status_labels[project_name] = status_label
            
            # 分支选择
            branch_combo = ttk.Combobox(content_frame, textvariable=self.branch_vars[project_name], 
                                      values=("master",), state="readonly", width=20)
            branch_combo.grid(row=row, column=3, sticky="ew", padx=5, pady=2)
            branch_combo.bind('<<ComboboxSelected>>', 
                            lambda e, name=project_name: self.on_branch_changed(e, name))
            self.branch_combos[project_name] = branch_combo
            
            # 进度条容器
            progress_frame = ttk.Frame(content_frame)
            progress_frame.grid(row=row, column=4, sticky="ew", padx=5, pady=2)
            
            # 创建进度条（初始隐藏）
            progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=100)
            progress_label = ttk.Label(progress_frame, text="", width=12)
            
            self.progress_bars[project_name] = {
                'bar': progress_bar,
                'label': progress_label
            }
            
            # 操作按钮
            action_frame = ttk.Frame(content_frame)
            action_frame.grid(row=row, column=5, sticky="ew", padx=5, pady=2)
            
            ttk.Button(action_frame, text="打开", width=8, style='Primary.TButton',
                      command=lambda name=project_name: self.open_project_dir(name)).pack(side=tk.LEFT, padx=2)
            ttk.Button(action_frame, text="Qt打开", width=8, style='Primary.TButton',
                      command=lambda name=project_name: self.open_project_with_qtcreator(name)).pack(side=tk.LEFT, padx=2)
            ttk.Button(action_frame, text="删除", width=8, style='Danger.TButton',
                      command=lambda name=project_name: self.delete_project_dir(name)).pack(side=tk.LEFT, padx=2)
            ttk.Button(action_frame, text="打包", width=8, style='Success.TButton',
                      command=lambda name=project_name: self.deb_packet_generate_dir(name)).pack(side=tk.LEFT, padx=2)
            
            row += 1

    
    def create_package_table(self, parent):
        """创建软件包管理表格"""
        # 创建主容器
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置主容器权重
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)  # 内容区域可扩展
        
        # 固定标题框架
        header_frame = ttk.Frame(main_container)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        
        # 配置标题列权重
        header_frame.columnconfigure(0, weight=0, minsize=60)   # 选择列
        header_frame.columnconfigure(1, weight=1, minsize=150)  # 包名列
        header_frame.columnconfigure(2, weight=2, minsize=250)  # 描述列
        header_frame.columnconfigure(3, weight=0, minsize=100)  # 状态列
        
        # 表格头部
        ttk.Label(header_frame, text="选择", style='Header.TLabel').grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(header_frame, text="软件包", style='Header.TLabel').grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(header_frame, text="描述", style='Header.TLabel').grid(
            row=0, column=2, padx=5, pady=5, sticky=tk.W
        )
        ttk.Label(header_frame, text="状态", style='Header.TLabel').grid(
            row=0, column=3, padx=5, pady=5, sticky=tk.W
        )
        
        # 添加分隔线
        separator = ttk.Separator(header_frame, orient="horizontal")
        separator.grid(row=1, column=0, columnspan=4, sticky="ew", pady=2)
        
        # 创建可滚动的内容框架
        content_scroll = ScrollableFrame(main_container)
        content_scroll.grid(row=1, column=0, sticky="nsew")
        
        # 获取内容框架
        content_frame = content_scroll.get_frame()
        content_frame.columnconfigure(0, weight=0, minsize=60)   # 选择列
        content_frame.columnconfigure(1, weight=1, minsize=150)  # 包名列
        content_frame.columnconfigure(2, weight=2, minsize=250)  # 描述列
        content_frame.columnconfigure(3, weight=0, minsize=100)  # 状态列
        
        # 软件包行
        self.package_status_labels = {}
        for idx, (package_name, description) in enumerate(self.packages.items()):
            row = idx
            
            # 选择框（默认全部勾选）
            var = tk.BooleanVar(value=True)
            self.package_vars[package_name] = var
            ttk.Checkbutton(content_frame, variable=var).grid(
                row=row, column=0, padx=5, pady=2, sticky=tk.W
            )
            
            # 软件包名称
            ttk.Label(content_frame, text=package_name, style='Info.TLabel').grid(
                row=row, column=1, padx=5, pady=3, sticky=tk.W
            )
            
            # 描述
            ttk.Label(content_frame, text=description, style='Info.TLabel').grid(
                row=row, column=2, padx=5, pady=3, sticky=tk.W
            )
            
            # 状态标签
            status_label = ttk.Label(content_frame, text="检查中...", 
                                   style='Info.TLabel', foreground="orange")
            status_label.grid(row=row, column=3, padx=5, pady=3, sticky=tk.W)
            self.package_status_labels[package_name] = status_label

        
        # 启动时检查软件包状态
        self.root.after(3000, self.check_package_status)

    def select_all_packages(self):
        """全选软件包"""
        for var in self.package_vars.values():
            var.set(True)
        selected_packages = list(self.packages.keys())
        self.log_message(f"[软件包] [全选] 已全选所有软件包 ({len(selected_packages)} 个)")
        for pkg in selected_packages:
            desc = self.packages.get(pkg, "未知软件包")
            self.log_message(f"[软件包] • {pkg} - {desc}")

    def deselect_all_packages(self):
        """全不选软件包"""
        for var in self.package_vars.values():
            var.set(False)
        total_packages = len(self.packages)
        self.log_message(f"[软件包] [取消] 已取消选择所有软件包 ({total_packages} 个)")
    
    def invert_package_selection(self):
        """反选软件包"""
        selected_count = 0
        for var in self.package_vars.values():
            var.set(not var.get())
            if var.get():
                selected_count += 1
        total_packages = len(self.packages)
        unselected_count = total_packages - selected_count
        self.log_message(f"[软件包] [反选] 已反选软件包，当前选中 {selected_count} 个，未选中 {unselected_count} 个")

    def check_package_status(self):
        """检查软件包安装状态"""
        def check_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在检查软件包状态..."))
                self.message_queue.put(("log", "[软件包] [检查] 开始检查软件包安装状态"))
                
                installed_count = 0
                not_installed_count = 0
                error_count = 0
                
                for package_name in self.packages.keys():
                    try:
                        # 使用dpkg-query检查软件包状态
                        result = subprocess.run(
                            ["dpkg-query", "-W", "-f='${Status}'", package_name],
                            capture_output=True, text=True, timeout=10
                        )
                        
                        if result.returncode == 0 and "install ok installed" in result.stdout:
                            self.message_queue.put(("package_status", package_name, "已安装", "green"))
                            self.message_queue.put(("log", f"[软件包] [成功] {package_name} 已安装"))
                            installed_count += 1
                        else:
                            self.message_queue.put(("package_status", package_name, "未安装", "red"))
                            self.message_queue.put(("log", f"[软件包] [未装] {package_name} 未安装"))
                            not_installed_count += 1
                            
                    except subprocess.TimeoutExpired:
                        self.message_queue.put(("package_status", package_name, "检查超时", "orange"))
                        self.message_queue.put(("log", f"[软件包] [超时] {package_name} 状态检查超时"))
                        error_count += 1
                    except Exception as e:
                        self.message_queue.put(("package_status", package_name, "检查错误", "red"))
                        self.message_queue.put(("log", f"[软件包] [错误] {package_name} 状态检查出错: {str(e)}"))
                        error_count += 1
                
                # 输出检查结果统计
                total_packages = len(self.packages)
                self.message_queue.put(("log", f"[软件包] [统计] 状态检查完成: 总计 {total_packages} 个软件包"))
                self.message_queue.put(("log", f"[软件包] [统计] 已安装: {installed_count} 个，未安装: {not_installed_count} 个，错误: {error_count} 个"))
                self.message_queue.put(("status", "软件包状态检查完成"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] [失败] 软件包状态检查失败: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=check_task, daemon=True).start()

    def install_packages(self):
        """安装选中的软件包"""
        selected_packages = [name for name, var in self.package_vars.items() if var.get()]
        
        if not selected_packages:
            messagebox.showwarning("警告", "请至少选择一个软件包进行安装")
            return
        
        # 确认安装
        response = messagebox.askyesno(
            "确认安装软件包",
            f"是否确认安装以下 {len(selected_packages)} 个软件包？\n\n" +
            "\n".join([f"• {name} - {self.packages[name]}" for name in selected_packages]) +
            "\n\n此操作需要管理员权限。",
            icon="question"
        )
        
        if not response:
            return
        
        def install_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在安装软件包..."))
                self.message_queue.put(("log", f"[软件包] [开始] 开始安装 {len(selected_packages)} 个软件包"))
                
                # 显示将要安装的软件包列表
                for pkg in selected_packages:
                    desc = self.packages.get(pkg, "未知软件包")
                    self.message_queue.put(("log", f"[软件包] • {pkg} - {desc}"))
                
                # 步骤1: 更新软件源
                self.message_queue.put(("log", "[软件包] [步骤1] 步骤 1/2: 更新软件源 (apt update)"))
                self.message_queue.put(("status", "正在更新软件源..."))
                
                update_cmd = ["pkexec", "apt", "update"]
                self.message_queue.put(("log", f"[软件包] 执行命令: {' '.join(update_cmd)}"))
                
                # 使用Popen实时输出
                try:
                    update_process = subprocess.Popen(
                        update_cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True, 
                        bufsize=1, 
                        universal_newlines=True
                    )
                    
                    # 实时读取输出
                    while True:
                        output = update_process.stdout.readline()
                        if output == '' and update_process.poll() is not None:
                            break
                        if output:
                            # 过滤掉空行和不重要的信息
                            line = output.strip()
                            if line and not line.startswith('WARNING:'):
                                self.message_queue.put(("log", f"[软件包] [apt update] {line}"))
                    
                    # 读取错误输出
                    stderr_output = update_process.stderr.read()
                    update_returncode = update_process.wait(timeout=120)
                    
                    if update_returncode == 0:
                        self.message_queue.put(("log", "[软件包] [成功] 软件源更新成功"))
                    else:
                        self.message_queue.put(("log", f"[软件包] [警告] 软件源更新失败，返回码: {update_returncode}"))
                        if stderr_output:
                            if "cancelled" in stderr_output.lower():
                                self.message_queue.put(("log", "[软件包] [取消] 用户取消了权限授权"))
                                return
                            else:
                                self.message_queue.put(("log", f"[软件包] [错误信息] {stderr_output.strip()}"))
                    
                    self.message_queue.put(("log", "[软件包] 尝试继续安装软件包..."))
                        
                except subprocess.TimeoutExpired:
                    self.message_queue.put(("log", "[软件包] [超时] 软件源更新超时"))
                    if 'update_process' in locals():
                        update_process.kill()
                except Exception as e:
                    self.message_queue.put(("log", f"[软件包] [错误] 软件源更新过程出错: {str(e)}"))
                
                # 步骤2: 安装软件包
                self.message_queue.put(("log", "[软件包] [步骤2] 步骤 2/2: 安装软件包"))
                self.message_queue.put(("status", "正在安装软件包..."))
                
                # 使用pkexec获取图形化sudo权限
                install_cmd = ["pkexec", "apt", "install", "-y"] + selected_packages
                
                self.message_queue.put(("log", f"[软件包] 执行命令: {' '.join(install_cmd)}"))
                
                # 使用Popen实时输出安装进度
                try:
                    install_process = subprocess.Popen(
                        install_cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True, 
                        bufsize=1, 
                        universal_newlines=True
                    )
                    
                    # 实时读取输出
                    while True:
                        output = install_process.stdout.readline()
                        if output == '' and install_process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            if line:
                                # 过滤和格式化输出信息
                                if 'Reading package lists' in line:
                                    self.message_queue.put(("log", "[软件包] [安装] 正在读取软件包列表..."))
                                elif 'Building dependency tree' in line:
                                    self.message_queue.put(("log", "[软件包] [安装] 正在分析软件包依赖关系..."))
                                elif 'Reading state information' in line:
                                    self.message_queue.put(("log", "[软件包] [安装] 正在读取状态信息..."))
                                elif 'The following' in line:
                                    self.message_queue.put(("log", f"[软件包] [信息] {line}"))
                                elif 'Setting up' in line:
                                    self.message_queue.put(("log", f"[软件包] [配置] {line}"))
                                elif 'Processing triggers' in line:
                                    self.message_queue.put(("log", f"[软件包] [处理] {line}"))
                                elif 'Unpacking' in line:
                                    self.message_queue.put(("log", f"[软件包] [解包] {line}"))
                                elif 'Get:' in line:
                                    self.message_queue.put(("log", f"[软件包] [下载] {line}"))
                                elif '已下载' in line or 'downloaded' in line.lower():
                                    self.message_queue.put(("log", f"[软件包] [下载] {line}"))
                                elif not line.startswith('WARNING:') and not line.startswith('debconf:'):
                                    self.message_queue.put(("log", f"[软件包] [安装] {line}"))
                    
                    # 读取错误输出
                    stderr_output = install_process.stderr.read()
                    install_returncode = install_process.wait(timeout=600)
                    
                    if install_returncode == 0:
                        self.message_queue.put(("log", "[软件包] [成功] 软件包安装成功"))
                        self.message_queue.put(("log", f"[软件包] [完成] 已成功安装: {', '.join(selected_packages)}"))
                        
                        # 显示安装详情
                        for pkg in selected_packages:
                            self.message_queue.put(("log", f"[软件包] [成功] {pkg} 安装完成"))
                        
                        # 重新检查状态
                        self.root.after(1000, self.check_package_status)
                    else:
                        self.message_queue.put(("log", f"[软件包] [失败] 软件包安装失败，返回码: {install_returncode}"))
                        if stderr_output:
                            if "cancelled" in stderr_output.lower():
                                self.message_queue.put(("log", "[软件包] [取消] 用户取消了权限授权"))
                            else:
                                self.message_queue.put(("log", f"[软件包] [错误信息] {stderr_output.strip()}"))
                    
                except subprocess.TimeoutExpired:
                    self.message_queue.put(("log", "[软件包] [超时] 软件包安装超时"))
                    if 'install_process' in locals():
                        install_process.kill()
                except Exception as install_e:
                    self.message_queue.put(("log", f"[软件包] [错误] 软件包安装过程出错: {str(install_e)}"))
                    
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[软件包] [超时] 安装超时，请检查网络连接"))
                if 'install_process' in locals():
                    install_process.kill()
            except Exception as install_e:
                self.message_queue.put(("log", f"[软件包] [错误] 安装过程出错: {str(install_e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "软件包安装完成"))
        
        threading.Thread(target=install_task, daemon=True).start()

    def remove_packages(self):
        """移除选中的软件包"""
        selected_packages = [name for name, var in self.package_vars.items() if var.get()]
        
        if not selected_packages:
            messagebox.showwarning("警告", "请至少选择一个软件包进行移除")
            return
        
        # 确认移除
        response = messagebox.askyesno(
            "确认移除软件包",
            f"是否确认移除以下 {len(selected_packages)} 个软件包？\n\n" +
            "\n".join([f"• {name} - {self.packages[name]}" for name in selected_packages]) +
            "\n\n此操作需要管理员权限，移除后可能影响系统功能。",
            icon="warning"
        )
        
        if not response:
            return
        
        def remove_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在移除软件包..."))
                self.message_queue.put(("log", f"[软件包] [移除] 开始移除 {len(selected_packages)} 个软件包"))
                
                # 显示将要移除的软件包列表
                for pkg in selected_packages:
                    desc = self.packages.get(pkg, "未知软件包")
                    self.message_queue.put(("log", f"[软件包] • {pkg} - {desc}"))
                
                # 使用pkexec获取图形化sudo权限
                cmd = ["pkexec", "apt", "remove", "-y"] + selected_packages
                
                self.message_queue.put(("log", f"[软件包] 执行命令: {' '.join(cmd)}"))
                
                # 使用Popen实时输出移除进度
                try:
                    remove_process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True, 
                        bufsize=1, 
                        universal_newlines=True
                    )
                    
                    # 实时读取输出
                    while True:
                        output = remove_process.stdout.readline()
                        if output == '' and remove_process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            if line:
                                # 过滤和格式化输出信息
                                if 'Reading package lists' in line:
                                    self.message_queue.put(("log", "[软件包] [移除] 正在读取软件包列表..."))
                                elif 'Building dependency tree' in line:
                                    self.message_queue.put(("log", "[软件包] [移除] 正在分析软件包依赖关系..."))
                                elif 'Reading state information' in line:
                                    self.message_queue.put(("log", "[软件包] [移除] 正在读取状态信息..."))
                                elif 'The following' in line:
                                    self.message_queue.put(("log", f"[软件包] [信息] {line}"))
                                elif 'Removing' in line:
                                    self.message_queue.put(("log", f"[软件包] [移除] {line}"))
                                elif 'Processing triggers' in line:
                                    self.message_queue.put(("log", f"[软件包] [处理] {line}"))
                                elif not line.startswith('WARNING:') and not line.startswith('debconf:'):
                                    self.message_queue.put(("log", f"[软件包] [移除] {line}"))
                    
                    # 读取错误输出
                    stderr_output = remove_process.stderr.read()
                    remove_returncode = remove_process.wait(timeout=300)
                    
                    if remove_returncode == 0:
                        self.message_queue.put(("log", "[软件包] [成功] 软件包移除成功"))
                        self.message_queue.put(("log", f"[软件包] [完成] 已成功移除: {', '.join(selected_packages)}"))
                        
                        # 显示移除详情
                        for pkg in selected_packages:
                            self.message_queue.put(("log", f"[软件包] [成功] {pkg} 移除完成"))
                        
                        # 重新检查状态
                        self.root.after(1000, self.check_package_status)
                    else:
                        self.message_queue.put(("log", f"[软件包] [失败] 软件包移除失败，返回码: {remove_returncode}"))
                        if stderr_output:
                            if "cancelled" in stderr_output.lower():
                                self.message_queue.put(("log", "[软件包] [取消] 用户取消了权限授权"))
                            else:
                                self.message_queue.put(("log", f"[软件包] [错误信息] {stderr_output.strip()}"))
                    
                except subprocess.TimeoutExpired:
                    self.message_queue.put(("log", "[软件包] [超时] 软件包移除超时"))
                    if 'remove_process' in locals():
                        remove_process.kill()
                except Exception as remove_e:
                    self.message_queue.put(("log", f"[软件包] [错误] 软件包移除过程出错: {str(remove_e)}"))
                    
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[软件包] [超时] 移除超时"))
                if 'remove_process' in locals():
                    remove_process.kill()
            except Exception as remove_e:
                self.message_queue.put(("log", f"[软件包] [错误] 移除过程出错: {str(remove_e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "软件包移除完成"))
        
        threading.Thread(target=remove_task, daemon=True).start()

    def cleanup_all(self):
        """一键清理：移除所有软件包和本地Git仓库"""
        # 危险操作确认
        response = messagebox.askyesno(
            "危险操作确认",
            "一键清理将执行以下操作：\n\n" +
            "[移除] 移除所有选中的软件包：\n" +
            "\n".join([f"• {name}" for name in self.packages.keys()]) +
            f"\n\n[删除] 删除所有项目的本地Git仓库：\n" +
            "\n".join([f"• {name}" for name in self.project_repos.keys()]) +
            f"\n\n[路径] 删除路径: {self.save_path.get()}\n\n" +
            "[警告] 此操作不可恢复，请谨慎确认！\n\n" +
            "是否继续执行一键清理？",
            icon="warning"
        )
        
        if not response:
            return
        
        # 二次确认
        response2 = messagebox.askyesno(
            "最终确认",
            "您即将清理所有软件包和项目仓库！\n\n" +
            "这将删除所有本地代码和配置。\n\n" +
            "确认要继续吗？",
            icon="error"
        )
        
        if not response2:
            return
        
        def cleanup_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在执行一键清理..."))
                self.message_queue.put(("log", "[清理] [开始] 开始执行一键清理操作"))
                
                # 1. 移除软件包
                self.message_queue.put(("log", "[清理] 步骤 1/2: 移除软件包"))
                package_list = list(self.packages.keys())
                
                cmd = ["pkexec", "apt", "remove", "-y"] + package_list
                self.message_queue.put(("log", f"[清理] 执行: {' '.join(cmd)}"))
                
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300
                )
                
                if result.returncode == 0:
                    self.message_queue.put(("log", f"[清理] [成功] 软件包移除成功: {', '.join(package_list)}"))
                else:
                    self.message_queue.put(("log", f"[清理] [失败] 软件包移除失败: {result.stderr}"))
                
                # 2. 删除项目目录
                self.message_queue.put(("log", "[清理] 步骤 2/2: 删除项目仓库"))
                
                import shutil
                success_count = 0
                error_count = 0
                
                for project_name in self.project_repos.keys():
                    try:
                        project_path = os.path.join(self.save_path.get(), project_name)
                        
                        if os.path.exists(project_path):
                            shutil.rmtree(project_path)
                            self.message_queue.put(("log", f"[清理] [成功] 已删除 {project_name}"))
                            success_count += 1
                        else:
                            self.message_queue.put(("log", f"[清理] [跳过] {project_name} 目录不存在"))
                    except Exception as e:
                        self.message_queue.put(("log", f"[清理] [失败] {project_name} 删除失败: {str(e)}"))
                        error_count += 1
                
                self.message_queue.put(("log", f"[清理] [统计] 项目清理统计: 成功 {success_count} 个, 失败 {error_count} 个"))
                
                # 重新检查软件包状态
                self.root.after(2000, self.check_package_status)
                
                self.message_queue.put(("log", "[清理] [完成] 一键清理操作完成"))
                self.message_queue.put(("status", "一键清理完成"))
                
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", "[清理] [超时] 清理操作超时"))
            except Exception as e:
                self.message_queue.put(("log", f"[清理] [失败] 清理过程中出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=cleanup_task, daemon=True).start()
    
    def on_source_changed(self, event=None):
        """源选择改变时的回调"""
        source = self.source_var.get()
        self.log_message(f"已切换到 {source.upper()} 源")
        # 清空现有分支信息，重新查询
        for combo in self.branch_combos.values():
            combo['values'] = ("master",)
            combo.set("master")
        # 自动重新查询分支
        self.root.after(500, self.auto_query_branches)
    
    def on_branch_changed(self, event, project_name):
        """分支选择改变时的回调"""
        if self.branch_switching.get(project_name, False):
            self.log_message(f"[分支] {project_name} 正在切换中，忽略重复操作")
            return  # 正在切换中，避免递归
            
        project_path = os.path.join(self.save_path.get(), project_name)
        new_branch = self.branch_vars[project_name].get()
        
        self.log_message(f"[分支] {project_name} 用户选择分支: {new_branch}")
        
        if not os.path.exists(project_path):
            # 项目目录不存在时给出提示
            self.log_message(f"[提示] {project_name} 本地保存路径不存在: {project_path}")
            self.log_message(f"[提示] {project_name} 分支选择已保存为 {new_branch}，下次下载时将使用此分支")
            # 自动保存配置以记录分支选择
            self.save_config()
            return
        
        # 检查当前分支
        try:
            self.log_message(f"[分支] {project_name} 检查本地Git仓库状态...")
            
            current_branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=project_path
            )
            
            if current_branch_result.returncode != 0:
                self.log_message(f"[错误] {project_name} 无法获取当前分支: {current_branch_result.stderr}")
                self.cancel_branch_switch(project_name, "master")
                return
                
            current_branch = current_branch_result.stdout.strip()
            self.log_message(f"[分支] {project_name} 当前分支: {current_branch}")
            
            if current_branch == new_branch:
                self.log_message(f"[分支] {project_name} 已经是目标分支 {new_branch}，无需切换")
                return  # 已经是目标分支
                
            # 检查是否有未提交的修改
            self.log_message(f"[分支] {project_name} 检查是否有未提交的修改...")
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=project_path
            )
            
            has_changes = bool(status_result.stdout.strip())
            
            if has_changes:
                self.log_message(f"[警告] {project_name} 检测到未提交的修改")
                
                # 有未提交的修改，询问用户
                response = messagebox.askyesnocancel(
                    "检测到未提交的修改",
                    f"项目 {project_name} 在分支 {current_branch} 上有未提交的修改。\n\n"
                    f"是否强制切换到分支 {new_branch}？\n"
                    f"• 是：强制切换并丢弃修改\n"
                    f"• 否：取消切换\n"
                    f"• 取消：取消操作",
                    icon="warning"
                )
                
                if response is True:  # 强制切换
                    self.log_message(f"[分支] {project_name} 用户选择强制切换并丢弃修改")
                    self.force_switch_branch(project_name, new_branch, current_branch)
                elif response is False:  # 取消切换
                    self.log_message(f"[分支] {project_name} 用户取消分支切换")
                    self.cancel_branch_switch(project_name, current_branch)
                else:  # 取消操作
                    self.log_message(f"[分支] {project_name} 用户取消操作")
                    self.cancel_branch_switch(project_name, current_branch)
            else:
                self.log_message(f"[分支] {project_name} 工作区干净，可以安全切换分支")
                # 没有修改，直接切换
                self.switch_branch(project_name, new_branch)
                
        except Exception as e:
            self.log_message(f"[错误] {project_name} 检查分支状态失败: {str(e)}")
            import traceback
            self.log_message(f"[错误] {project_name} 详细错误: {traceback.format_exc()}")
            self.cancel_branch_switch(project_name, "master")
    
    def force_switch_branch(self, project_name, new_branch, old_branch):
        """强制切换分支"""
        def switch_task():
            try:
                project_path = os.path.join(self.save_path.get(), project_name)
                
                # 强制重置到当前分支HEAD
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=project_path, check=True)
                
                # 清理未跟踪的文件
                subprocess.run(["git", "clean", "-fd"], cwd=project_path, check=True)
                
                # 切换分支
                result = subprocess.run(
                    ["git", "checkout", new_branch],
                    capture_output=True, text=True, cwd=project_path
                )
                
                if result.returncode == 0:
                    self.message_queue.put(("log", f"[成功] {project_name} 已强制切换到分支 {new_branch}"))
                    self.message_queue.put(("save_config", ))
                else:
                    self.message_queue.put(("log", f"[失败] {project_name} 分支切换失败: {result.stderr}"))
                    self.message_queue.put(("cancel_branch", project_name, old_branch))
                    
            except Exception as e:
                self.message_queue.put(("log", f"[错误] {project_name} 分支切换出错: {str(e)}"))
                self.message_queue.put(("cancel_branch", project_name, old_branch))
            finally:
                self.branch_switching[project_name] = False
        
        self.branch_switching[project_name] = True
        threading.Thread(target=switch_task, daemon=True).start()
    
    def switch_branch(self, project_name, new_branch):
        """普通分支切换"""
        def switch_task():
            try:
                project_path = os.path.join(self.save_path.get(), project_name)
                
                # 先获取当前分支，以便失败时恢复
                current_branch_result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, cwd=project_path
                )
                current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "master"
                
                result = subprocess.run(
                    ["git", "checkout", new_branch],
                    capture_output=True, text=True, cwd=project_path
                )
                
                if result.returncode == 0:
                    self.message_queue.put(("log", f"[成功] {project_name} 已切换到分支 {new_branch}"))
                    self.message_queue.put(("save_config", ))
                else:
                    # 记录第一次失败的详细信息
                    self.message_queue.put(("log", f"[调试] {project_name} 本地分支切换失败: {result.stderr.strip()}"))
                    
                    # 尝试从远程创建分支
                    self.message_queue.put(("log", f"[尝试] {project_name} 尝试从远程创建分支 {new_branch}"))
                    result2 = subprocess.run(
                        ["git", "checkout", "-b", new_branch, f"origin/{new_branch}"],
                        capture_output=True, text=True, cwd=project_path
                    )
                    if result2.returncode == 0:
                        self.message_queue.put(("log", f"[成功] {project_name} 已创建并切换到分支 {new_branch}"))
                        self.message_queue.put(("save_config", ))
                    else:
                        self.message_queue.put(("log", f"[失败] {project_name} 远程分支创建也失败: {result2.stderr.strip()}"))
                        self.message_queue.put(("log", f"[失败] {project_name} 分支切换失败，恢复到 {current_branch}"))
                        self.message_queue.put(("cancel_branch", project_name, current_branch))
                        
            except Exception as e:
                self.message_queue.put(("log", f"[错误] {project_name} 分支切换出错: {str(e)}"))
                # 在异常情况下，也尝试获取当前分支进行恢复
                try:
                    current_branch_result = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True, cwd=project_path
                    )
                    current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "master"
                    self.message_queue.put(("cancel_branch", project_name, current_branch))
                except:
                    self.message_queue.put(("cancel_branch", project_name, "master"))
            finally:
                self.branch_switching[project_name] = False
        
        self.branch_switching[project_name] = True
        threading.Thread(target=switch_task, daemon=True).start()
    
    def cancel_branch_switch(self, project_name, old_branch):
        """取消分支切换，恢复到原分支"""
        self.branch_switching[project_name] = True
        self.branch_vars[project_name].set(old_branch)
        self.branch_switching[project_name] = False
        self.log_message(f"[取消] {project_name} 分支切换已取消")
    
    def delete_project_dir(self, project_name):
        """删除项目目录"""
        project_path = os.path.join(self.save_path.get(), project_name)
        
        if not os.path.exists(project_path):
            messagebox.showwarning("警告", f"项目目录不存在: {project_name}")
            return
            
        response = messagebox.askyesno(
            "确认删除",
            f"确定要删除项目目录吗？\n\n"
            f"项目: {project_name}\n"
            f"路径: {project_path}\n\n"
            f"此操作不可恢复！",
            icon="warning"
        )
        
        if response:
            try:
                subprocess.run(["rm", "-rf", project_path], check=True)
                self.log_message(f"[删除] 已删除项目目录: {project_name}")
                # 更新项目状态显示
                self.update_project_status(project_name)
                messagebox.showinfo("删除成功", f"项目 {project_name} 目录已删除")
            except Exception as e:
                error_msg = f"删除项目目录失败: {str(e)}"
                self.log_message(f"[错误] {error_msg}")
                messagebox.showerror("删除失败", error_msg)
    
    def install_dependencies(self):
        """安装选中项目的依赖"""
        selected_projects = [name for name, var in self.project_vars.items() if var.get()]
        
        if not selected_projects:
            messagebox.showwarning("警告", "请至少选择一个项目进行依赖安装")
            return
            
        # 检查项目是否存在
        existing_projects = []
        for project_name in selected_projects:
            project_path = os.path.join(self.save_path.get(), project_name)
            if os.path.exists(project_path):
                existing_projects.append(project_name)
                
        if not existing_projects:
            messagebox.showwarning("警告", "选中的项目目录都不存在，请先下载项目")
            return
            
        # 确认安装
        project_list = "\n".join([f"• {name}" for name in existing_projects])
        response = messagebox.askyesno(
            "确认安装依赖",
            f"将为以下项目安装构建依赖：\n\n{project_list}\n\n"
            f"此操作将执行：sudo apt build-dep . -y\n"
            f"需要管理员权限，是否继续？",
            icon="question"
        )
        
        if response:
            def install_task():
                try:
                    self.message_queue.put(("progress", "start"))
                    
                    for project_name in existing_projects:
                        self.message_queue.put(("status", f"正在为 {project_name} 安装依赖..."))
                        self.message_queue.put(("log", f"[安装] 开始安装 {project_name} 的构建依赖"))
                        
                        project_path = os.path.join(self.save_path.get(), project_name)
                        
                        # 执行 sudo apt build-dep . -y，实时显示输出
                        self.message_queue.put(("log", f"[{project_name}] 执行命令: sudo apt build-dep {project_path} -y"))

                        process = subprocess.Popen(
                            ["pkexec", "sudo", "apt", "build-dep", project_path, "-y"],
                            cwd=project_path,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, universal_newlines=True
                        )
                        
                        # 实时读取输出
                        if process.stdout:
                            for line in iter(process.stdout.readline, ''):
                                if line.strip():
                                    clean_line = line.strip()
                                    # 显示所有apt输出，但过滤掉一些不重要的信息
                                    skip_keywords = ['warning: apt does not have a stable cli', 'warning: apt-key', 'deprecated']
                                    if not any(skip.lower() in clean_line.lower() for skip in skip_keywords):
                                        self.message_queue.put(("log", f"[{project_name}] {clean_line}"))
                        
                        # 等待进程完成
                        process.wait()
                        
                        if process.returncode == 0:
                            self.message_queue.put(("log", f"[成功] {project_name} 依赖安装完成"))
                        else:
                            self.message_queue.put(("log", f"[失败] {project_name} 依赖安装失败，返回码: {process.returncode}"))
                    
                    self.message_queue.put(("status", "依赖安装完成"))
                    self.message_queue.put(("log", "[完成] 所有选中项目的依赖安装完成"))
                    
                except Exception as e:
                    self.message_queue.put(("log", f"[错误] 依赖安装过程中出错: {str(e)}"))
                finally:
                    self.message_queue.put(("progress", "stop"))
            
            threading.Thread(target=install_task, daemon=True).start()
    
    def select_path(self):
        """选择保存路径"""
        from tkinter import filedialog
        selected_path = filedialog.askdirectory(initialdir=self.save_path.get())
        if selected_path:
            self.save_path.set(selected_path)
            self.log_message(f"[设置] 保存路径已更改为: {selected_path}")
            self.save_config()  # 自动保存配置

    def _on_key_press(self, event):
        """处理键盘按键事件"""
        # 允许Ctrl+C (复制) 和 Ctrl+A (全选)
        if event.state & 0x4:  # Ctrl键被按下
            if event.keysym in ['c', 'C', 'a', 'A']:
                return  # 允许这些组合键
        # 阻止其他所有按键
        return 'break'
    def _show_log_context_menu(self, event):
        """显示日志文本框右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="复制", command=self._copy_log_text)
        context_menu.add_command(label="全选", command=self._select_all_log_text)
        context_menu.add_separator()
        context_menu.add_command(label="清空日志", command=self.clear_log)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _copy_log_text(self):
        """复制选中的日志文本"""
        try:
            selected_text = self.log_text.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            # 如果没有选中文本，不做任何操作
            pass
    
    def _select_all_log_text(self):
        """全选日志文本"""
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)

    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # 检查日志组件是否已创建，避免初始化时的错误
        if hasattr(self, 'log_text') and self.log_text:
            # 日志文本框保持NORMAL状态，允许选择和复制
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)
        
        # 同时更新状态栏（如果存在）
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(message)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("日志已清空")
    
    def show_progress(self, project_name, progress=None):
        """显示项目进度条"""
        if project_name in self.progress_bars:
            pb = self.progress_bars[project_name]
            # 确保进度条组件显示
            pb['bar'].pack(side=tk.LEFT, padx=(0, 5))
            pb['label'].pack(side=tk.LEFT)
            if progress is not None:
                pb['bar'].config(mode='determinate')
                pb['bar']['value'] = progress
                pb['label'].config(text=f"{progress:.1f}%")
            else:
                pb['bar'].config(mode='indeterminate')
                pb['bar'].start()
                pb['label'].config(text="下载中...")
    
    def hide_progress(self, project_name):
        """隐藏项目进度条"""
        if project_name in self.progress_bars:
            pb = self.progress_bars[project_name]
            pb['bar'].stop()
            pb['bar'].pack_forget()
            pb['label'].pack_forget()
    
    def update_progress(self, project_name, progress, status_text):
        """更新项目进度"""
        if project_name in self.progress_bars:
            pb = self.progress_bars[project_name]
            pb['bar']['value'] = progress
            pb['label'].config(text=status_text)
    
    def download_single_project(self, project_name, repo_url, branch, save_path):
        """下载单个项目"""
        try:
            project_path = os.path.join(save_path, project_name)
            
            # 显示进度条
            self.message_queue.put(("show_progress", project_name, None))
            
            # 如果目录已存在，先删除
            if os.path.exists(project_path):
                self.message_queue.put(("log", f"[删除] {project_name}: 删除已存在的目录"))
                self.message_queue.put(("update_progress", project_name, 10, "删除旧目录"))
                subprocess.run(["rm", "-rf", project_path], check=True)
            
            # 检查是否需要认证
            clone_url = repo_url
            if self.requires_auth(project_name, repo_url):
                self.message_queue.put(("log", f"[认证] {project_name}: 项目需要身份认证"))
                
                # 获取认证凭据（在主线程中执行）
                credentials = None
                auth_result = [None]  # 使用列表来存储结果，以便在闭包中修改
                
                def get_credentials():
                    auth_result[0] = self.get_auth_credentials(project_name, repo_url)
                
                # 在主线程中执行认证对话框
                self.root.after(0, get_credentials)
                
                # 等待认证对话框的结果
                while auth_result[0] is None:
                    time.sleep(0.1)
                
                credentials = auth_result[0]
                
                if credentials['cancelled']:
                    self.message_queue.put(("log", f"[取消] {project_name}: 用户取消了认证"))
                    self.message_queue.put(("hide_progress", project_name))
                    return False
                
                if credentials['username'] and credentials['password']:
                    clone_url = self.build_authenticated_url(repo_url, credentials['username'], credentials['password'])
                    self.message_queue.put(("log", f"[认证] {project_name}: 认证信息已设置，用户: {credentials['username']}"))
                else:
                    self.message_queue.put(("log", f"[错误] {project_name}: 认证信息不完整"))
                    self.message_queue.put(("hide_progress", project_name))
                    return False
            
            # 克隆仓库
            self.message_queue.put(("log", f"[下载] {project_name}: 开始克隆仓库 {repo_url}"))
            self.message_queue.put(("update_progress", project_name, 20, "克隆中..."))
            
            # 实时显示git clone输出
            process = subprocess.Popen(
                ["git", "clone", "--progress", clone_url, project_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, cwd=save_path, universal_newlines=True
            )
            
            # 实时读取输出
            progress_count = 0
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line.strip():
                        clean_line = line.strip()
                        # 过滤并显示有用的信息
                        if any(keyword in clean_line.lower() for keyword in ['receiving', 'resolving', 'counting', 'compressing', 'done', 'total', 'objects', 'remote']):
                            self.message_queue.put(("log", f"[{project_name}] {clean_line}"))
                            # 根据输出更新进度
                            progress_count += 1
                            progress = min(20 + (progress_count * 2), 60)
                            self.message_queue.put(("update_progress", project_name, progress, "克隆中..."))
            
            # 等待进程完成
            process.wait()
            
            if process.returncode != 0:
                # 获取错误输出
                stderr_output = ""
                if process.stderr:
                    stderr_output = process.stderr.read()
                elif hasattr(process, '_stderr_output'):
                    stderr_output = process._stderr_output
                
                self.message_queue.put(("log", f"[失败] {project_name}: 克隆失败，返回码: {process.returncode}"))
                if stderr_output:
                    self.message_queue.put(("log", f"[错误详情] {project_name}: {stderr_output.strip()}"))
                self.message_queue.put(("hide_progress", project_name))
                return False
            
            self.message_queue.put(("log", f"[成功] {project_name}: 仓库克隆完成"))
            self.message_queue.put(("update_progress", project_name, 60, "克隆完成"))
            
            # 切换分支
            if branch != "master":
                self.message_queue.put(("log", f"[切换] {project_name}: 切换到分支 {branch}"))
                self.message_queue.put(("update_progress", project_name, 80, f"切换分支..."))
                
                # 获取所有分支
                self.message_queue.put(("log", f"[切换] {project_name}: 正在获取远程分支信息..."))
                try:
                    fetch_process = subprocess.Popen(
                        ["git", "fetch", "--all"],
                        cwd=project_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    # 实时读取fetch输出
                    while True:
                        output = fetch_process.stdout.readline()
                        if output == '' and fetch_process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            if line and not line.startswith('From '):
                                self.message_queue.put(("log", f"[切换] [fetch] {line}"))
                    
                    fetch_returncode = fetch_process.wait()
                    if fetch_returncode == 0:
                        self.message_queue.put(("log", f"[切换] {project_name}: 远程分支获取完成"))
                    else:
                        self.message_queue.put(("log", f"[切换] {project_name}: 远程分支获取失败"))
                except Exception as e:
                    self.message_queue.put(("log", f"[切换] {project_name}: fetch操作出错: {str(e)}"))
                
                # 切换分支
                checkout_result = subprocess.run(
                    ["git", "checkout", branch],
                    capture_output=True, text=True, cwd=project_path
                )
                
                if checkout_result.returncode != 0:
                    # 尝试创建并切换到远程分支
                    subprocess.run(
                        ["git", "checkout", "-b", branch, f"origin/{branch}"],
                        capture_output=True, text=True, cwd=project_path
                    )
            
            self.message_queue.put(("update_progress", project_name, 100, "完成"))
            time.sleep(0.5)  # 让用户看到100%
            self.message_queue.put(("log", f"[完成] {project_name}: 下载完成 (分支: {branch})"))
            self.message_queue.put(("hide_progress", project_name))
            # 更新项目状态显示
            self.message_queue.put(("update_project_status", project_name))
            return True
            
        except Exception as e:
            self.message_queue.put(("log", f"[错误] {project_name}: 下载出错 - {str(e)}"))
            self.message_queue.put(("hide_progress", project_name))
            return False
    
    def query_branches(self, project_name):
        """查询单个项目的分支"""
        def query_task():
            try:
                self.message_queue.put(("status", f"正在查询 {project_name} 的分支..."))
                self.message_queue.put(("progress", "start"))
                
                projects = self.get_current_projects()
                repo_url = projects[project_name]
                
                # 检查是否需要认证
                query_url = repo_url
                if self.requires_auth(project_name, repo_url):
                    self.message_queue.put(("log", f"[认证] {project_name}: 分支查询需要身份认证"))
                    
                    # 获取认证凭据（在主线程中执行）
                    credentials = None
                    auth_result = [None]  # 使用列表来存储结果，以便在闭包中修改
                    
                    def get_credentials():
                        auth_result[0] = self.get_auth_credentials(project_name, repo_url)
                    
                    # 在主线程中执行认证对话框
                    self.root.after(0, get_credentials)
                    
                    # 等待认证对话框的结果
                    while auth_result[0] is None:
                        time.sleep(0.1)
                    
                    credentials = auth_result[0]
                    
                    if credentials['cancelled']:
                        self.message_queue.put(("log", f"[取消] {project_name}: 用户取消了认证"))
                        return
                    
                    if credentials['username'] and credentials['password']:
                        query_url = self.build_authenticated_url(repo_url, credentials['username'], credentials['password'])
                        self.message_queue.put(("log", f"[认证] {project_name}: 分支查询认证信息已设置"))
                    else:
                        self.message_queue.put(("log", f"[错误] {project_name}: 认证信息不完整"))
                        return
                
                result = subprocess.run(
                    ["git", "ls-remote", "--heads", query_url],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    branches = []
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            branch = line.split('\t')[1].replace('refs/heads/', '')
                            branches.append(branch)
                    
                    self.message_queue.put(("branches", project_name, branches))
                    self.message_queue.put(("log", f"[成功] {project_name} 分支查询完成，共找到 {len(branches)} 个分支"))
                else:
                    self.message_queue.put(("log", f"[失败] {project_name} 分支查询失败: {result.stderr}"))
                    
            except subprocess.TimeoutExpired:
                self.message_queue.put(("log", f"[超时] {project_name} 分支查询超时"))
            except Exception as e:
                self.message_queue.put(("log", f"[错误] {project_name} 分支查询出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=query_task, daemon=True).start()
    
    def query_all_branches(self):
        """查询所有项目的分支"""
        def query_all_task():
            try:
                projects = self.get_current_projects()
                self.message_queue.put(("log", f"[调试] 开始查询所有分支，共 {len(projects)} 个项目"))
                
                for project_name in projects.keys():
                    try:
                        self.message_queue.put(("status", f"正在查询 {project_name} 的分支..."))
                        self.message_queue.put(("log", f"[调试] 开始查询项目: {project_name}"))
                        
                        repo_url = projects[project_name]
                        
                        # 检查是否需要认证
                        query_url = repo_url
                        if self.requires_auth(project_name, repo_url):
                            self.message_queue.put(("log", f"[认证] {project_name}: 分支查询需要身份认证"))
                            
                            # 获取认证凭据（在主线程中执行）
                            credentials = None
                            auth_result = [None]  # 使用列表来存储结果，以便在闭包中修改
                            
                            def get_credentials():
                                auth_result[0] = self.get_auth_credentials(project_name, repo_url)
                            
                            # 在主线程中执行认证对话框
                            self.root.after(0, get_credentials)
                            
                            # 等待认证对话框的结果
                            while auth_result[0] is None:
                                time.sleep(0.1)
                            
                            credentials = auth_result[0]
                            
                            if credentials['cancelled']:
                                self.message_queue.put(("log", f"[取消] {project_name}: 用户取消了认证"))
                                continue
                            
                            if credentials['username'] and credentials['password']:
                                query_url = self.build_authenticated_url(repo_url, credentials['username'], credentials['password'])
                                self.message_queue.put(("log", f"[认证] {project_name}: 分支查询认证信息已设置"))
                            else:
                                self.message_queue.put(("log", f"[错误] {project_name}: 认证信息不完整"))
                                continue
                        
                        result = subprocess.run(
                            ["git", "ls-remote", "--heads", query_url],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if result.returncode == 0:
                            branches = []
                            for line in result.stdout.strip().split('\n'):
                                if line:
                                    branch = line.split('\t')[1].replace('refs/heads/', '')
                                    branches.append(branch)
                            
                            self.message_queue.put(("branches", project_name, branches))
                            self.message_queue.put(("log", f"[成功] {project_name} 分支查询完成，找到 {len(branches)} 个分支"))
                        else:
                            self.message_queue.put(("log", f"[失败] {project_name} 分支查询失败: {result.stderr}"))
                            
                    except Exception as e:
                        self.message_queue.put(("log", f"[错误] {project_name} 分支查询出错: {str(e)}"))
                
                self.message_queue.put(("log", "[调试] 所有项目分支查询循环完成，准备发送完成消息"))
                self.message_queue.put(("status", "所有分支查询完成"))
                self.message_queue.put(("log", "[调试] 完成消息已发送"))
            except Exception as e:
                self.message_queue.put(("log", f"[错误] query_all_branches 主任务出错: {str(e)}"))
                import traceback
                self.message_queue.put(("log", f"[错误] 详细错误信息: {traceback.format_exc()}"))
            finally:
                # 确保进度条停止
                self.message_queue.put(("progress", "stop"))
        
        self.progress.start()
        threading.Thread(target=query_all_task, daemon=True).start()
    
    def auto_query_branches(self):
        """启动时自动查询所有项目的分支"""
        source = self.source_var.get().upper()
        self.log_message(f">> 正在自动获取所有项目的分支信息 ({source} 源)...")
        self.query_all_branches()
    
    def query_and_detect_branches(self):
        """合并查询远程分支和本地分支"""
        def combined_query_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在查询远程分支和本地分支..."))
                self.message_queue.put(("log", "[合并查询] 开始查询远程分支和检测本地分支"))
                
                projects = self.get_current_projects()
                
                for project_name in projects.keys():
                    try:
                        project_path = os.path.join(self.save_path.get(), project_name)
                        remote_branches = []
                        local_branches = []
                        current_branch = ""
                        
                        # 1. 查询远程分支
                        self.message_queue.put(("status", f"正在查询 {project_name} 的远程分支..."))
                        repo_url = projects[project_name]
                        
                        # 检查是否需要认证
                        query_url = repo_url
                        if self.requires_auth(project_name, repo_url):
                            self.message_queue.put(("log", f"[认证] {project_name}: 分支查询需要身份认证"))
                            
                            # 获取认证凭据（在主线程中执行）
                            credentials = None
                            auth_result = [None]  # 使用列表来存储结果，以便在闭包中修改
                            
                            def get_credentials():
                                auth_result[0] = self.get_auth_credentials(project_name, repo_url)
                            
                            # 在主线程中执行认证对话框
                            self.root.after(0, get_credentials)
                            
                            # 等待认证对话框的结果
                            while auth_result[0] is None:
                                time.sleep(0.1)
                            
                            credentials = auth_result[0]
                            
                            if credentials['cancelled']:
                                self.message_queue.put(("log", f"[取消] {project_name}: 用户取消了认证"))
                                continue
                            
                            if credentials['username'] and credentials['password']:
                                query_url = self.build_authenticated_url(repo_url, credentials['username'], credentials['password'])
                                self.message_queue.put(("log", f"[认证] {project_name}: 分支查询认证信息已设置"))
                            else:
                                self.message_queue.put(("log", f"[错误] {project_name}: 认证信息不完整"))
                                continue
                        
                        result = subprocess.run(
                            ["git", "ls-remote", "--heads", query_url],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if result.returncode == 0:
                            for line in result.stdout.strip().split('\n'):
                                if line:
                                    branch = line.split('\t')[1].replace('refs/heads/', '')
                                    remote_branches.append(branch)
                        
                        # 2. 检测本地分支（如果存在）
                        if os.path.exists(project_path) and os.path.exists(os.path.join(project_path, ".git")):
                            self.message_queue.put(("status", f"正在检测 {project_name} 的本地分支..."))
                            
                            # 获取所有本地分支
                            local_result = subprocess.run(
                                ["git", "branch", "-a"],
                                capture_output=True, text=True, cwd=project_path
                            )
                            
                            # 获取当前分支
                            current_result = subprocess.run(
                                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, cwd=project_path
                            )
                            
                            if local_result.returncode == 0:
                                current_branch = current_result.stdout.strip() if current_result.returncode == 0 else ""
                                
                                for line in local_result.stdout.strip().split('\n'):
                                    if line.strip():
                                        branch = line.strip().replace('* ', '').replace('  ', '')
                                        if branch.startswith('remotes/origin/'):
                                            branch = branch.replace('remotes/origin/', '')
                                        if branch and branch != 'HEAD' and '->' not in branch:
                                            local_branches.append(branch)
                        
                        # 3. 合并远程和本地分支
                        all_branches = set()
                        all_branches.update(remote_branches)
                        all_branches.update(local_branches)
                        
                        # 移除重复项并排序
                        merged_branches = sorted(list(all_branches))
                        
                        if merged_branches:
                            # 更新分支选项
                            self.message_queue.put(("branches", project_name, merged_branches))
                            
                            # 设置当前分支（避免触发分支切换事件）
                            if current_branch and current_branch in merged_branches:
                                # 临时禁用事件绑定，避免触发分支切换
                                combo = self.branch_combos[project_name]
                                combo.unbind('<<ComboboxSelected>>')
                                
                                self.branch_vars[project_name].set(current_branch)
                                
                                # 重新绑定事件
                                combo.bind('<<ComboboxSelected>>', 
                                         lambda e, name=project_name: self.on_branch_changed(e, name))
                            
                            # 记录结果
                            remote_count = len(remote_branches)
                            local_count = len(local_branches)
                            total_count = len(merged_branches)
                            
                            self.message_queue.put(("log", f"[合并查询] {project_name} 完成"))
                            self.message_queue.put(("log", f"  - 远程分支: {remote_count} 个"))
                            self.message_queue.put(("log", f"  - 本地分支: {local_count} 个"))  
                            self.message_queue.put(("log", f"  - 合并后总计: {total_count} 个"))
                            if current_branch:
                                self.message_queue.put(("log", f"[合并查询] {project_name} 获取本地仓库当前分支..."))
                                current_result = subprocess.run(
                                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                    capture_output=True, text=True, cwd=project_path
                                )
                                
                                if current_result.returncode == 0:
                                    current_branch = current_result.stdout.strip()
                                    self.message_queue.put(("log", f"[合并查询] {project_name} 当前分支: {current_branch}"))
                                else:
                                    current_branch = None
                                    self.message_queue.put(("log", f"[合并查询] {project_name} 无法获取当前分支"))
                            
                        else:
                            self.message_queue.put(("log", f"[合并查询] {project_name} 未找到任何分支"))
                            
                    except subprocess.TimeoutExpired:
                        self.message_queue.put(("log", f"[合并查询] {project_name} 远程查询超时"))
                    except Exception as e:
                        self.message_queue.put(("log", f"[合并查询] {project_name} 查询出错: {str(e)}"))
                
                self.message_queue.put(("status", "合并查询完成"))
                self.message_queue.put(("log", "[合并查询] 所有项目的远程分支和本地分支查询完成"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[合并查询] 查询过程中出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=combined_query_task, daemon=True).start()
    
    def download_selected(self):
        """下载选中的项目（多线程并行）"""
        selected_projects = [name for name, var in self.project_vars.items() if var.get()]
        
        if not selected_projects:
            messagebox.showwarning("警告", "请至少选择一个项目进行下载")
            return
        
        def download_all_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("log", f"[开始] 准备并行下载 {len(selected_projects)} 个项目"))
                
                # 确保保存目录存在
                os.makedirs(self.save_path.get(), exist_ok=True)
                
                projects = self.get_current_projects()
                
                # 使用线程池并行下载
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {}
                    
                    for project_name in selected_projects:
                        repo_url = projects[project_name]
                        branch = self.branch_vars[project_name].get() or "master"
                        
                        future = executor.submit(
                            self.download_single_project,
                            project_name, repo_url, branch, self.save_path.get()
                        )
                        futures[future] = project_name
                    
                    # 等待所有下载完成
                    completed = 0
                    total = len(selected_projects)
                    self.message_queue.put(("status", f"[{total}] 显示本地状态..."))
                    
                    for future in concurrent.futures.as_completed(futures):
                        project_name = futures[future]
                        completed += 1
                        
                        try:
                            success = future.result()
                            status = "成功" if success else "失败"
                            self.message_queue.put(("status", f"[{completed}/{total}] {project_name} 下载{status}"))
                        except Exception as e:
                            self.message_queue.put(("log", f"[异常] {project_name} 下载异常: {str(e)}"))
                
                self.message_queue.put(("status", "所有选中项目下载完成"))
                self.message_queue.put(("log", f"[完成] 并行下载完成! 项目保存在: {self.save_path.get()}"))
                
                # 更新所有项目的状态显示
                for project_name in selected_projects:
                    self.message_queue.put(("update_project_status", project_name))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 下载过程中出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=download_all_task, daemon=True).start()
    
    def open_download_dir(self):
        """打开下载目录"""
        if os.path.exists(self.save_path.get()):
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", self.save_path.get()])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.save_path.get()])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", self.save_path.get()])
        else:
            messagebox.showwarning("警告", "下载目录不存在")
    
    def open_project_dir(self, project_name):
        """打开项目目录"""
        project_path = os.path.join(self.save_path.get(), project_name)
        if os.path.exists(project_path):
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", project_path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", project_path])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", project_path])
            self.log_message(f"已打开项目目录: {project_name}")
        else:
            messagebox.showwarning("警告", f"项目目录不存在: {project_name}")

    def open_project_with_qtcreator(self, project_name):
        """使用Qt Creator打开项目"""
        project_path = os.path.join(self.save_path.get(), project_name)
        if os.path.exists(project_path):
            try:
                # 使用qtcreator命令打开项目目录
                subprocess.Popen(["qtcreator", project_path])
                self.log_message(f"已使用Qt Creator打开项目: {project_name}")
            except FileNotFoundError:
                messagebox.showerror("错误", "未找到Qt Creator，请确保已安装Qt Creator")
                self.log_message(f"[错误] 未找到Qt Creator，无法打开项目: {project_name}")
            except Exception as e:
                messagebox.showerror("错误", f"打开项目时出错: {str(e)}")
                self.log_message(f"[错误] 使用Qt Creator打开项目失败: {project_name}, 错误: {str(e)}")
        else:
            messagebox.showwarning("警告", f"项目目录不存在: {project_name}")

    def deb_packet_generate_dir(self, project_name):
        """在目标目录打包并将产物移动到 packages 文件夹，同时通知进度条"""
        project_path = os.path.join(self.save_path.get(), project_name)
        def combined_query_task():
            if os.path.exists(project_path):
                # 1. 启动进度条
                self.message_queue.put(("progress", "start"))
                self.log_message("开始打包...")

                # 2. 执行打包命令
                try:
                    # 使用Popen实时输出打包进度
                    build_process = subprocess.Popen(
                        ["dpkg-buildpackage", "-us", "-uc", "-b"],
                        cwd=project_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,  # 将stderr重定向到stdout以便统一处理
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    # 实时读取并输出打包过程
                    while True:
                        output = build_process.stdout.readline()
                        if output == '' and build_process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            if line:
                                # 格式化不同类型的打包输出
                                if 'dpkg-buildpackage:' in line:
                                    self.message_queue.put(("log", f"[打包] [构建] {line}"))
                                elif 'dpkg-source:' in line:
                                    self.message_queue.put(("log", f"[打包] [源码] {line}"))
                                elif 'debian/rules' in line:
                                    self.message_queue.put(("log", f"[打包] [编译] {line}"))
                                elif 'dpkg-deb:' in line:
                                    self.message_queue.put(("log", f"[打包] [打包] {line}"))
                                elif 'dpkg-genchanges:' in line:
                                    self.message_queue.put(("log", f"[打包] [变更] {line}"))
                                elif 'make[' in line:
                                    self.message_queue.put(("log", f"[打包] [Make] {line}"))
                                elif line.startswith('g++') or line.startswith('gcc'):
                                    self.message_queue.put(("log", f"[打包] [编译] {line}"))
                                elif '编译' in line or 'compiling' in line.lower():
                                    self.message_queue.put(("log", f"[打包] [编译] {line}"))
                                elif '链接' in line or 'linking' in line.lower():
                                    self.message_queue.put(("log", f"[打包] [链接] {line}"))
                                elif 'warning:' in line.lower():
                                    self.message_queue.put(("log", f"[打包] [警告] {line}"))
                                elif 'error:' in line.lower():
                                    self.message_queue.put(("log", f"[打包] [错误] {line}"))
                                else:
                                    self.message_queue.put(("log", f"[打包] {line}"))
                    
                    # 等待进程完成并获取返回码
                    build_returncode = build_process.wait()
                    
                    if build_returncode != 0:
                        self.message_queue.put(("progress", "stop"))
                        self.message_queue.put(("log", f"[打包] [失败] 打包失败，返回码: {build_returncode}"))
                        messagebox.showerror("打包失败", f"打包过程失败，返回码: {build_returncode}")
                        return
                    
                    self.message_queue.put(("log", f"[打包] [成功] 打包完成: {project_name}"))
                    
                except Exception as e:
                    self.message_queue.put(("progress", "stop"))
                    self.message_queue.put(("log", f"[打包] [异常] 打包过程出错: {str(e)}"))
                    messagebox.showerror("打包异常", str(e))
                    return

                # 3. 停止进度条（打包成功）
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("log", f"[打包] [完成] 打包流程结束，正在处理文件..."))

                # 4. 新建 packages 文件夹（在项目目录的上一级目录）
                parent_dir = os.path.dirname(project_path)
                packages_dir = os.path.join(parent_dir, "packages")
                os.makedirs(packages_dir, exist_ok=True)

                # 4. 移动 .deb 文件（一般在项目目录的上一级）
                deb_files = glob.glob(os.path.join(parent_dir, "*.deb"))
                if not deb_files:
                    self.log_message("未找到 .deb 文件")
                else:
                    for deb_file in deb_files:
                        try:
                            shutil.move(deb_file, packages_dir)
                            self.log_message(f"已移动: {os.path.basename(deb_file)} 到 packages/")
                        except Exception as e:
                            self.log_message(f"移动文件失败: {deb_file}，原因: {e}")

                # 5. 打开 packages 文件夹（在上一级目录）
                subprocess.Popen(["xdg-open", packages_dir])
                self.log_message(f"已打开 packages 目录: {packages_dir}")

            else:
                messagebox.showwarning("警告", f"项目目录不存在: {project_name}")
                
        threading.Thread(target=combined_query_task, daemon=True).start()
        

    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                
                if message[0] == "log":
                    self.log_message(message[1])
                elif message[0] == "status":
                    self.status_var.set(message[1])
                elif message[0] == "progress":
                    if message[1] == "start":
                        self.progress.start()
                    else:
                        self.progress.stop()
                elif message[0] == "show_progress":
                    if len(message) == 3:
                        self.show_progress(message[1], message[2])
                    else:
                        self.show_progress(message[1])
                elif message[0] == "hide_progress":
                    self.hide_progress(message[1])
                elif message[0] == "update_progress":
                    self.update_progress(message[1], message[2], message[3])
                elif message[0] == "cancel_branch":
                    self.cancel_branch_switch(message[1], message[2])
                elif message[0] == "enable_controls":
                    self.set_project_controls_enabled(message[1])
                elif message[0] == "branches":
                    project_name, branches = message[1], message[2]
                    combo = self.branch_combos[project_name]
                    
                    # 获取当前分支选择框的值
                    current_selection = combo.get()
                    
                    # 更新分支选项
                    combo['values'] = branches
                    
                    # 智能设置默认分支
                    if branches:
                        # 首先检查是否有保存的分支配置
                        saved_branch = None
                        if hasattr(self, 'saved_branches') and project_name in self.saved_branches:
                            saved_branch = self.saved_branches[project_name]
                        
                        # 优先级：保存的配置 > 当前选择 > 默认分支
                        # 临时禁用事件绑定，避免触发分支切换
                        combo.unbind('<<ComboboxSelected>>')
                        
                        if saved_branch and saved_branch in branches:
                            combo.set(saved_branch)
                            self.branch_vars[project_name].set(saved_branch)
                        elif current_selection and current_selection in branches:
                            combo.set(current_selection)
                        elif 'master' in branches:
                            combo.set('master')
                        elif 'main' in branches:
                            combo.set('main')
                        elif 'develop' in branches:
                            combo.set('develop')
                        else:
                            combo.set(branches[0])
                        
                        # 重新绑定事件
                        combo.bind('<<ComboboxSelected>>', 
                                 lambda e, name=project_name: self.on_branch_changed(e, name))
                elif message[0] == "save_config":
                    self.save_config()
                elif message[0] == "package_status":
                    package_name, status, color = message[1], message[2], message[3]
                    if package_name in self.package_status_labels:
                        label = self.package_status_labels[package_name]
                        label.config(text=status, foreground=color)
                elif message[0] == "update_project_status":
                    project_name = message[1]
                    self.update_project_status(project_name)
                elif message[0] == "host_content":
                    content = message[1]
                    self.host_text.delete(1.0, tk.END)
                    self.host_text.insert(1.0, content)
                elif message[0] == "host_status":
                    status = message[1]
                    if status == "文件不存在":
                        self.host_file_label.config(text="/etc/hosts (文件不存在)", foreground="red")
                    elif status == "权限不足":
                        self.host_file_label.config(text="/etc/hosts (权限不足)", foreground="orange")
                    elif status == "读取错误":
                        self.host_file_label.config(text="/etc/hosts (读取错误)", foreground="orange")
                    else:
                        self.host_file_label.config(text="/etc/hosts", foreground="black")
                elif message[0] == "ping_status":
                    status = message[1]
                    if status == "running":
                        self.ping_btn.config(state=tk.DISABLED)
                        self.stop_ping_btn.config(state=tk.NORMAL)
                    else:
                        self.ping_btn.config(state=tk.NORMAL)
                        self.stop_ping_btn.config(state=tk.DISABLED)
                elif message[0] == "ping_result":
                    result_text = message[1]
                    self.ping_result_text.insert(tk.END, result_text)
                    self.ping_result_text.see(tk.END)  # 自动滚动到底部
                elif message[0] == "sshfs_status":
                    status = message[1]
                    self.sshfs_status_var.set(status)
                elif message[0] == "sshfs_title":
                    title = message[1]
                    self.sshfs_title_var.set(title)
                        
        except queue.Empty:
            pass
        
        # 每100ms检查一次消息队列
        self.root.after(100, self.process_queue)

    def create_host_management(self, parent):
        """创建Host管理界面"""
        # 主容器
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置主容器权重
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # 按钮区域
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # 保存按钮
        self.save_host_btn = ttk.Button(button_frame, text="保存Host配置", command=self.save_host_config, style='Success.TButton')
        self.save_host_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清理github.com条目按钮
        self.cleanup_github_btn = ttk.Button(button_frame, text="清理GitHub条目", command=self.cleanup_github_entry, style='Warning.TButton')
        self.cleanup_github_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重新加载按钮
        self.reload_host_btn = ttk.Button(button_frame, text="重新加载", command=self.reload_hosts, style='Primary.TButton')
        self.reload_host_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 备份当前配置按钮
        self.backup_host_btn = ttk.Button(button_frame, text="备份当前配置", command=self.backup_hosts, style='Primary.TButton')
        self.backup_host_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建Notebook用于多tab切换
        self.host_notebook = ttk.Notebook(main_container)
        self.host_notebook.grid(row=1, column=0, sticky="nsew")
        
        # 初始化变量
        self.ping_process = None
        self.host_file_path = "/etc/hosts"
        self.host_editors = {}  # 存储编辑器引用
        
        # 创建Host配置tab
        self.create_host_config_tab()
        
        # 创建Ping工具tab
        self.create_ping_tool_tab()
        
        # 启动时检查hosts文件
        self.root.after(500, self.check_and_load_hosts)

    def create_host_config_tab(self):
        """创建Host配置tab"""
        # 创建Host配置tab
        host_config_tab = ttk.Frame(self.host_notebook)
        self.host_notebook.add(host_config_tab, text="Host配置")
        host_config_tab.columnconfigure(0, weight=1)
        host_config_tab.rowconfigure(0, weight=1)
        
        # 文件路径标签
        self.host_file_label = ttk.Label(host_config_tab, text="/etc/hosts", font=("", 9, "bold"))
        self.host_file_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # 文本编辑框
        self.host_text = scrolledtext.ScrolledText(host_config_tab, wrap=tk.WORD, height=20)
        self.host_text.grid(row=1, column=0, sticky="nsew")
        
        # 存储编辑器引用
        self.host_editors["/etc/hosts"] = self.host_text

    def create_ping_tool_tab(self):
        """创建Ping工具tab"""
        # 创建Ping工具tab
        ping_tab = ttk.Frame(self.host_notebook)
        self.host_notebook.add(ping_tab, text="Ping工具")
        ping_tab.columnconfigure(0, weight=1)
        ping_tab.rowconfigure(1, weight=1)
        
        # Ping工具控制区域
        ping_control_frame = ttk.LabelFrame(ping_tab, text="Ping控制")
        ping_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # IP地址输入
        ttk.Label(ping_control_frame, text="IP地址:").pack(side=tk.LEFT, padx=(5, 2))
        self.ping_ip_var = tk.StringVar(value="8.8.8.8")
        ping_ip_entry = ttk.Entry(ping_control_frame, textvariable=self.ping_ip_var, width=15)
        ping_ip_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Ping按钮
        self.ping_btn = ttk.Button(ping_control_frame, text="开始Ping", command=self.start_ping, style='Success.TButton')
        self.ping_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 停止Ping按钮
        self.stop_ping_btn = ttk.Button(ping_control_frame, text="停止Ping", command=self.stop_ping, state=tk.DISABLED, style='Danger.TButton')
        self.stop_ping_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Ping结果显示区域
        ping_result_frame = ttk.LabelFrame(ping_tab, text="Ping结果")
        ping_result_frame.grid(row=1, column=0, sticky="nsew")
        ping_result_frame.columnconfigure(0, weight=1)
        ping_result_frame.rowconfigure(0, weight=1)
        
        # Ping结果文本框
        self.ping_result_text = scrolledtext.ScrolledText(ping_result_frame, wrap=tk.WORD, height=15)
        self.ping_result_text.grid(row=0, column=0, sticky="nsew")

    def check_and_load_hosts(self):
        """检查并加载hosts文件"""
        def check_task():
            try:
                self.message_queue.put(("log", "[Host] 正在检查hosts文件..."))
                
                if not os.path.exists(self.host_file_path):
                    self.message_queue.put(("log", "[Host] hosts文件不存在"))
                    self.message_queue.put(("host_status", "文件不存在"))
                    return
                
                # 读取hosts文件内容
                try:
                    with open(self.host_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查是否包含github.com条目
                    github_entry = "140.82.112.4 github.com"
                    if github_entry not in content:
                        self.message_queue.put(("log", "[Host] 未找到github.com条目，将在文件末尾添加"))
                        content += f"\n\n{github_entry}\n"
                        
                        # 使用pkexec添加条目
                        add_cmd = ["pkexec", "sh", "-c", f"echo '{github_entry}' >> {self.host_file_path}"]
                        result = subprocess.run(add_cmd, capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            self.message_queue.put(("log", "[Host] 已添加github.com条目到hosts文件"))
                            # 重新读取文件内容
                            with open(self.host_file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        else:
                            if "cancelled" in result.stderr.lower():
                                self.message_queue.put(("log", "[Host] 用户取消了添加github.com条目的权限授权"))
                            else:
                                self.message_queue.put(("log", f"[Host] 添加github.com条目失败: {result.stderr}"))
                    else:
                        self.message_queue.put(("log", "[Host] hosts文件中已存在github.com条目"))
                    
                    self.message_queue.put(("host_content", content))
                    self.message_queue.put(("host_status", "文件正常"))
                    
                except PermissionError:
                    self.message_queue.put(("log", "[Host] 没有权限读取hosts文件"))
                    self.message_queue.put(("host_status", "权限不足"))
                except Exception as e:
                    self.message_queue.put(("log", f"[Host] 读取hosts文件时出错: {str(e)}"))
                    self.message_queue.put(("host_status", "读取错误"))
                    
            except Exception as e:
                self.message_queue.put(("log", f"[Host] 检查hosts文件时出错: {str(e)}"))
        
        threading.Thread(target=check_task, daemon=True).start()

    def save_host_config(self):
        """保存hosts配置"""
        def save_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在保存hosts配置..."))
                self.message_queue.put(("log", "[Host] [开始] 开始保存hosts配置"))
                
                # 获取编辑器内容
                content = self.host_text.get(1.0, tk.END).rstrip('\n')
                
                # 创建临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as temp_file:
                    temp_file.write(content)
                    temp_path = temp_file.name
                
                # 使用pkexec复制文件
                copy_cmd = ["pkexec", "cp", temp_path, self.host_file_path]
                result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=30)
                
                # 清理临时文件
                os.unlink(temp_path)
                
                if result.returncode == 0:
                    self.message_queue.put(("log", "[Host] [成功] hosts配置已保存"))
                else:
                    if "cancelled" in result.stderr.lower():
                        self.message_queue.put(("log", "[Host] [取消] 用户取消了权限授权"))
                    else:
                        self.message_queue.put(("log", f"[Host] [失败] 保存hosts配置失败: {result.stderr}"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[Host] [错误] 保存hosts配置时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "hosts配置操作完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认保存Hosts配置",
            "此操作将保存hosts文件配置。\n\n"
            "[注意] 错误的hosts配置可能影响网络连接！\n\n"
            "是否继续？",
            icon="warning"
        )
        
        if response:
            threading.Thread(target=save_task, daemon=True).start()

    def reload_hosts(self):
        """重新加载hosts文件"""
        def reload_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在重新加载hosts文件..."))
                self.message_queue.put(("log", "[Host] [开始] 重新加载hosts文件"))
                
                if not os.path.exists(self.host_file_path):
                    self.message_queue.put(("log", "[Host] [失败] hosts文件不存在"))
                    self.message_queue.put(("host_status", "文件不存在"))
                    return
                
                # 读取hosts文件内容
                try:
                    with open(self.host_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.message_queue.put(("host_content", content))
                    self.message_queue.put(("host_status", "文件正常"))
                    self.message_queue.put(("log", "[Host] [成功] hosts文件重新加载完成"))
                    
                except PermissionError:
                    self.message_queue.put(("log", "[Host] [失败] 没有权限读取hosts文件"))
                    self.message_queue.put(("host_status", "权限不足"))
                except Exception as e:
                    self.message_queue.put(("log", f"[Host] [失败] 读取hosts文件时出错: {str(e)}"))
                    self.message_queue.put(("host_status", "读取错误"))
                    
            except Exception as e:
                self.message_queue.put(("log", f"[Host] [错误] 重新加载hosts文件时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "hosts文件重新加载完成"))
        
        threading.Thread(target=reload_task, daemon=True).start()

    def backup_hosts(self):
        """备份当前hosts配置"""
        def backup_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在备份hosts配置..."))
                self.message_queue.put(("log", "[Host] [开始] 备份hosts配置"))
                
                if not os.path.exists(self.host_file_path):
                    self.message_queue.put(("log", "[Host] [失败] hosts文件不存在，无法备份"))
                    return
                
                # 创建备份目录
                import tempfile
                backup_dir = tempfile.mkdtemp(prefix="hosts_backup_")
                
                # 复制hosts文件到备份目录
                backup_cmd = ["pkexec", "cp", self.host_file_path, backup_dir]
                result = subprocess.run(backup_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    backup_path = os.path.join(backup_dir, "hosts")
                    self.message_queue.put(("log", f"[Host] [成功] hosts配置已备份到: {backup_path}"))
                else:
                    if "cancelled" in result.stderr.lower():
                        self.message_queue.put(("log", "[Host] [取消] 用户取消了备份权限授权"))
                    else:
                        self.message_queue.put(("log", f"[Host] [失败] 备份hosts配置失败: {result.stderr}"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[Host] [错误] 备份hosts配置时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "hosts配置备份完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认备份Hosts配置",
            "此操作将备份当前的hosts文件配置。\n\n"
            "是否继续？",
            icon="info"
        )
        
        if response:
            threading.Thread(target=backup_task, daemon=True).start()

    def start_ping(self):
        """开始ping操作"""
        ip = self.ping_ip_var.get().strip()
        if not ip:
            messagebox.showwarning("警告", "请输入IP地址")
            return

        self.ping_result_text.delete(1.0, tk.END)
        self.status_var.set("Ping结果 日志已清空")
        
        def ping_task():
            try:
                self.message_queue.put(("ping_result", f"[{self.get_current_time()}] 开始ping {ip}...\n"))
                self.message_queue.put(("ping_status", "running"))
                
                # 启动ping进程
                self.ping_process = subprocess.Popen(
                    ["ping", "-c", "1000", ip],  # 设置较大的次数，通过停止按钮控制
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 实时读取输出
                while self.ping_process and self.ping_process.poll() is None:
                    output = self.ping_process.stdout.readline()
                    if output:
                        line = output.strip()
                        if line:
                            self.message_queue.put(("ping_result", f"{line}\n"))
                    else:
                        break
                
                # 读取剩余输出
                remaining_output = self.ping_process.stdout.read()
                if remaining_output:
                    for line in remaining_output.strip().split('\n'):
                        if line:
                            self.message_queue.put(("ping_result", f"{line}\n"))
                
                if self.ping_process:
                    returncode = self.ping_process.wait()
                    if returncode == 0:
                        self.message_queue.put(("ping_result", f"[{self.get_current_time()}] ping {ip} 完成\n"))
                    else:
                        self.message_queue.put(("ping_result", f"[{self.get_current_time()}] ping {ip} 失败，返回码: {returncode}\n"))
                
            except Exception as e:
                self.message_queue.put(("ping_result", f"[{self.get_current_time()}] ping操作出错: {str(e)}\n"))
            finally:
                self.message_queue.put(("ping_status", "stopped"))
                self.ping_process = None
        
        threading.Thread(target=ping_task, daemon=True).start()

    def stop_ping(self):
        """停止ping操作"""
        if self.ping_process:
            try:
                self.ping_process.terminate()
                self.message_queue.put(("ping_result", f"[{self.get_current_time()}] 正在停止ping操作...\n"))
            except Exception as e:
                self.message_queue.put(("ping_result", f"[{self.get_current_time()}] 停止ping操作时出错: {str(e)}\n"))

    def cleanup_github_entry(self):
        """手动清理hosts文件中的github.com条目"""
        def cleanup_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在清理GitHub条目..."))
                self.message_queue.put(("log", "[Host] [开始] 开始清理GitHub条目"))
                
                if not os.path.exists(self.host_file_path):
                    self.message_queue.put(("log", "[Host] [失败] hosts文件不存在"))
                    return
                
                # 读取当前内容
                try:
                    with open(self.host_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except PermissionError:
                    self.message_queue.put(("log", "[Host] [失败] 没有权限读取hosts文件"))
                    return
                except Exception as e:
                    self.message_queue.put(("log", f"[Host] [失败] 读取hosts文件时出错: {str(e)}"))
                    return
                
                # 移除github.com条目
                github_entry = "140.82.112.4 github.com"
                if github_entry in content:
                    # 创建临时文件
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as temp_file:
                        # 移除github.com条目
                        lines = content.split('\n')
                        filtered_lines = [line for line in lines if line.strip() != github_entry.strip()]
                        temp_file.write('\n'.join(filtered_lines))
                        temp_path = temp_file.name
                    
                    # 使用pkexec复制文件
                    copy_cmd = ["pkexec", "cp", temp_path, self.host_file_path]
                    result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=30)
                    
                    # 清理临时文件
                    os.unlink(temp_path)
                    
                    if result.returncode == 0:
                        self.message_queue.put(("log", "[Host] [成功] GitHub条目已清理"))
                        # 重新加载文件内容到编辑器
                        try:
                            with open(self.host_file_path, 'r', encoding='utf-8') as f:
                                new_content = f.read()
                            self.message_queue.put(("host_content", new_content))
                        except Exception as e:
                            self.message_queue.put(("log", f"[Host] [警告] 重新加载文件内容失败: {str(e)}"))
                    else:
                        if "cancelled" in result.stderr.lower():
                            self.message_queue.put(("log", "[Host] [取消] 用户取消了权限授权"))
                        else:
                            self.message_queue.put(("log", f"[Host] [失败] 清理GitHub条目失败: {result.stderr}"))
                else:
                    self.message_queue.put(("log", "[Host] [信息] hosts文件中未找到GitHub条目"))
                    
            except Exception as e:
                self.message_queue.put(("log", f"[Host] [错误] 清理GitHub条目时出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
                self.message_queue.put(("status", "GitHub条目清理完成"))
        
        # 确认对话框
        response = messagebox.askyesno(
            "确认清理GitHub条目",
            "此操作将从hosts文件中移除 '140.82.112.4 github.com' 条目。\n\n"
            "是否继续？",
            icon="warning"
        )
        
        if response:
            threading.Thread(target=cleanup_task, daemon=True).start()

    def get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def cleanup_hosts_on_exit(self):
        """退出时清理hosts文件中的github.com条目（已废弃）"""
        # 此方法已废弃，改为手动按钮触发
        pass

    def on_closing(self):
        """程序退出时的清理操作"""
        try:
            # 停止ping进程
            if hasattr(self, 'ping_process') and self.ping_process:
                self.ping_process.terminate()
            
            # 不再自动清理hosts文件中的github.com条目
            # 用户需要手动点击"清理GitHub条目"按钮
            
        except Exception as e:
            # 静默处理，避免影响程序退出
            pass
        
        # 销毁窗口
        self.root.destroy()

def main():
    # 检查Git是否可用
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showerror("错误", "未找到Git命令，请先安装Git")
        return
    
    root = tk.Tk()
    app = DeepinProjectDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
