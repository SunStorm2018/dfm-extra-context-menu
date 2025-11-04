#!/usr/bin/env python3
"""
Debian Changelog 版本更新 GUI 工具
功能：提供图形界面来更新 Debian 包版本，实时预览更改并提交到 Git
"""

import os
import sys
import re
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog


class DebianVersionGUI:
    """Debian 版本更新 GUI 应用"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Debian 包版本更新工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 配置信息
        self.maintainer = "zhanghongyuan"
        self.email = "zhanghongyuan@uniontech.com"
        self.full_maintainer = f"{self.maintainer} <{self.email}>"
        
        # YAML 文件配置
        self.default_yaml_files = [
            "sw64/linglong.yaml",
            "loong64/linglong.yaml", 
            "arm64/linglong.yaml",
            "mips64/linglong.yaml",
            "linglong.yaml"
        ]
        
        # 当前状态
        self.current_version = ""
        self.project_path = ""
        self.project_name = ""
        self.last_commit_hash = ""  # 记录第一次提交的hash
        self.current_session_commits = []  # 记录本次会话的提交
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 文件路径选择
        ttk.Label(main_frame, text="项目路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(main_frame, textvariable=self.path_var, width=60)
        self.path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="浏览", command=self.browse_path).grid(row=0, column=2, padx=5)
        
        # 当前版本显示
        ttk.Label(main_frame, text="当前版本:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.current_version_var = tk.StringVar(value="未选择项目")
        ttk.Label(main_frame, textvariable=self.current_version_var).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 新版本输入
        ttk.Label(main_frame, text="新版本号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.new_version_var = tk.StringVar()
        self.new_version_entry = ttk.Entry(main_frame, textvariable=self.new_version_var, width=30)
        self.new_version_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.new_version_entry.bind('<KeyRelease>', self.on_version_change)
        
        # 版本类型选择
        ttk.Label(main_frame, text="版本类型:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.version_type_var = tk.StringVar(value="patch")
        version_frame = ttk.Frame(main_frame)
        version_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(version_frame, text="主要版本 (major)", variable=self.version_type_var, 
                        value="major", command=self.on_version_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(version_frame, text="次要版本 (minor)", variable=self.version_type_var, 
                        value="minor", command=self.on_version_type_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(version_frame, text="修订版本 (patch)", variable=self.version_type_var, 
                        value="patch", command=self.on_version_type_change).pack(side=tk.LEFT)
        
        # 预览区域
        ttk.Label(main_frame, text="更改预览:").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # 创建标签页
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Changelog 预览标签页
        changelog_frame = ttk.Frame(notebook, padding="5")
        notebook.add(changelog_frame, text="Changelog")
        
        self.changelog_preview = scrolledtext.ScrolledText(changelog_frame, width=80, height=10)
        self.changelog_preview.pack(fill=tk.BOTH, expand=True)
        self.changelog_preview.config(state=tk.DISABLED)
        
        # YAML 配置标签页
        yaml_frame = ttk.Frame(notebook, padding="5")
        notebook.add(yaml_frame, text="YAML 配置")
        
        # 创建 YAML 配置表格框架
        yaml_table_frame = ttk.Frame(yaml_frame)
        yaml_table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建表格标题
        header_frame = ttk.Frame(yaml_table_frame)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(header_frame, text="YAML 名称", width=20).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="旧版本", width=15).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="新版本", width=15).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="操作", width=10).pack(side=tk.LEFT, padx=2)
        
        # 创建滚动区域用于 YAML 配置表格
        yaml_canvas = tk.Canvas(yaml_table_frame)
        scrollbar = ttk.Scrollbar(yaml_table_frame, orient="vertical", command=yaml_canvas.yview)
        scrollable_frame = ttk.Frame(yaml_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: yaml_canvas.configure(scrollregion=yaml_canvas.bbox("all"))
        )
        
        yaml_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        yaml_canvas.configure(yscrollcommand=scrollbar.set)
        
        yaml_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.yaml_table_frame = scrollable_frame
        self.yaml_config_widgets = {}  # 存储 YAML 配置组件
        
        # 添加创建新 YAML 配置行的按钮
        add_button_frame = ttk.Frame(yaml_frame)
        add_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            add_button_frame,
            text="添加 YAML 配置行",
            command=self.add_yaml_config_row
        ).pack(side=tk.LEFT, padx=5)
        
        # Commit 预览标签页
        commit_frame = ttk.Frame(notebook, padding="5")
        notebook.add(commit_frame, text="Commit Info")
        
        self.commit_preview = scrolledtext.ScrolledText(commit_frame, width=80, height=10)
        self.commit_preview.pack(fill=tk.BOTH, expand=True)
        self.commit_preview.config(state=tk.DISABLED)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="修改版本", command=self.modify_version).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 配置权重
        main_frame.rowconfigure(5, weight=1)
        
        # 初始加载当前目录
        self.path_var.set(os.getcwd())
        self.load_project()
        
    def browse_path(self):
        """浏览选择项目路径"""
        path = filedialog.askdirectory(title="选择项目目录")
        if path:
            self.path_var.set(path)
            self.load_project()
    
    def load_project(self):
        """加载项目信息"""
        self.project_path = self.path_var.get()
        
        if not os.path.isdir(self.project_path):
            self.status_var.set("错误: 路径不存在")
            return
        
        if not self.check_git_repo():
            self.status_var.set("错误: 不是 Git 仓库")
            return
        
        if not self.check_debian_dir():
            self.status_var.set("错误: 没有 debian 目录")
            return
        
        # 获取当前版本
        self.current_version = self.get_current_version()
        self.current_version_var.set(self.current_version)
        
        # 获取项目名称
        self.project_name = self.get_project_name()
        
        # 重置会话状态
        self.last_commit_hash = ""
        self.current_session_commits = []
        
        self.status_var.set(f"已加载项目: {self.project_name}")
        self.refresh_preview()
    
    def check_git_repo(self):
        """检查是否是 Git 仓库"""
        git_dir = os.path.join(self.project_path, ".git")
        return os.path.isdir(git_dir)
    
    def check_debian_dir(self):
        """检查是否有 debian 目录"""
        debian_dir = os.path.join(self.project_path, "debian")
        return os.path.isdir(debian_dir)
    
    def get_current_version(self):
        """获取当前版本"""
        changelog_path = os.path.join(self.project_path, "debian/changelog")
        
        if os.path.isfile(changelog_path):
            try:
                result = subprocess.run(
                    ['dpkg-parsechangelog', '-l', 'changelog', '-S', 'version'],
                    cwd=os.path.join(self.project_path, "debian"),
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip()
            except:
                pass
        
        return "0.0.1-1"
    
    def get_project_name(self):
        """从 changelog 中提取项目名称"""
        changelog_path = os.path.join(self.project_path, "debian/changelog")
        
        if os.path.isfile(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    match = re.search(r'^([a-zA-Z0-9-]+)\s*\(', first_line)
                    if match:
                        return match.group(1)
            except:
                pass
        
        return "unknown-project"
    
    def generate_new_version(self, current_version: str, version_type: str) -> str:
        """生成新版本号"""
        # 分离主版本号和 Debian 修订号
        had_revision = '-' in current_version
        if had_revision:
            base_version, debian_rev = current_version.rsplit('-', 1)
            if debian_rev.isdigit():
                debian_rev = int(debian_rev)
            else:
                base_version = current_version
                debian_rev = 1
                had_revision = True
        else:
            base_version = current_version
            debian_rev = 1
        
        # 解析主版本号
        version_parts = base_version.split('.')
        if len(version_parts) >= 3:
            try:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                patch = int(version_parts[2])
            except ValueError:
                major, minor, patch = 1, 0, 0
        elif len(version_parts) == 2:
            try:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                patch = 0
            except ValueError:
                major, minor, patch = 1, 0, 0
        elif len(version_parts) == 1:
            try:
                major = int(version_parts[0])
                minor = 0
                patch = 0
            except ValueError:
                major, minor, patch = 1, 0, 0
        else:
            major, minor, patch = 1, 0, 0
        
        # 根据版本类型递增
        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
            debian_rev = 1
        elif version_type == "minor":
            minor += 1
            patch = 0
            debian_rev = 1
        else:  # patch
            patch += 1
            debian_rev = 1
        
        # 构建新版本号
        new_base_version = f"{major}.{minor}.{patch}"
        
        # 如果原始版本没有修订号，新版本也不添加修订号
        if had_revision:
            return f"{new_base_version}-{debian_rev}"
        else:
            return new_base_version
    
    def on_version_change(self, event=None):
        """版本输入框内容变化时的处理"""
        self.refresh_preview()
    
    def on_version_type_change(self):
        """版本类型选择变化时的处理"""
        if self.current_version:
            new_version = self.generate_new_version(self.current_version, self.version_type_var.get())
            self.new_version_var.set(new_version)
            self.refresh_preview()
    
    def refresh_preview(self):
        """刷新预览内容"""
        new_version = self.new_version_var.get().strip()
        
        if not new_version or not self.current_version:
            return
        
        self.status_var.set("正在刷新预览...")
        
        # 更新 changelog 预览
        self.update_changelog_preview(new_version)
        
        # 更新 YAML 预览
        self.update_yaml_preview(new_version)
        
        # 更新 git diff 预览
        self.update_diff_preview(new_version)
        
        # 更新 commit 预览
        self.update_commit_preview(new_version)
        
        self.status_var.set("预览已刷新")
    
    def update_changelog_preview(self, new_version: str):
        """更新 changelog 预览"""
        changelog_path = os.path.join(self.project_path, "debian/changelog")
        
        if not os.path.isfile(changelog_path):
            return
        
        try:
            # 读取当前 changelog
            with open(changelog_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # 生成新的 changelog 条目
            current_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            git_log = self.get_git_log()
            
            new_entry = f"""{self.project_name} ({new_version}) unstable; urgency=medium
    
  * chore: Update version to {new_version}
{git_log}
 -- {self.full_maintainer}  {current_date}

"""
            
            # 生成预览内容（新条目 + 原内容）
            preview_content = new_entry + current_content
            
            # 更新预览框
            self.changelog_preview.config(state=tk.NORMAL)
            self.changelog_preview.delete(1.0, tk.END)
            self.changelog_preview.insert(1.0, preview_content)
            self.changelog_preview.config(state=tk.DISABLED)
            
        except Exception as e:
            self.status_var.set(f"错误: {str(e)}")
    
    def update_yaml_preview(self, new_version: str):
        """更新 YAML 文件配置表格"""
        try:
            yaml_files = self.get_existing_yaml_files()
            
            # 清除旧的表格内容
            for widget in self.yaml_table_frame.winfo_children():
                widget.destroy()
            
            self.yaml_config_widgets = {}
            
            # 创建表格行
            for i, yaml_file in enumerate(yaml_files):
                self.create_yaml_config_row(i, yaml_file, new_version)
            
        except Exception as e:
            self.status_var.set(f"YAML 配置错误: {str(e)}")
    
    def create_yaml_config_row(self, row_index: int, yaml_file: str, new_version: str):
        """创建 YAML 配置表格行"""
        row_frame = ttk.Frame(self.yaml_table_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        # YAML 文件名
        file_label = ttk.Label(row_frame, text=yaml_file, width=20)
        file_label.pack(side=tk.LEFT, padx=2)
        
        # 旧版本显示
        old_content = self.read_yaml_file(yaml_file)
        old_version = self.extract_version_from_yaml(old_content)
        old_version_var = tk.StringVar(value=old_version)
        old_version_label = ttk.Label(row_frame, textvariable=old_version_var, width=15)
        old_version_label.pack(side=tk.LEFT, padx=2)
        
        # 新版本输入框（可编辑）
        new_version_var = tk.StringVar(value=new_version.replace('-', '.'))
        new_version_entry = ttk.Entry(row_frame, textvariable=new_version_var, width=15)
        new_version_entry.pack(side=tk.LEFT, padx=2)
        
        # 绑定版本变化事件
        new_version_entry.bind('<KeyRelease>', lambda e, f=yaml_file: self.on_yaml_version_change(f))
        
        # 替换按钮
        replace_button = ttk.Button(
            row_frame,
            text="替换",
            width=8,
            command=lambda f=yaml_file: self.replace_single_yaml(f)
        )
        replace_button.pack(side=tk.LEFT, padx=2)
        
        # 存储组件引用
        self.yaml_config_widgets[yaml_file] = {
            'row_frame': row_frame,
            'file_label': file_label,
            'old_version_var': old_version_var,
            'new_version_var': new_version_var,
            'new_version_entry': new_version_entry,
            'replace_button': replace_button
        }
    
    def replace_single_yaml(self, yaml_file: str):
        """替换单个 YAML 文件"""
        try:
            # 获取该YAML文件配置的新版本号
            if yaml_file not in self.yaml_config_widgets:
                messagebox.showerror("错误", f"YAML 文件未配置: {yaml_file}")
                return
                
            new_version = self.yaml_config_widgets[yaml_file]['new_version_var'].get().strip()
            
            if not new_version:
                messagebox.showerror("错误", f"请输入 {yaml_file} 的新版本号")
                return
            
            full_path = os.path.join(self.project_path, yaml_file)
            
            # 备份原文件
            backup_path = full_path + ".bak"
            shutil.copy2(full_path, backup_path)
            
            try:
                # 读取文件内容
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 更新版本号
                updated_content = self.update_yaml_content(content, new_version)
                
                # 写入新内容
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                # 验证更改
                with open(full_path, 'r', encoding='utf-8') as f:
                    updated_content_check = f.read()
                    if self.extract_version_from_yaml(updated_content_check) != new_version.replace('-', '.'):
                        raise Exception(f"YAML 文件 {yaml_file} 更改应用失败")
                
                # 删除备份文件
                os.remove(backup_path)
                
                # 更新界面显示
                old_content = self.read_yaml_file(yaml_file)
                old_version = self.extract_version_from_yaml(old_content)
                self.yaml_config_widgets[yaml_file]['old_version_var'].set(old_version)
                
                self.status_var.set(f"已更新 {yaml_file}")
                messagebox.showinfo("成功", f"已更新 {yaml_file} 的版本")
                
            except Exception as e:
                # 恢复备份
                if os.path.exists(backup_path):
                    shutil.move(backup_path, full_path)
                raise e
                
        except Exception as e:
            messagebox.showerror("错误", f"更新 {yaml_file} 时出错: {str(e)}")
            self.status_var.set(f"错误: {str(e)}")
    
    def on_yaml_version_change(self, yaml_file: str):
        """YAML 版本输入框内容变化时的处理"""
        # 可以在这里添加版本验证逻辑
        pass
    
    def add_yaml_config_row(self):
        """添加新的 YAML 配置行"""
        # 弹出对话框让用户输入 YAML 文件路径
        yaml_path = tk.simpledialog.askstring("添加 YAML 配置", "请输入 YAML 文件路径:")
        
        if yaml_path:
            # 检查文件是否存在
            full_path = os.path.join(self.project_path, yaml_path)
            if not os.path.isfile(full_path):
                messagebox.showerror("错误", f"文件不存在: {yaml_path}")
                return
            
            # 检查是否已经在配置列表中
            if yaml_path in self.yaml_config_widgets:
                messagebox.showwarning("警告", f"YAML 文件已存在: {yaml_path}")
                return
            
            # 添加到默认文件列表（如果不存在）
            if yaml_path not in self.default_yaml_files:
                self.default_yaml_files.append(yaml_path)
            
            # 创建新的配置行
            new_version = self.new_version_var.get().strip() or self.current_version
            row_index = len(self.yaml_config_widgets)
            self.create_yaml_config_row(row_index, yaml_path, new_version)
            
            self.status_var.set(f"已添加 YAML 配置: {yaml_path}")
    
    def update_commit_preview(self, new_version: str):
        """更新提交信息预览"""
        try:
            commit_info = f"提交信息预览 (版本: {new_version})\n"
            commit_info += "=" * 50 + "\n\n"
            
            # 显示当前会话的提交历史
            if self.current_session_commits:
                commit_info += "本次会话提交历史:\n"
                for i, commit in enumerate(self.current_session_commits, 1):
                    commit_info += f"{i}. {commit}\n"
                commit_info += "\n"
            else:
                commit_info += "本次会话暂无提交\n\n"
            
            # 显示即将执行的提交操作
            commit_info += "即将执行的提交操作:\n"
            commit_info += f"- 更新 debian/changelog 到版本 {new_version}\n"
            
            yaml_files = self.get_existing_yaml_files()
            if yaml_files:
                commit_info += "- 更新以下 YAML 文件:\n"
                for yaml_file in yaml_files:
                    commit_info += f"  - {yaml_file}\n"
            
            commit_info += f"\n提交信息: chore: Update version to {new_version}\n"
            
            # 更新预览框
            self.commit_preview.config(state=tk.NORMAL)
            self.commit_preview.delete(1.0, tk.END)
            self.commit_preview.insert(1.0, commit_info)
            self.commit_preview.config(state=tk.DISABLED)
            
        except Exception as e:
            self.status_var.set(f"提交预览错误: {str(e)}")
    
    def get_existing_yaml_files(self) -> List[str]:
        """获取存在的 YAML 文件列表"""
        existing_files = []
        for yaml_file in self.default_yaml_files:
            full_path = os.path.join(self.project_path, yaml_file)
            if os.path.isfile(full_path):
                existing_files.append(yaml_file)
        return existing_files
    
    def read_yaml_file(self, yaml_file: str) -> str:
        """读取 YAML 文件内容"""
        full_path = os.path.join(self.project_path, yaml_file)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def extract_version_from_yaml(self, content: str) -> str:
        """从 YAML 内容中提取版本号"""
        version_match = re.search(r'version:\s*([0-9][0-9.]*)', content)
        if version_match:
            return version_match.group(1)
        return "未找到版本号"
    
    def update_yaml_content(self, content: str, new_version: str) -> str:
        """更新 YAML 内容中的版本号"""
        # 将 Debian 版本格式 (x.y.z-r) 转换为 linglong 格式 (x.y.z.r)
        linglong_version = new_version.replace('-', '.')
        print(linglong_version)
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.strip().startswith('version:'):
                version_match = re.search(r'version:\s*([0-9][0-9.]*)', line)
                if version_match:
                    old_version = version_match.group(1)
                    new_line = line.replace(old_version, linglong_version)
                    print(new_line, version_match, old_version)
                    updated_lines.append(new_line)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        return '\n'.join(updated_lines)
    
    def get_git_log(self) -> str:
        """获取 Git 提交历史"""
        original_cwd = os.getcwd()
        os.chdir(self.project_path)
        
        try:
            # 获取 changelog 文件的提交历史
            result = subprocess.run(
                ['git', 'log', '--oneline', 'debian/changelog'],
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                return "  * 初始版本"
            
            # 解析输出，取第一个提交的 hash
            lines = result.stdout.strip().split('\n')
            if not lines:
                return "  * 初始版本"
            
            first_commit_hash = lines[0].split()[0]
            
            # 获取从该提交到当前的所有提交信息
            log_result = subprocess.run(
                ['git', 'log', '--format=  * %s', f'{first_commit_hash}..'],
                capture_output=True,
                text=True
            )
            
            if log_result.stdout.strip():
                return log_result.stdout
            else:
                return "  * 无新功能提交"
                
        except Exception as e:
            return f"  * 获取提交历史失败: {str(e)}"
        finally:
            os.chdir(original_cwd)
    
    def update_diff_preview(self, new_version: str):
        """更新 git diff 预览"""
        # 先模拟应用更改，然后获取 diff
        try:
            # 创建临时目录来模拟更改
            with tempfile.TemporaryDirectory() as temp_dir:
                # 复制 debian 目录到临时目录
                debian_src = os.path.join(self.project_path, "debian")
                debian_dest = os.path.join(temp_dir, "debian")
                shutil.copytree(debian_src, debian_dest)
                
                # 应用更改到临时文件
                self.apply_changes_to_temp(debian_dest, new_version)
                
                # 获取 diff
                diff = self.get_diff_between_dirs(debian_src, debian_dest)
                
                # 更新预览框
                self.diff_preview.config(state=tk.NORMAL)
                self.diff_preview.delete(1.0, tk.END)
                self.diff_preview.insert(1.0, diff if diff else "没有更改")
                self.diff_preview.config(state=tk.DISABLED)
                
        except Exception as e:
            self.status_var.set(f"Diff 错误: {str(e)}")
    
    def apply_changes_to_temp(self, temp_debian_dir: str, new_version: str):
        """应用更改到临时目录"""
        changelog_path = os.path.join(temp_debian_dir, "changelog")
        
        with open(changelog_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # 生成新的 changelog 条目
        current_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        git_log = self.get_git_log()
        
        new_entry = f"""{self.project_name} ({new_version}) unstable; urgency=medium

  * chore: Update version to {new_version}
{git_log}

 -- {self.full_maintainer}  {current_date}

"""
        
        # 写入新内容
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(new_entry)
            f.write(current_content)
    
    def get_diff_between_dirs(self, dir1: str, dir2: str) -> str:
        """获取两个目录之间的差异"""
        try:
            # 使用 diff 命令比较两个目录
            result = subprocess.run(
                ['diff', '-urN', dir1, dir2],
                capture_output=True,
                text=True
            )
            return result.stdout
        except:
            return ""
    
    def modify_version(self):
        """修改版本并提交到 Git"""
        new_version = self.new_version_var.get().strip()
        
        if not new_version:
            messagebox.showerror("错误", "请输入新版本号")
            return
        
        if not re.match(r'^\d+\.\d+\.\d+(?:\.\d+)?(?:-\d+)?$', new_version):
            messagebox.showerror("错误", "版本号格式不正确，应为 x.y.z 或 x.y.z.w 或 x.y.z-r")
            return
        
        try:
            # 更新 changelog 文件
            self.update_changelog_file(new_version)
            
            # 刷新 YAML 配置表格
            self.refresh_preview()
            
            # 询问是否提交到 Git
            if messagebox.askyesno("确认提交", f"是否将版本 {new_version} 提交到 Git？"):
                if self.commit_to_git(new_version):
                    messagebox.showinfo("成功", f"版本已更新为 {new_version} 并提交到 Git")
                    self.status_var.set(f"版本更新成功: {new_version}")
                    # 刷新当前版本显示
                    self.current_version = new_version
                    self.current_version_var.set(new_version)
                else:
                    messagebox.showerror("错误", "Git 提交失败")
            else:
                messagebox.showinfo("已取消", "版本已更新但未提交到 Git")
                self.status_var.set(f"版本已更新: {new_version} (未提交)")
                self.current_version = new_version
                self.current_version_var.set(new_version)
                
        except Exception as e:
            messagebox.showerror("错误", f"修改版本时出错: {str(e)}")
            self.status_var.set(f"错误: {str(e)}")
    
    def apply_changes_to_actual(self, new_version: str):
        """应用更改到实际文件"""
        # 更新 changelog
        self.update_changelog_file(new_version)
        
        # 更新 YAML 文件
        self.update_yaml_files(new_version)
    
    def update_changelog_file(self, new_version: str):
        """更新 changelog 文件"""
        changelog_path = os.path.join(self.project_path, "debian/changelog")
        
        # 备份原文件
        backup_path = changelog_path + ".bak"
        shutil.copy2(changelog_path, backup_path)
        
        try:
            with open(changelog_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # 生成新的 changelog 条目
            current_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            git_log = self.get_git_log()
            
            new_entry = f"""{self.project_name} ({new_version}) unstable; urgency=medium

  * chore: Update version to {new_version}
{git_log}
 -- {self.full_maintainer}  {current_date}

"""
            
            # 写入新内容
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(new_entry)
                f.write(current_content)
            
            # 验证更改
            with open(changelog_path, 'r', encoding='utf-8') as f:
                updated_content = f.read()
                if new_version not in updated_content:
                    raise Exception("changelog 更改应用失败")
            
            # 删除备份文件
            os.remove(backup_path)
            
        except Exception as e:
            # 恢复备份
            if os.path.exists(backup_path):
                shutil.move(backup_path, changelog_path)
            raise e
    
    def update_yaml_files(self, new_version: str):
        """批量更新所有 YAML 文件"""
        yaml_files = self.get_existing_yaml_files()
        updated_count = 0
        
        for yaml_file in yaml_files:
            try:
                self.replace_single_yaml(yaml_file, new_version)
                updated_count += 1
            except Exception as e:
                self.status_var.set(f"更新 {yaml_file} 失败: {str(e)}")
        
        if updated_count > 0:
            self.status_var.set(f"已批量更新 {updated_count} 个 YAML 文件")
    
    def commit_to_git(self, new_version: str) -> bool:
        """提交更改到 Git（使用 amend 如果已有提交）"""
        original_cwd = os.getcwd()
        os.chdir(self.project_path)
        
        try:
            # 设置 Git 用户信息
            subprocess.run(['git', 'config', 'user.name', self.maintainer], check=True)
            subprocess.run(['git', 'config', 'user.email', self.email], check=True)
            
            # 添加更改的文件
            subprocess.run(['git', 'add', 'debian/changelog'], check=True)
            
            # 检查是否有未提交的更改
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if not result.stdout.strip():
                self.status_var.set("没有需要提交的更改")
                return True
            
            commit_message = f"""chore: Update version to {new_version}
    
- update version to {new_version}

 log: update version to {new_version}"""
            
            # 检查是否是本次会话的第一次提交
            if not self.last_commit_hash:
                # 第一次提交，创建新提交
                subprocess.run(['git', 'commit', '-m', commit_message], check=True)
                # 记录提交hash
                result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
                self.last_commit_hash = result.stdout.strip()
                self.current_session_commits.append(f"{new_version} - 初始提交")
                self.status_var.set("创建新提交")
            else:
                # 后续提交，使用 amend 追加到本次提交
                subprocess.run(['git', 'commit', '--amend', '--no-edit'], check=True)
                self.current_session_commits.append(f"{new_version} - 追加提交")
                self.status_var.set("使用 amend 追加提交")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.status_var.set(f"Git 错误: {str(e)}")
            return False
        finally:
            os.chdir(original_cwd)
    
    def run(self):
        """运行 GUI 应用"""
        self.root.mainloop()


def parse_arguments():
    """解析命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debian 包版本更新 GUI 工具")
    parser.add_argument('project_path', nargs='?', help='项目目录路径')
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    app = DebianVersionGUI()
    
    # 如果通过命令行指定了项目路径，自动加载
    if args.project_path:
        app.path_var.set(args.project_path)
        app.load_project()
    
    app.run()


if __name__ == "__main__":
    main()