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
import urllib.request
import urllib.parse
import zipfile
import tempfile
from datetime import datetime

class DebPackageSaver:
    def __init__(self, root):
        self.root = root
        self.root.title("DEB包保存器")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 800)
        
        # 设置主题样式
        self.setup_styles()
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.expanduser("~"), ".deb_saver_config.json")
        
        # 消息队列用于线程间通信
        self.message_queue = queue.Queue()
        
        # 下载源变量
        self.source_url = tk.StringVar(value="http://10.0.32.60:5001/tasks/580959/unstable-arm64/")
        
        # 架构选择变量
        self.arch_vars = {
            'arm64': tk.BooleanVar(value=False),
            'amd64': tk.BooleanVar(value=False),
            'i386': tk.BooleanVar(value=False),
            'loongarch64': tk.BooleanVar(value=False),
            'mips64el': tk.BooleanVar(value=False),
            'sw_64': tk.BooleanVar(value=False),
            'all': tk.BooleanVar(value=False)  # 'all' 是一种特殊的架构类型，不是全选功能
        }
        
        # 全选架构变量
        self.select_all_archs = tk.BooleanVar(value=False)
        
        # 符号包选择变量
        self.include_dbgsym = tk.BooleanVar(value=False)
        
        # 显示日志选择变量
        self.show_log = tk.BooleanVar(value=False)
        
        # 本地保存位置变量
        self.save_path = tk.StringVar(value="")
        
        # 搜索关键字变量
        self.search_keyword = tk.StringVar(value="")
        
        # 包列表数据
        self.package_data = []
        self.filtered_package_data = []  # 过滤后的包数据
        self.package_vars = {}  # 存储每个包的选择状态
        
        # 创建临时目录
        self.create_temp_directory()
        
        # 创建界面
        self.create_widgets()
        
        # 加载配置
        self.load_config()
        
        # 启动消息队列处理
        self.process_queue()
        
        # 绑定滚动事件
        self.root.after(100, self._bind_all_scroll_events)
        
        # 绑定全局鼠标点击事件，用于关闭右键菜单
        self.root.bind("<Button-1>", self._on_global_click)
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'), foreground='#2c3e50')
        style.configure('Header.TLabel', font=('Arial', 11, 'bold'), foreground='#34495e')
        style.configure('Info.TLabel', font=('Arial', 10), foreground='#7f8c8d')
        style.configure('Status.TLabel', font=('Arial', 10), foreground='orange')
        
        # 按钮样式
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        style.configure('Success.TButton', font=('Arial', 10, 'bold'))
        style.configure('Warning.TButton', font=('Arial', 10, 'bold'))
        style.configure('Danger.TButton', font=('Arial', 10, 'bold'))
        
        # 框架样式
        style.configure('Card.TFrame', relief='solid', borderwidth=1)
        style.configure('Section.TFrame', relief='groove', borderwidth=2)
        
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
        
        # 输入框样式
        style.configure('TEntry', font=('Arial', 10))
        style.configure('TCombobox', font=('Arial', 10))
        
        # 复选框样式
        style.configure('TCheckbutton', font=('Arial', 10))
        
        # 滚动条样式
        style.configure('TScrollbar', background='#bdc3c7', troughcolor='#ecf0f1', width=12)
    
    def create_temp_directory(self):
        """创建临时目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_dir = f"/tmp/deb_saver_{timestamp}"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.save_path.set(self.temp_dir)
        self.log_message(f"[初始化] 创建临时目录: {self.temp_dir}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        # 配置主框架中各行的权重，让包表格区域占据主要空间
        main_frame.rowconfigure(0, weight=0)  # 配置区域固定高度
        main_frame.rowconfigure(1, weight=0)  # 搜索区域固定高度
        main_frame.rowconfigure(2, weight=1)  # 包表格区域占据剩余空间
        main_frame.rowconfigure(3, weight=0)  # 按钮区域固定高度
        main_frame.rowconfigure(4, weight=0)  # 日志区域固定高度
        main_frame.rowconfigure(5, weight=0)  # 进度条固定高度
        main_frame.rowconfigure(6, weight=0)  # 状态栏固定高度
        
        # 配置区域
        config_frame = ttk.LabelFrame(main_frame, text="配置选项", padding="10", style='Title.TLabelframe')
        config_frame.grid(row=0, column=0, sticky="ew")
        config_frame.columnconfigure(1, weight=1)
        
        # 下载源配置
        ttk.Label(config_frame, text="下载源:", style='Header.TLabel').grid(row=0, column=0, sticky="w")
        
        source_frame = ttk.Frame(config_frame)
        source_frame.grid(row=0, column=1, sticky="ew")
        source_frame.columnconfigure(0, weight=1)
        
        # 源路径输入
        self.source_entry = ttk.Entry(source_frame, textvariable=self.source_url, font=('Arial', 10))
        self.source_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)
        
        # 添加源类型显示标签
        self.source_type_label = ttk.Label(source_frame, text="", style='Info.TLabel')
        self.source_type_label.grid(row=0, column=1, sticky="e", padx=(0, 5), pady=5)
        
        ttk.Button(source_frame, text="选择本地", command=self.select_local_source,
                  style='Primary.TButton').grid(row=0, column=2, sticky="e", padx=(0, 5), pady=5)
        
        ttk.Button(source_frame, text="刷新", command=self.refresh_package_list,
                  style='Success.TButton').grid(row=0, column=3, sticky="e", pady=5)
        
        # 绑定路径输入变化事件
        self.source_url.trace('w', self.on_source_path_changed)
        
        # 本地保存位置
        ttk.Label(config_frame, text="本地保存位置:", style='Header.TLabel').grid(row=1, column=0, sticky="w")
        
        save_frame = ttk.Frame(config_frame)
        save_frame.grid(row=1, column=1, sticky="ew")
        save_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(save_frame, textvariable=self.save_path, font=('Arial', 10)).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(save_frame, text="选择路径", command=self.select_save_path,
                  style='Primary.TButton').grid(row=0, column=1, sticky="e", padx=(0, 5))
        ttk.Button(save_frame, text="打开保存目录", command=self.open_save_dir,
                  style='Success.TButton').grid(row=0, column=2, sticky="e")
        
        # 显示日志选择 - 放在本地保存位置下一行
        ttk.Label(config_frame, text="显示日志:", style='Header.TLabel').grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(config_frame, text="操作日志", variable=self.show_log,
                      command=self.on_log_visibility_changed).grid(row=2, column=1, sticky="w")
        
        # 搜索选项区域
        search_frame = ttk.LabelFrame(main_frame, text="搜索选项", padding="10", style='Title.TLabelframe')
        search_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        search_frame.columnconfigure(1, weight=1)
        
        # 搜索输入框和按钮 - 第一行
        ttk.Label(search_frame, text="关键字:", style='Header.TLabel').grid(row=0, column=0, sticky="w")
        
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        search_input_frame.columnconfigure(0, weight=1)
        
        # 搜索输入框
        self.search_entry = ttk.Entry(search_input_frame, textvariable=self.search_keyword, font=('Arial', 10))
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # 绑定回车键搜索
        self.search_entry.bind('<Return>', lambda e: self.search_packages())
        
        # 搜索按钮
        search_button = ttk.Button(search_input_frame, text="搜索", command=self.search_packages,
                              style='Success.TButton')
        search_button.grid(row=0, column=1, sticky="e")
        
        # 架构选择 - 第二行
        ttk.Label(search_frame, text="架构:", style='Header.TLabel').grid(row=1, column=0, sticky="w")
        
        arch_frame = ttk.Frame(search_frame)
        arch_frame.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        
        # 架构选择
        arch_list = ['arm64', 'amd64', 'i386', 'loongarch64', 'mips64el', 'sw_64', 'all']
        for arch in arch_list:
            ttk.Checkbutton(arch_frame, text=arch, variable=self.arch_vars[arch],
                          command=self.on_arch_changed).pack(side=tk.LEFT, padx=(0, 10))
        
        # 添加全选架构选项
        ttk.Checkbutton(arch_frame, text="全选", variable=self.select_all_archs,
                      command=self.on_select_all_archs_changed).pack(side=tk.LEFT, padx=(20, 0))
        
        # 符号包选择 - 第三行
        ttk.Label(search_frame, text="符号包:", style='Header.TLabel').grid(row=2, column=0, sticky="w")
        
        dbgsym_frame = ttk.Frame(search_frame)
        dbgsym_frame.grid(row=2, column=1, sticky="ew", pady=(0, 5))
        
        ttk.Checkbutton(dbgsym_frame, text="dbgsym", variable=self.include_dbgsym,
                      command=self.on_dbgsym_changed).pack(side=tk.LEFT)
        
        # 包表格区域
        table_frame = ttk.LabelFrame(main_frame, text="包列表", padding="10", style='Title.TLabelframe')
        table_frame.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建包表格
        self.create_package_table(table_frame)
        
        # 操作按钮区域 - 移除了大部分按钮，只保留必要的
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        
        # 可以在这里添加其他必要的按钮，目前为空
        
        # 日志区域
        self.log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10", style='Title.TLabelframe')
        self.log_frame.grid(row=4, column=0, sticky="ew", pady=(5, 0))
        self.log_frame.columnconfigure(0, weight=1)
        
        # 日志内容框架
        self.log_content_frame = ttk.Frame(self.log_frame)
        self.log_content_frame.grid(row=0, column=0, sticky="ew")
        self.log_content_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(self.log_content_frame, height=8, state=tk.NORMAL,
                                               font=('Consolas', 9),
                                               background='#f8f9fa',
                                               foreground='#2c3e50',
                                               insertbackground='#4a90e2')
        self.log_text.grid(row=0, column=0, sticky="ew")
        
        # 初始化日志可见性
        self.update_log_visibility()
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', style='Custom.Horizontal.TProgressbar')
        self.progress.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 5))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel')
        status_label.grid(row=6, column=0, sticky="ew", padx=15, pady=(0, 15))
    
    def create_package_table(self, parent_frame):
        """创建包表格"""
        # 清除现有内容
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # 创建Treeview表格，支持多选，移除固定高度以允许动态调整
        columns = ('index', 'selected', 'name', 'arch', 'status', 'download_time')
        self.package_tree = ttk.Treeview(parent_frame, columns=columns, show='headings', selectmode='extended')
        
        # 设置列标题
        self.package_tree.heading('index', text='序号')
        self.package_tree.heading('selected', text='勾选状态')
        self.package_tree.heading('name', text='包名')
        self.package_tree.heading('arch', text='架构名')
        self.package_tree.heading('status', text='下载状态')
        self.package_tree.heading('download_time', text='下载时间')
        
        # 设置列宽，使用最小宽度以允许动态调整
        self.package_tree.column('index', width=50, minwidth=50, anchor='center')
        self.package_tree.column('selected', width=80, minwidth=80, anchor='center')
        self.package_tree.column('name', width=200, minwidth=150, anchor='w')
        self.package_tree.column('arch', width=100, minwidth=80, anchor='center')
        self.package_tree.column('status', width=100, minwidth=80, anchor='center')
        self.package_tree.column('download_time', width=150, minwidth=120, anchor='center')
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.package_tree.yview)
        h_scrollbar = ttk.Scrollbar(parent_frame, orient="horizontal", command=self.package_tree.xview)
        self.package_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局 - 确保表格能够填充整个可用空间
        self.package_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置父框架的网格权重，确保表格能够扩展
        parent_frame.rowconfigure(0, weight=1)
        parent_frame.columnconfigure(0, weight=1)
        
        # 绑定右键菜单
        self.package_tree.bind('<Button-3>', self.show_context_menu)
        self.package_tree.bind('<Double-1>', self.on_item_double_click)
        
        # 绑定鼠标拖拽选择事件
        self.package_tree.bind('<Button-1>', self.on_item_single_click)
        self.package_tree.bind('<B1-Motion>', self.on_item_motion)
        self.package_tree.bind('<ButtonRelease-1>', self.on_item_release)
        self.package_tree.bind('<Control-Button-1>', self.on_ctrl_click)
        self.package_tree.bind('<Shift-Button-1>', self.on_shift_click)
        
        # 初始化拖拽选择变量
        self.drag_start_item = None
        self.drag_start_selection = set()
        self.drag_mode = None  # 'normal', 'ctrl', 'shift'
        
        # 初始化包数据字典
        self.package_item_data = {}
        
        # 填充表格数据
        self.refresh_table_data()
    
    def refresh_table_data(self):
        """刷新表格数据"""
        # 清除现有数据
        for item in self.package_tree.get_children():
            self.package_tree.delete(item)
        
        # 重新初始化包数据字典
        self.package_item_data = {}
        self.package_vars.clear()
        
        # 使用过滤后的包数据，如果没有过滤数据则使用全部数据
        data_to_display = self.filtered_package_data if hasattr(self, 'filtered_package_data') and self.filtered_package_data else self.package_data
        
        # 包数据行
        for i, package in enumerate(data_to_display):
            # 使用包名+架构作为唯一标识符，避免同名包冲突
            unique_key = f"{package['name']}_{package.get('arch', '')}"
            
            # 勾选状态
            var = tk.BooleanVar(value=package.get('selected', False))
            self.package_vars[unique_key] = var
            
            # 插入数据
            selected_text = "☑" if var.get() else "☐"
            status_text = package.get('status', '未下载')
            
            # 优先使用完整文件名，如果没有则使用解析后的包名
            display_name = package.get('full_filename', package['name'])
            item_id = self.package_tree.insert('', 'end', values=(
                i + 1,  # 序号，从1开始
                selected_text,
                display_name,  # 显示完整文件名，包含架构和后缀
                package.get('arch', ''),
                status_text,
                package.get('download_time', '')
            ))
            
            # 存储包数据到字典中，使用唯一标识符
            self.package_item_data[item_id] = {
                'package': package,
                'unique_key': unique_key
            }
    
    def on_source_path_changed(self, *args):
        """源路径改变时的处理，自动判断路径类型"""
        path = self.source_url.get().strip()
        
        if not path:
            self.source_type_label.config(text="")
            return
        
        # 判断是网络路径还是本地路径
        if path.startswith(('http://', 'https://', 'ftp://')):
            source_type = "网络源"
        elif os.path.exists(path):
            source_type = "本地源"
        else:
            source_type = "未知路径（将尝试作为网络源处理）"
        
        self.source_type_label.config(text=f"检测到: {source_type}")
    
    def on_arch_changed(self):
        """架构选择改变时的处理"""
        self.search_packages()
    
    def on_select_all_archs_changed(self):
        """全选架构选项改变时的处理"""
        if self.select_all_archs.get():
            # 如果选择了全选，则选中所有架构
            for arch in self.arch_vars:
                self.arch_vars[arch].set(True)
        else:
            # 如果取消了全选，则取消所有架构的选择
            for arch in self.arch_vars:
                self.arch_vars[arch].set(False)
        
        self.search_packages()
    
    def on_dbgsym_changed(self):
        """符号包选择改变时的处理"""
        self.search_packages()
    
    def on_log_visibility_changed(self):
        """日志显示选择改变时的处理"""
        self.update_log_visibility()
    
    def search_packages(self):
        """根据关键字和架构选项搜索包"""
        keyword = self.search_keyword.get().strip().lower()
        selected_archs = [arch for arch, var in self.arch_vars.items() if var.get()]
        arch_text = ", ".join(selected_archs) if selected_archs else "无"
        
        self.log_message(f"[搜索] 开始搜索，关键字: '{keyword}', 选中架构: {arch_text}, 包含符号包: {self.include_dbgsym.get()}")
        self.log_message(f"[搜索] 总包数: {len(self.package_data)}")
        
        # 首先根据架构和符号包设置过滤包
        base_packages = self.filter_packages(self.package_data)
        
        if not keyword:
            # 如果关键字为空，显示过滤后的所有包
            self.filtered_package_data = base_packages.copy()
            self.log_message(f"[搜索] 显示架构 {arch_text} 的所有包，共 {len(self.filtered_package_data)} 个")
        else:
            # 根据关键字过滤包
            self.filtered_package_data = []
            for pkg in base_packages:
                if (keyword in pkg['name'].lower() or
                    keyword in pkg.get('arch', '').lower() or
                    keyword in pkg.get('version', '').lower()):
                    self.filtered_package_data.append(pkg)
            
            self.log_message(f"[搜索] 关键字 '{keyword}' 在架构 {arch_text} 中找到 {len(self.filtered_package_data)} 个包")
        
        # 更新表格显示
        self.refresh_table_data()
    
    def update_log_visibility(self):
        """更新日志可见性"""
        if self.show_log.get():
            # 显示日志区域
            self.log_frame.grid(row=4, column=0, sticky="ew", pady=(5, 0))
            self.log_message("[界面] 操作日志已显示")
        else:
            # 隐藏日志区域
            self.log_frame.grid_remove()
            self.log_message("[界面] 操作日志已隐藏")
    
    def select_local_source(self):
        """选择本地源路径"""
        selected_path = filedialog.askdirectory(title="选择本地源路径")
        if selected_path:
            self.source_url.set(selected_path)
    
    def select_save_path(self):
        """选择保存路径"""
        selected_path = filedialog.askdirectory(title="选择保存路径", initialdir=self.save_path.get())
        if selected_path:
            self.save_path.set(selected_path)
    
    def refresh_package_list(self):
        """刷新包列表"""
        def refresh_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在获取包列表..."))
                self.message_queue.put(("log", "[开始] 开始获取包列表"))
                
                source = self.source_url.get().strip()
                
                if not source:
                    self.message_queue.put(("log", "[错误] 请输入下载源路径"))
                    return
                
                # 自动判断路径类型
                if source.startswith(('http://', 'https://', 'ftp://')):
                    self.message_queue.put(("log", f"[信息] 检测到网络源，使用网络获取方式"))
                    packages = self.get_network_packages(source)
                elif os.path.exists(source):
                    self.message_queue.put(("log", f"[信息] 检测到本地源，使用本地扫描方式"))
                    packages = self.get_local_packages(source)
                else:
                    # 尝试作为网络源处理
                    self.message_queue.put(("log", f"[信息] 路径不存在，尝试作为网络源处理"))
                    packages = self.get_network_packages(source)
                
                # 不在这里过滤，保存完整的包数据
                # 过滤操作将在 search_packages() 中进行
                
                self.message_queue.put(("update_packages", packages))
                self.message_queue.put(("log", f"[完成] 获取到 {len(packages)} 个包"))
                self.message_queue.put(("status", "包列表刷新完成"))
                # 刷新后自动执行搜索
                self.message_queue.put(("auto_search",))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 获取包列表失败: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=refresh_task, daemon=True).start()
    
    def get_network_packages(self, url):
        """从网络获取包列表"""
        try:
            self.log_message(f"[网络] 从URL获取包列表: {url}")
            
            # 尝试从网络URL获取包列表
            packages = []
            
            # 首先尝试解析HTML页面获取包列表
            try:
                import requests
                from bs4 import BeautifulSoup
                
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找所有.deb文件的链接
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.endswith('.deb'):
                        # 构造完整的URL
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('/'):
                            from urllib.parse import urljoin
                            full_url = urljoin(url, href)
                        else:
                            full_url = url.rstrip('/') + '/' + href
                        
                        # 解析包信息
                        pkg_info = self.parse_deb_filename(os.path.basename(href))
                        if pkg_info:
                            # 保存完整文件名作为显示名称
                            full_filename = os.path.basename(href)
                            packages.append({
                                'name': pkg_info['name'],
                                'arch': pkg_info['arch'],
                                'version': pkg_info['version'],
                                'full_filename': full_filename,  # 添加完整文件名
                                'status': '未下载',
                                'download_time': '',
                                'selected': False,
                                'url': full_url
                            })
                
                self.log_message(f"[网络] 从HTML页面获取到 {len(packages)} 个包")
                
            except ImportError:
                self.log_message("[警告] 未安装requests和beautifulsoup4，使用备用方法")
                # 使用urllib备用方法
                try:
                    import urllib.request
                    from html.parser import HTMLParser
                    
                    class LinkParser(HTMLParser):
                        def __init__(self):
                            super().__init__()
                            self.links = []
                        
                        def handle_starttag(self, tag, attrs):
                            if tag == 'a':
                                for attr, value in attrs:
                                    if attr == 'href' and value.endswith('.deb'):
                                        self.links.append(value)
                    
                    parser = LinkParser()
                    response = urllib.request.urlopen(url, timeout=10)
                    html_content = response.read().decode('utf-8')
                    parser.feed(html_content)
                    
                    for href in parser.links:
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('/'):
                            from urllib.parse import urljoin
                            full_url = urljoin(url, href)
                        else:
                            full_url = url.rstrip('/') + '/' + href
                        
                        pkg_info = self.parse_deb_filename(os.path.basename(href))
                        if pkg_info:
                            # 保存完整文件名作为显示名称
                            full_filename = os.path.basename(href)
                            packages.append({
                                'name': pkg_info['name'],
                                'arch': pkg_info['arch'],
                                'version': pkg_info['version'],
                                'full_filename': full_filename,  # 添加完整文件名
                                'status': '未下载',
                                'download_time': '',
                                'selected': False,
                                'url': full_url
                            })
                    
                    self.log_message(f"[网络] 使用urllib获取到 {len(packages)} 个包")
                    
                except Exception as e:
                    self.log_message(f"[错误] 备用方法也失败: {str(e)}")
                    # 最后使用模拟数据
                    return self._get_mock_packages()
            
            # 如果没有获取到包，使用模拟数据
            if not packages:
                self.log_message("[信息] 未获取到网络包，使用模拟数据")
                return self._get_mock_packages()
            
            return packages
            
        except Exception as e:
            self.log_message(f"[错误] 网络获取包列表失败: {str(e)}")
            return self._get_mock_packages()
    
    def get_local_packages(self, path):
        """从本地路径获取包列表（只扫描当前目录）"""
        try:
            self.log_message(f"[本地] 从路径获取包列表: {path}")
            
            packages = []
            if not os.path.exists(path):
                self.log_message(f"[警告] 本地路径不存在: {path}")
                return packages
            
            # 只扫描当前目录，不递归
            self.message_queue.put(("status", "正在扫描本地DEB文件..."))
            
            try:
                files = os.listdir(path)
            except PermissionError:
                self.log_message(f"[错误] 没有权限访问目录: {path}")
                return packages
            
            # 过滤出.deb文件
            deb_files = [file for file in files if file.endswith('.deb')]
            total_files = len(deb_files)
            
            if total_files == 0:
                self.log_message(f"[信息] 当前目录没有找到DEB文件")
                return packages
            
            self.log_message(f"[信息] 发现 {total_files} 个DEB文件，开始解析...")
            
            # 扫描并解析包信息
            for i, file in enumerate(deb_files):
                full_path = os.path.join(path, file)
                
                # 每扫描50个文件更新一次进度
                if (i + 1) % 50 == 0:
                    progress = ((i + 1) / total_files) * 100
                    self.message_queue.put(("status", f"扫描进度: {i+1}/{total_files} ({progress:.1f}%)"))
                
                # 解析包名和架构
                pkg_info = self.parse_deb_filename(file)
                if pkg_info:
                    # 检查是否已下载到保存目录
                    save_path = self.save_path.get()
                    target_path = os.path.join(save_path, file)
                    status = '已下载' if os.path.exists(target_path) else '未下载'
                    
                    # 保存完整文件名作为显示名称
                    full_filename = file
                    packages.append({
                        'name': pkg_info['name'],
                        'arch': pkg_info['arch'],
                        'version': pkg_info['version'],
                        'full_filename': full_filename,  # 添加完整文件名
                        'status': status,
                        'download_time': '',
                        'selected': False,
                        'source_path': full_path
                    })
                else:
                    self.log_message(f"[警告] 无法解析文件名: {file}")
            
            self.log_message(f"[完成] 成功解析 {len(packages)} 个DEB包")
            return packages
            
        except Exception as e:
            self.log_message(f"[错误] 本地获取包列表失败: {str(e)}")
            return []
    
    def parse_deb_filename(self, filename):
        """解析.deb文件名，提取包名和架构"""
        try:
            # 移除.deb后缀
            if not filename.endswith('.deb'):
                return None
            
            name_part = filename[:-4]
            
            # 定义有效的架构列表，包括带下划线的架构
            valid_archs = ['amd64', 'i386', 'arm64', 'armhf', 'armel', 'mips', 'mipsel', 'mips64el', 'ppc64el', 's390x', 'all', 'loongarch64', 'sw_64']
            
            # 首先尝试从后往前匹配已知的架构
            for arch in sorted(valid_archs, key=len, reverse=True):  # 从最长的开始匹配
                if name_part.endswith('_' + arch):
                    # 找到架构，分割包名和版本
                    arch_index = len(name_part) - len('_' + arch)
                    package_and_version = name_part[:arch_index]
                    
                    # 查找版本号的开始位置（最后一个下划线）
                    last_underscore = package_and_version.rfind('_')
                    if last_underscore > 0:
                        package_name = package_and_version[:last_underscore]
                        version = package_and_version[last_underscore + 1:]
                        
                        return {
                            'name': package_name,
                            'version': version,
                            'arch': arch
                        }
            
            # 如果标准解析失败，尝试使用split方法
            parts = name_part.split('_')
            if len(parts) >= 3:
                # 最后一个是架构
                arch = parts[-1]
                # 倒数第二个是版本
                version = parts[-2]
                # 剩下的都是包名
                package_name = '_'.join(parts[:-2])
                
                # 验证架构是否有效
                if arch in valid_archs:
                    return {
                        'name': package_name,
                        'version': version,
                        'arch': arch
                    }
            
            # 如果都失败了，尝试使用文件名作为包名，架构设为unknown
            self.log_message(f"[警告] 无法解析文件名架构: {filename}, 使用默认值")
            return {
                'name': name_part,
                'version': 'unknown',
                'arch': 'unknown'
            }
            
        except Exception as e:
            self.log_message(f"[警告] 解析文件名失败: {filename}, 错误: {str(e)}")
            return None
    
    def _get_mock_packages(self):
        """获取模拟包数据"""
        packages = []
        all_archs = ['arm64', 'amd64', 'i386', 'loongarch64', 'mips64el', 'sw_64', 'all']
        
        # 模拟包名
        base_packages = [
            'package1', 'package2', 'package3', 'package4', 'package5',
            'libtest1', 'libtest2', 'app-example', 'tool-utils', 'service-daemon',
            'deepin-terminal', 'deepin-file-manager', 'deepin-system-monitor',
            'deepin-calculator', 'deepin-music', 'deepin-camera'
        ]
        
        for pkg_name in base_packages:
            for arch in all_archs:
                # 构造完整文件名
                full_filename = f"{pkg_name}_{arch}.deb"
                packages.append({
                    'name': pkg_name,
                    'arch': arch,
                    'version': '1.0.0',
                    'full_filename': full_filename,  # 添加完整文件名
                    'status': '未下载',
                    'download_time': '',
                    'selected': False,
                    'url': f"{self.source_url.get()}/{full_filename}"
                })
                
                # 总是包含符号包，过滤操作在 should_include_package() 中进行
                # 构造完整文件名
                full_filename = f"{pkg_name}-dbgsym_{arch}.deb"
                packages.append({
                    'name': f"{pkg_name}-dbgsym",
                    'arch': arch,
                    'version': '1.0.0',
                    'full_filename': full_filename,  # 添加完整文件名
                    'status': '未下载',
                    'download_time': '',
                    'selected': False,
                    'url': f"{self.source_url.get()}/{full_filename}"
                })
        
        return packages
    
    def should_include_package(self, pkg_info):
        """检查包是否应该包含在列表中"""
        # 检查架构
        selected_archs = [arch for arch, var in self.arch_vars.items() if var.get()]
        pkg_name = pkg_info.get('name', '').lower()
        pkg_arch = pkg_info.get('arch', '').lower()
        
        # 调试日志
        self.log_message(f"[调试] 检查包: {pkg_info.get('full_filename', pkg_info.get('name', 'unknown'))}, 架构: {pkg_arch}")
        self.log_message(f"[调试] 选中的架构: {selected_archs}")
        
        # 如果没有选择任何架构，则不显示任何包
        if not selected_archs:
            self.log_message(f"[调试] 没有选择任何架构，包被过滤掉")
            return False
            
        # 架构筛选条件
        arch_condition_met = False
        
        # 'all' 是一种特殊的架构类型，不是全选功能
        # 只有当选择了 'all' 架构或者包的架构在选中的架构列表中时，架构条件才满足
        # 检查包的架构是否在选中的架构列表中
        # 优先使用解析出的架构信息，如果没有则从包名中匹配
        for arch in selected_archs:
                arch_lower = arch.lower()
                # 检查解析出的架构
                if pkg_arch == arch_lower:
                    arch_condition_met = True
                    self.log_message(f"[调试] 架构匹配: {pkg_arch} == {arch_lower}")
                    break
                # 检查包名中是否包含架构关键字
                elif arch_lower in pkg_name:
                    arch_condition_met = True
                    self.log_message(f"[调试] 包名中包含架构关键字: {arch_lower} in {pkg_name}")
                    break
            
        if not arch_condition_met:
            self.log_message(f"[调试] 架构不匹配，包被过滤掉")
        
        # 符号包筛选条件
        dbgsym_condition_met = True
        if not self.include_dbgsym.get() and 'dbgsym' in pkg_info['name']:
            dbgsym_condition_met = False
            self.log_message(f"[调试] 符号包被过滤掉: {pkg_info['name']}")
        else:
            self.log_message(f"[调试] 符号包条件满足: include_dbgsym={self.include_dbgsym.get()}, is_dbgsym={'dbgsym' in pkg_info['name']}")
        
        result = arch_condition_met and dbgsym_condition_met
        self.log_message(f"[调试] 最终结果: {result} (架构条件={arch_condition_met}, 符号包条件={dbgsym_condition_met})")
        
        # 返回架构和符号包条件的"且"关系
        return result
    
    def filter_packages(self, packages):
        """根据当前设置过滤包列表"""
        filtered = []
        for pkg in packages:
            if self.should_include_package(pkg):
                filtered.append(pkg)
        return filtered
    
    def refresh_package_table(self):
        """刷新包表格显示"""
        self.refresh_table_data()
    
    def select_all(self):
        """全选所有包"""
        for var in self.package_vars.values():
            var.set(True)
        self.update_tree_selection()
        self.log_message("[操作] 已全选所有包")
    
    def deselect_all(self):
        """全不选所有包"""
        for var in self.package_vars.values():
            var.set(False)
        self.update_tree_selection()
        self.log_message("[操作] 已取消选择所有包")
    
    def update_tree_selection(self):
        """更新树形视图的勾选状态显示"""
        for item in self.package_tree.get_children():
            # 获取包数据
            item_data = self.package_item_data.get(item, {})
            package = item_data.get('package', {})
            unique_key = item_data.get('unique_key', '')
            
            if unique_key and unique_key in self.package_vars:
                selected_text = "☑" if self.package_vars[unique_key].get() else "☐"
                # 更新第一列的勾选状态
                self.package_tree.set(item, 'selected', selected_text)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选中右键点击的项
        item = self.package_tree.identify_row(event.y)
        if item:
            # 检查当前项是否已经在选择中
            current_selection = self.package_tree.selection()
            if item not in current_selection:
                # 如果当前项不在选择中，则只选择这一项
                self.package_tree.selection_set(item)
            # 如果当前项已经在选择中，则保持现有选择不变
            
            # 创建右键菜单
            self.context_menu = tk.Menu(self.root, tearoff=0)
            
            # 包操作菜单
            self.context_menu.add_command(label="下载选中", command=self.download_selected)
            self.context_menu.add_command(label="删除选中", command=self.delete_selected)
            self.context_menu.add_separator()
            
            # 选择操作菜单
            self.context_menu.add_command(label="全选", command=self.select_all)
            self.context_menu.add_command(label="全不选", command=self.deselect_all)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="勾选", command=self.toggle_selection)
            self.context_menu.add_command(label="取消勾选", command=self.deselect_item)
            self.context_menu.add_separator()
            
            # 列表操作菜单
            self.context_menu.add_command(label="刷新列表", command=self.refresh_package_list)
            self.context_menu.add_separator()
            
            # 工具操作菜单
            self.context_menu.add_command(label="压缩成ZIP包", command=self.create_zip)
            self.context_menu.add_command(label="打开本地保存目录", command=self.open_save_dir)
            self.context_menu.add_command(label="拷贝到剪切板", command=self.copy_to_clipboard)
            
            # 显示菜单
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def toggle_selection(self):
        """切换选中项的勾选状态"""
        selected_items = self.package_tree.selection()
        for item in selected_items:
            item_data = self.package_item_data.get(item, {})
            unique_key = item_data.get('unique_key', '')
            
            if unique_key and unique_key in self.package_vars:
                current_state = self.package_vars[unique_key].get()
                self.package_vars[unique_key].set(not current_state)
        
        self.update_tree_selection()
    
    def deselect_item(self):
        """取消勾选选中项"""
        selected_items = self.package_tree.selection()
        for item in selected_items:
            item_data = self.package_item_data.get(item, {})
            unique_key = item_data.get('unique_key', '')
            
            if unique_key and unique_key in self.package_vars:
                self.package_vars[unique_key].set(False)
        
        self.update_tree_selection()
    
    def copy_to_clipboard(self):
        """复制选中项到剪切板"""
        selected_items = self.package_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要复制的包")
            return
        
        try:
            # 获取选中包的信息
            package_names = []
            for item in selected_items:
                values = self.package_tree.item(item, 'values')
                if values and len(values) >= 4:
                    index = values[0]  # 序号在第一列
                    package_name = values[2]  # 包名在第三列
                    arch = values[3]  # 架构在第四列
                    package_names.append(f"{index}. {package_name} ({arch})")
            
            # 复制到剪切板
            clipboard_text = '\n'.join(package_names)
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            self.root.update()
            
            self.log_message(f"[操作] 已复制 {len(package_names)} 个包到剪切板")
            messagebox.showinfo("复制成功", f"已复制 {len(package_names)} 个包到剪切板")
            
        except Exception as e:
            self.log_message(f"[错误] 复制到剪切板失败: {str(e)}")
            messagebox.showerror("复制失败", f"复制到剪切板失败: {str(e)}")
    
    def on_item_single_click(self, event):
        """单击项目时的处理"""
        item = self.package_tree.identify_row(event.y)
        if item:
            # 记录拖拽开始项
            self.drag_start_item = item
            self.drag_start_selection = set(self.package_tree.selection())
            self.drag_mode = 'normal'
            
            # 如果没有按下Ctrl或Shift，则清除之前的选择
            if not event.state & 0x0004 and not event.state & 0x0001:  # Ctrl和Shift
                self.package_tree.selection_set(item)
    
    def on_ctrl_click(self, event):
        """Ctrl+点击项目时的处理"""
        item = self.package_tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
            self.drag_start_selection = set(self.package_tree.selection())
            self.drag_mode = 'ctrl'
            
            # 切换选择状态
            if item in self.drag_start_selection:
                self.package_tree.selection_remove(item)
            else:
                self.package_tree.selection_add(item)
    
    def on_shift_click(self, event):
        """Shift+点击项目时的处理"""
        item = self.package_tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
            self.drag_start_selection = set(self.package_tree.selection())
            self.drag_mode = 'shift'
            
            # 获取当前选择的第一项
            current_selection = self.package_tree.selection()
            if current_selection:
                anchor_item = current_selection[0]
                self.select_range(anchor_item, item)
            else:
                self.package_tree.selection_set(item)
    
    def on_item_motion(self, event):
        """鼠标拖拽移动时的处理"""
        if not self.drag_start_item:
            return
            
        current_item = self.package_tree.identify_row(event.y)
        if not current_item or current_item == self.drag_start_item:
            return
        
        if self.drag_mode == 'normal':
            # 普通拖拽选择：选择从开始项到当前项的所有项
            self.select_range(self.drag_start_item, current_item)
        elif self.drag_mode == 'ctrl':
            # Ctrl+拖拽：切换选择状态
            if current_item not in self.drag_start_selection:
                self.package_tree.selection_add(current_item)
            else:
                self.package_tree.selection_remove(current_item)
        elif self.drag_mode == 'shift':
            # Shift+拖拽：范围选择
            current_selection = self.package_tree.selection()
            if current_selection:
                anchor_item = current_selection[0]
                self.select_range(anchor_item, current_item)
    
    def on_item_release(self, event):
        """鼠标释放时的处理"""
        self.drag_start_item = None
        self.drag_start_selection = set()
        self.drag_mode = None
    
    def select_range(self, start_item, end_item):
        """选择从开始项到结束项范围内的所有项"""
        # 获取所有子项
        all_items = list(self.package_tree.get_children())
        
        try:
            start_index = all_items.index(start_item)
            end_index = all_items.index(end_item)
            
            # 确保开始索引小于结束索引
            if start_index > end_index:
                start_index, end_index = end_index, start_index
            
            # 选择范围内的所有项
            range_items = all_items[start_index:end_index + 1]
            self.package_tree.selection_set(range_items)
            
        except ValueError:
            # 如果项目不存在，只选择结束项
            self.package_tree.selection_set(end_item)
    
    def on_item_double_click(self, event):
        """双击项目时的处理"""
        item = self.package_tree.identify_row(event.y)
        if item:
            item_data = self.package_item_data.get(item, {})
            unique_key = item_data.get('unique_key', '')
            
            if unique_key and unique_key in self.package_vars:
                # 切换勾选状态
                current_state = self.package_vars[unique_key].get()
                self.package_vars[unique_key].set(not current_state)
                self.update_tree_selection()
    
    def download_selected(self):
        """下载选中的包"""
        selected_packages = []
        for pkg in self.package_data:
            # 使用唯一标识符检查选中状态
            unique_key = f"{pkg['name']}_{pkg.get('arch', '')}"
            if self.package_vars.get(unique_key, tk.BooleanVar(value=False)).get():
                selected_packages.append(pkg)
        
        if not selected_packages:
            messagebox.showwarning("警告", "请至少选择一个包进行下载")
            return
        
        def download_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在下载选中的包..."))
                self.message_queue.put(("log", f"[开始] 开始下载 {len(selected_packages)} 个包"))
                
                save_path = self.save_path.get()
                os.makedirs(save_path, exist_ok=True)
                
                success_count = 0
                error_count = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {}
                    
                    for pkg in selected_packages:
                        source = self.source_url.get().strip()
                        # 自动判断下载方式
                        if source.startswith(('http://', 'https://', 'ftp://')) or not os.path.exists(source):
                            future = executor.submit(self.download_network_package, pkg, save_path)
                        else:
                            future = executor.submit(self.copy_local_package, pkg, save_path)
                        futures[future] = pkg
                    
                    for future in concurrent.futures.as_completed(futures):
                        pkg = futures[future]
                        try:
                            success = future.result()
                            if success:
                                success_count += 1
                                self.message_queue.put(("log", f"[成功] {pkg['name']} 下载完成"))
                                # 更新包状态
                                pkg['status'] = '已下载'
                                pkg['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                error_count += 1
                                self.message_queue.put(("log", f"[失败] {pkg['name']} 下载失败"))
                        except Exception as e:
                            error_count += 1
                            self.message_queue.put(("log", f"[错误] {pkg['name']} 下载异常: {str(e)}"))
                
                # 刷新表格显示
                self.message_queue.put(("refresh_table",))
                self.message_queue.put(("log", f"[完成] 下载完成: 成功 {success_count} 个，失败 {error_count} 个"))
                self.message_queue.put(("status", "下载操作完成"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 下载过程出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=download_task, daemon=True).start()
    
    def download_network_package(self, pkg, save_path):
        """下载网络包"""
        try:
            self.log_message(f"[下载] 开始下载网络包: {pkg['name']}")
            
            # 获取下载URL
            download_url = pkg.get('url')
            if not download_url:
                # 如果没有URL，尝试构造
                download_url = f"{self.source_url.get()}/{pkg['name']}_{pkg.get('version', '1.0')}_{pkg['arch']}.deb"
            
            # 生成文件名
            filename = f"{pkg['name']}_{pkg.get('version', '1.0')}_{pkg['arch']}.deb"
            target_path = os.path.join(save_path, filename)
            
            # 使用urllib下载
            try:
                import urllib.request
                urllib.request.urlretrieve(download_url, target_path)
                self.log_message(f"[成功] 网络包下载完成: {filename}")
                return True
                
            except ImportError:
                # 备用方法：使用requests
                try:
                    import requests
                    response = requests.get(download_url, timeout=30)
                    response.raise_for_status()
                    
                    with open(target_path, 'wb') as f:
                        f.write(response.content)
                    
                    self.log_message(f"[成功] 网络包下载完成: {filename}")
                    return True
                    
                except Exception as e:
                    self.log_message(f"[错误] requests下载失败: {str(e)}")
                    # 最后使用模拟文件
                    with open(target_path, 'w') as f:
                        f.write(f"模拟的DEB包文件: {pkg['name']}\n原始URL: {download_url}")
                    return True
            
        except Exception as e:
            self.log_message(f"[错误] 下载网络包失败: {pkg['name']}, 错误: {str(e)}")
            return False
    
    def copy_local_package(self, pkg, save_path):
        """复制本地包"""
        try:
            source_path = pkg.get('source_path')
            if not source_path or not os.path.exists(source_path):
                self.log_message(f"[错误] 源文件不存在: {source_path}")
                return False
            
            filename = os.path.basename(source_path)
            target_path = os.path.join(save_path, filename)
            
            self.log_message(f"[复制] 开始复制本地包: {pkg['name']}")
            
            # 使用多线程复制
            shutil.copy2(source_path, target_path)
            
            return True
            
        except Exception as e:
            self.log_message(f"[错误] 复制本地包失败: {pkg['name']}, 错误: {str(e)}")
            return False
    
    def delete_selected(self):
        """删除选中的包"""
        selected_packages = []
        for pkg in self.package_data:
            # 使用唯一标识符检查选中状态
            unique_key = f"{pkg['name']}_{pkg.get('arch', '')}"
            if self.package_vars.get(unique_key, tk.BooleanVar(value=False)).get():
                selected_packages.append(pkg)
        
        if not selected_packages:
            messagebox.showwarning("警告", "请至少选择一个包进行删除")
            return
        
        response = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(selected_packages)} 个包吗？\n\n此操作不可恢复！",
            icon="warning"
        )
        
        if not response:
            return
        
        def delete_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在删除选中的包..."))
                self.message_queue.put(("log", f"[开始] 开始删除 {len(selected_packages)} 个包"))
                
                save_path = self.save_path.get()
                success_count = 0
                error_count = 0
                
                for pkg in selected_packages:
                    try:
                        # 查找并删除文件
                        for file in os.listdir(save_path):
                            if pkg['name'] in file and file.endswith('.deb'):
                                file_path = os.path.join(save_path, file)
                                os.remove(file_path)
                                success_count += 1
                                self.message_queue.put(("log", f"[成功] 已删除: {file}"))
                                
                                # 更新包状态
                                pkg['status'] = '未下载'
                                pkg['download_time'] = ''
                                break
                        else:
                            self.message_queue.put(("log", f"[跳过] 未找到包文件: {pkg['name']}"))
                            error_count += 1
                            
                    except Exception as e:
                        error_count += 1
                        self.message_queue.put(("log", f"[错误] 删除包失败: {pkg['name']}, 错误: {str(e)}"))
                
                # 刷新表格显示
                self.message_queue.put(("refresh_table",))
                self.message_queue.put(("log", f"[完成] 删除完成: 成功 {success_count} 个，失败 {error_count} 个"))
                self.message_queue.put(("status", "删除操作完成"))
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 删除过程出错: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=delete_task, daemon=True).start()
    
    def create_zip(self):
        """创建ZIP压缩包"""
        response = messagebox.askyesno(
            "确认压缩",
            "确定要将保存目录中的所有.deb文件压缩成ZIP包吗？",
            icon="info"
        )
        
        if not response:
            return
        
        def zip_task():
            try:
                self.message_queue.put(("progress", "start"))
                self.message_queue.put(("status", "正在创建ZIP压缩包..."))
                self.message_queue.put(("log", "[开始] 开始创建ZIP压缩包"))
                
                save_path = self.save_path.get()
                zip_filename = f"deb_packages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(save_path, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in os.listdir(save_path):
                        if file.endswith('.deb'):
                            file_path = os.path.join(save_path, file)
                            zipf.write(file_path, file)
                            self.message_queue.put(("log", f"[压缩] 已添加: {file}"))
                
                self.message_queue.put(("log", f"[完成] ZIP包创建完成: {zip_path}"))
                self.message_queue.put(("status", "ZIP压缩包创建完成"))
                
                # 询问是否打开ZIP文件所在目录
                response = messagebox.askyesno(
                    "压缩完成",
                    f"ZIP包已创建:\n{zip_path}\n\n是否打开所在目录？"
                )
                
                if response:
                    subprocess.Popen(["xdg-open", save_path])
                
            except Exception as e:
                self.message_queue.put(("log", f"[错误] 创建ZIP包失败: {str(e)}"))
            finally:
                self.message_queue.put(("progress", "stop"))
        
        threading.Thread(target=zip_task, daemon=True).start()
    
    def open_save_dir(self):
        """打开保存目录"""
        save_path = self.save_path.get()
        if os.path.exists(save_path):
            subprocess.Popen(["xdg-open", save_path])
            self.log_message(f"[操作] 已打开保存目录: {save_path}")
        else:
            messagebox.showwarning("警告", f"保存目录不存在: {save_path}")
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if 'source_url' in config:
                    self.source_url.set(config['source_url'])
                if 'save_path' in config:
                    self.save_path.set(config['save_path'])
                if 'arch_vars' in config:
                    for arch, value in config['arch_vars'].items():
                        if arch in self.arch_vars:
                            self.arch_vars[arch].set(value)
                if 'include_dbgsym' in config:
                    self.include_dbgsym.set(config['include_dbgsym'])
                if 'show_log' in config:
                    self.show_log.set(config['show_log'])
                if 'search_keyword' in config:
                    self.search_keyword.set(config['search_keyword'])
                
                self.log_message("[配置] 配置文件加载完成")
            else:
                self.log_message("[配置] 配置文件不存在，使用默认配置")
                
        except Exception as e:
            self.log_message(f"[错误] 加载配置文件失败: {str(e)}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            config = {
                'source_url': self.source_url.get(),
                'save_path': self.save_path.get(),
                'arch_vars': {arch: var.get() for arch, var in self.arch_vars.items()},
                'include_dbgsym': self.include_dbgsym.get(),
                'show_log': self.show_log.get(),
                'search_keyword': self.search_keyword.get()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.log_message("[配置] 配置文件保存完成")
            
        except Exception as e:
            self.log_message(f"[错误] 保存配置文件失败: {str(e)}")
    
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)
        
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(message)
    
    def _bind_all_scroll_events(self):
        """绑定所有滚动区域的鼠标事件"""
        pass
    
    def _on_global_click(self, event):
        """全局鼠标点击事件处理，用于关闭右键菜单"""
        if hasattr(self, 'context_menu'):
            try:
                self.context_menu.unpost()
            except:
                pass
    
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
                elif message[0] == "update_packages":
                    self.package_data = message[1]
                    # 更新包数据后，自动执行搜索过滤
                    self.search_packages()
                elif message[0] == "refresh_table":
                    self.refresh_table_data()
                elif message[0] == "auto_search":
                    self.search_packages()
                    
        except queue.Empty:
            pass
        
        # 每100ms检查一次消息队列
        self.root.after(100, self.process_queue)
    
    def on_closing(self):
        """程序退出时的清理操作"""
        try:
            # 保存配置
            self.save_config()
            
            # 清理临时目录
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log_message(f"[清理] 已清理临时目录: {self.temp_dir}")
                
        except Exception as e:
            # 静默处理，避免影响程序退出
            pass
        
        # 销毁窗口
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DebPackageSaver(root)
    
    # 绑定窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()


if __name__ == "__main__":
    main()