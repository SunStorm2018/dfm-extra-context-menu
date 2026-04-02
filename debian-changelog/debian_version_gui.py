#!/usr/bin/env python3
"""
Debian Changelog 版本更新 GUI 工具
功能：提供图形界面来更新 Debian 包版本，实时预览更改并提交到 Git
参考项目: https://gitee.com/sunstom/changelog-gui.git
"""

import os
import sys
import re
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class GitWrapper:
    """Git 操作封装类"""
    
    def __init__(self, repo_path: str = ""):
        self.repo_path = repo_path
    
    def set_repository_path(self, path: str):
        """设置仓库路径"""
        self.repo_path = path
    
    def get_repository_path(self) -> str:
        """获取仓库路径"""
        return self.repo_path
    
    def is_git_repository(self) -> bool:
        """检查是否是 Git 仓库"""
        if not self.repo_path:
            return False
        git_dir = os.path.join(self.repo_path, ".git")
        return os.path.isdir(git_dir)
    
    def get_author_info(self) -> Dict[str, str]:
        """获取 Git 配置的作者信息"""
        author_info = {"name": "unknown", "email": "unknown@unknown.com"}
        
        if not self.repo_path:
            return author_info
        
        try:
            # 优先获取仓库级别的配置
            result = subprocess.run(
                ["git", "config", "--local", "user.name"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                author_info["name"] = result.stdout.strip()
            
            result = subprocess.run(
                ["git", "config", "--local", "user.email"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                author_info["email"] = result.stdout.strip()
            
            # 如果本地配置不存在，尝试全局配置
            if author_info["name"] == "unknown":
                result = subprocess.run(
                    ["git", "config", "--global", "user.name"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    author_info["name"] = result.stdout.strip()
            
            if author_info["email"] == "unknown@unknown.com":
                result = subprocess.run(
                    ["git", "config", "--global", "user.email"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    author_info["email"] = result.stdout.strip()
        except Exception:
            pass
        
        return author_info
    
    def get_commits_since_last_file_change(self, filepath: str) -> List[Dict[str, str]]:
        """获取指定文件最后一次修改到当前的所有提交信息"""
        commits = []
        
        if not self.repo_path or not self.is_git_repository():
            return commits
        
        try:
            # 获取文件最后一次修改的提交哈希（完整哈希）
            result = subprocess.run(
                ["git", "log", "-n", "1", "--format=%H", "--", filepath],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            last_commit = result.stdout.strip()
            
            if not last_commit:
                return commits
            
            # 获取从该提交之后的所有提交（不包括该提交）
            # 使用 <commit>.. 格式，这与 ^commit..HEAD 等价
            result = subprocess.run(
                ["git", "log", "--format=%h|%s", f"{last_commit}..", "--no-merges"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0], "subject": parts[1]})
        except Exception as e:
            print(f"Error getting commits: {e}")
        
        return commits
    
    def get_unstaged_files(self) -> List[str]:
        """获取未暂存的文件列表"""
        if not self.repo_path or not self.is_git_repository():
            return []
        
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return files
        except Exception:
            return []
    
    def get_worktree_diff(self) -> str:
        """获取工作区的 git diff"""
        if not self.repo_path or not self.is_git_repository():
            return ""
        
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "--color=never"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception as e:
            return f"Error getting diff: {str(e)}"
    
    def reset_hard_last_commit(self) -> str:
        """硬重置到最后一次提交或回退一次提交"""
        if not self.repo_path or not self.is_git_repository():
            return "Not a git repository"
        
        try:
            unstaged_files = self.get_unstaged_files()
            
            if not unstaged_files:
                # 没有未暂存的文件，回退到上一个提交
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD~1"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return "Reset to HEAD~1"
            else:
                # 有未暂存的文件，重置到当前提交
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return "Reset to HEAD"
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr or str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def commit_all(self, message: str) -> Dict[str, Any]:
        """提交所有更改"""
        result = {"success": False, "commit_hash": "", "error": ""}
        
        if not self.repo_path or not self.is_git_repository():
            result["error"] = "Not a git repository"
            return result
        
        try:
            # 添加所有更改
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 提交
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 获取提交哈希
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            result["success"] = True
            result["commit_hash"] = hash_result.stdout.strip()
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def push(self) -> Dict[str, Any]:
        """推送到远程仓库"""
        result = {"success": False, "error": ""}
        
        if not self.repo_path or not self.is_git_repository():
            result["error"] = "Not a git repository"
            return result
        
        try:
            subprocess.run(
                ["git", "push"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            result["success"] = True
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_current_branch(self) -> str:
        """获取当前分支名称"""
        if not self.repo_path or not self.is_git_repository():
            return ""
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def get_remote_url(self) -> str:
        """获取远程仓库 URL"""
        if not self.repo_path or not self.is_git_repository():
            return ""
        
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return ""


class ChangelogEntry:
    """Changelog 条目类"""
    
    def __init__(self):
        self.package_name = ""
        self.full_version = ""
        self.major_version = "0"
        self.minor_version = "0"
        self.patch_version = "0"
        self.downstream_version = ""
        self.distribution = "unstable"
        self.urgency = "medium"
        self.changes = []
        self.maintainer = ""
        self.email = ""
        self.date = datetime.now()
    
    def parse_from_file(self, filepath: str) -> bool:
        """从 changelog 文件解析第一条条目"""
        if not os.path.isfile(filepath):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析第一行
            first_line = content.split('\n')[0]
            
            # 匹配格式: package (version) distribution; urgency=level
            pattern = r'^([a-zA-Z0-9-]+)\s*\(([^\)]+)\)\s+([^;]+);\s+urgency=([^\s]+)'
            match = re.match(pattern, first_line)
            
            if match:
                self.package_name = match.group(1)
                self.full_version = match.group(2)
                self.distribution = match.group(3)
                self.urgency = match.group(4)
                
                # 解析版本号
                self._parse_version(self.full_version)
                
                return True
        except Exception:
            pass
        
        return False
    
    def _parse_version(self, version: str):
        """解析版本号"""
        # 分离下游版本号
        if '-' in version:
            base_version, downstream = version.rsplit('-', 1)
            self.downstream_version = downstream
        else:
            base_version = version
            self.downstream_version = ""
        
        # 解析主版本号
        parts = base_version.split('.')
        if len(parts) >= 3:
            self.major_version = parts[0]
            self.minor_version = parts[1]
            self.patch_version = parts[2]
        elif len(parts) == 2:
            self.major_version = parts[0]
            self.minor_version = parts[1]
            self.patch_version = "0"
        elif len(parts) == 1:
            self.major_version = parts[0]
            self.minor_version = "0"
            self.patch_version = "0"
    
    def to_changelog_string(self) -> str:
        """转换为 changelog 格式字符串"""
        date_str = self.date.strftime('%a, %d %b %Y %H:%M:%S %z')
        
        changelog = f"{self.package_name} ({self.full_version}) {self.distribution}; urgency={self.urgency}\n\n"
        
        for change in self.changes:
            changelog += f"  * {change}\n"
        
        changelog += f"\n -- {self.maintainer} <{self.email}>  {date_str}\n"
        
        return changelog
    
    def is_valid(self) -> bool:
        """检查是否有效"""
        return bool(self.package_name and self.full_version)


class DebianVersionGUI:
    """Debian 版本更新 GUI 应用"""
    
    # YAML 配置列表
    YAML_CONFIGS = [
        {"path": "linglong.yaml", "widget": "ll"},
        {"path": "sw64/linglong.yaml", "widget": "sw_ll"},
        {"path": "arm64/linglong.yaml", "widget": "arm_ll"},
        {"path": "loong64/linglong.yaml", "widget": "loong_ll"},
        {"path": "mips64/linglong.yaml", "widget": "mips_ll"}
    ]
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Debian Changelog GUI")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        self.root.minsize(700, 600)  # 设置最小窗口大小，防止内容被裁剪
        
        # Git 操作封装
        self.git = GitWrapper()
        
        # Changelog 条目
        self.current_changelog = ChangelogEntry()
        self.new_changelog = ChangelogEntry()
        
        # 设置文件路径
        self.settings_file = os.path.expanduser("~/.config/debian-changelog-gui/settings.json")
        self.history = []
        self.project_history = []  # 项目路径历史记录
        
        # 创建界面
        self.create_widgets()
        
        # 加载设置
        self.load_settings()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 使用 grid 布局以更好地控制各个区域
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 配置主容器网格权重 - 确保预览区域可以扩展，但底部区域固定
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(4, weight=1)  # 预览区域可以扩展
        
        # === 顶部区域：项目路径和作者信息 ===
        top_frame = ttk.Frame(main_container)
        top_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 10))
        
        # 项目路径
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 项目路径输入框
        self.project_path_var = tk.StringVar()
        self.project_path_entry = ttk.Entry(path_frame, textvariable=self.project_path_var)
        self.project_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.project_path_entry.bind('<FocusOut>', self.on_project_path_changed)
        
        # 历史项目下拉列表
        self.project_history_var = tk.StringVar()
        self.project_history_combo = ttk.Combobox(path_frame, textvariable=self.project_history_var, 
                                                  width=30, state='readonly')
        self.project_history_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.project_history_combo.bind('<<ComboboxSelected>>', self.on_history_project_selected)
        
        ttk.Button(path_frame, text="Open Project", command=self.browse_project).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(path_frame, text="Refresh", command=self.refresh_all).pack(side=tk.LEFT, padx=(5, 0))
        
        # 作者信息
        author_frame = ttk.Frame(top_frame)
        author_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(author_frame, text="Author:").pack(side=tk.LEFT)
        self.author_var = tk.StringVar()
        self.author_entry = ttk.Entry(author_frame, textvariable=self.author_var, width=30)
        self.author_entry.pack(side=tk.LEFT, padx=(5, 15))
        self.author_entry.bind('<FocusOut>', self.on_author_changed)
        
        ttk.Label(author_frame, text="Email:").pack(side=tk.LEFT)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(author_frame, textvariable=self.email_var, width=30)
        self.email_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.email_entry.bind('<FocusOut>', self.on_email_changed)
        
        # === 版本信息区域 ===
        version_frame = ttk.LabelFrame(main_container, text="Version Info", padding="10")
        version_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))
        
        # 当前版本
        ttk.Label(version_frame, text="Current Version:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.current_version_var = tk.StringVar(value="--")
        ttk.Entry(version_frame, textvariable=self.current_version_var, width=30, state='readonly').grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 20))
        
        # 新版本
        ttk.Label(version_frame, text="New Version:").grid(row=0, column=2, sticky=tk.W, pady=5)
        self.new_version_var = tk.StringVar()
        self.new_version_entry = ttk.Entry(version_frame, textvariable=self.new_version_var, width=30)
        self.new_version_entry.grid(row=0, column=3, sticky=tk.W, pady=5, padx=(5, 0))
        self.new_version_entry.bind('<FocusOut>', self.on_new_version_changed)
        
        # 版本类型选择
        version_type_frame = ttk.Frame(version_frame)
        version_type_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        self.version_type_var = tk.StringVar(value="patch")
        ttk.Radiobutton(version_type_frame, text="major", variable=self.version_type_var, 
                       value="major", command=self.on_version_type_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(version_type_frame, text="minor", variable=self.version_type_var, 
                       value="minor", command=self.on_version_type_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(version_type_frame, text="patch", variable=self.version_type_var, 
                       value="patch", command=self.on_version_type_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(version_type_frame, text="downstream", variable=self.version_type_var, 
                       value="downstream", command=self.on_version_type_changed).pack(side=tk.LEFT)
        
        # === YAML 配置区域 ===
        yaml_frame = ttk.LabelFrame(main_container, text="YAML Configuration", padding="10")
        yaml_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 10))
        
        # 选择按钮
        yaml_select_frame = ttk.Frame(yaml_frame)
        yaml_select_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(yaml_select_frame, text="Select All", command=self.select_all_yaml).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(yaml_select_frame, text="Select None", command=self.select_none_yaml).pack(side=tk.LEFT)
        
        # YAML 配置列表
        self.yaml_widgets = {}
        yaml_list_frame = ttk.Frame(yaml_frame)
        yaml_list_frame.pack(fill=tk.BOTH, expand=True)
        
        for i, config in enumerate(self.YAML_CONFIGS):
            row_frame = ttk.Frame(yaml_list_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # 复选框
            checkbox_var = tk.BooleanVar(value=True)
            checkbox = ttk.Checkbutton(row_frame, variable=checkbox_var)
            checkbox.pack(side=tk.LEFT, padx=(0, 5))
            
            # 文件名
            ttk.Label(row_frame, text=config["path"], width=20).pack(side=tk.LEFT)
            
            # 旧版本
            old_version_var = tk.StringVar(value="--")
            old_version_label = ttk.Label(row_frame, textvariable=old_version_var, width=15)
            old_version_label.pack(side=tk.LEFT, padx=(5, 5))
            
            # 新版本
            new_version_var = tk.StringVar()
            new_version_entry = ttk.Entry(row_frame, textvariable=new_version_var, width=20)
            new_version_entry.pack(side=tk.LEFT, padx=(5, 0))
            
            self.yaml_widgets[config["widget"]] = {
                "checkbox_var": checkbox_var,
                "old_version_var": old_version_var,
                "new_version_var": new_version_var,
                "config": config
            }
        
        # === 预览区域 ===
        preview_frame = ttk.LabelFrame(main_container, text="Preview", padding="10")
        preview_frame.grid(row=4, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        # 标签页
        self.notebook = ttk.Notebook(preview_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Changelog 标签页
        changelog_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(changelog_tab, text="ChangeLog")
        self.changelog_preview = scrolledtext.ScrolledText(changelog_tab, width=80, height=15)
        self.changelog_preview.pack(fill=tk.BOTH, expand=True)
        
        # Commit Info 标签页
        commit_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(commit_tab, text="Commit Info")
        self.commit_preview = scrolledtext.ScrolledText(commit_tab, width=80, height=15)
        self.commit_preview.pack(fill=tk.BOTH, expand=True)
        
        # Git Log 标签页
        git_log_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(git_log_tab, text="Git Log")
        self.git_log_preview = scrolledtext.ScrolledText(git_log_tab, width=80, height=15)
        self.git_log_preview.pack(fill=tk.BOTH, expand=True)
        
        # === 底部按钮区域 ===
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=5, column=0, sticky=tk.EW, pady=(0, 5))
        
        ttk.Button(button_frame, text="Gitk", command=self.open_gitk).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Revert", command=self.revert_changes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Open Remote", command=self.open_remote).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Frame(button_frame).pack(side=tk.LEFT, expand=True)  # Spacer
        
        ttk.Button(button_frame, text="Update", command=self.update_version).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Commit", command=self.commit_changes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Push", command=self.push_changes).pack(side=tk.LEFT)
        
        # === 状态栏 ===
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_container, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, sticky=tk.EW, pady=(5, 0))
    
    def browse_project(self):
        """浏览选择项目路径"""
        path = filedialog.askdirectory(title="Select Project Directory", initialdir=os.path.expanduser("~"))
        if path:
            self.project_path_var.set(path)
            self.on_project_path_changed(None)
    
    def on_history_project_selected(self, event):
        """从历史记录中选择项目"""
        selected_path = self.project_history_var.get()
        if selected_path:
            self.project_path_var.set(selected_path)
            self.on_project_path_changed(None)
    
    def on_project_path_changed(self, event):
        """项目路径改变时的处理"""
        project_path = self.project_path_var.get().strip()
        
        if not project_path or not os.path.isdir(project_path):
            return
        
        self.git.set_repository_path(project_path)
        
        if not self.git.is_git_repository():
            self.status_var.set("Error: Not a git repository")
            messagebox.showerror("Error", "Selected directory is not a git repository!")
            return
        
        # 添加到项目历史记录
        self.add_to_project_history(project_path)
        
        # 加载作者信息
        author_info = self.git.get_author_info()
        self.author_var.set(author_info["name"])
        self.email_var.set(author_info["email"])
        
        # 解析当前 changelog
        changelog_path = os.path.join(project_path, "debian/changelog")
        if self.current_changelog.parse_from_file(changelog_path):
            self.current_version_var.set(self.current_changelog.full_version)
            
            # 初始化新 changelog
            self.new_changelog.package_name = self.current_changelog.package_name
            self.new_changelog.distribution = self.current_changelog.distribution
            self.new_changelog.urgency = self.current_changelog.urgency
            self.new_changelog.maintainer = author_info["name"]
            self.new_changelog.email = author_info["email"]
            self.new_changelog.date = datetime.now()
            
            # 触发版本类型改变以生成新版本号
            self.on_version_type_changed()
        else:
            self.status_var.set("Error: Failed to parse changelog")
        
        # 更新 YAML 配置
        self.update_yaml_config()
        
        # 保存设置
        self.save_settings()
    
    def on_author_changed(self, event):
        """作者改变时的处理"""
        self.new_changelog.maintainer = self.author_var.get()
        self.update_changelog_preview()
        self.update_commit_preview()
        self.save_settings()
    
    def on_email_changed(self, event):
        """邮箱改变时的处理"""
        self.new_changelog.email = self.email_var.get()
        self.update_changelog_preview()
        self.update_commit_preview()
        self.save_settings()
    
    def on_version_type_changed(self):
        """版本类型改变时的处理"""
        if not self.current_changelog.is_valid():
            return
        
        version_type = self.version_type_var.get()
        
        if version_type == "major":
            major = int(self.current_changelog.major_version) + 1
            minor = 0
            patch = 0
            downstream = self.current_changelog.downstream_version or "1"
        elif version_type == "minor":
            major = int(self.current_changelog.major_version)
            minor = int(self.current_changelog.minor_version) + 1
            patch = 0
            downstream = self.current_changelog.downstream_version or "1"
        elif version_type == "patch":
            major = int(self.current_changelog.major_version)
            minor = int(self.current_changelog.minor_version)
            patch = int(self.current_changelog.patch_version) + 1
            downstream = self.current_changelog.downstream_version or "1"
        else:  # downstream
            major = int(self.current_changelog.major_version)
            minor = int(self.current_changelog.minor_version)
            patch = int(self.current_changelog.patch_version)
            downstream = str(int(self.current_changelog.downstream_version or "1") + 1)
        
        # 构建新版本号
        base_version = f"{major}.{minor}.{patch}"
        if self.current_changelog.downstream_version:
            new_version = f"{base_version}-{downstream}"
        else:
            new_version = base_version
        
        self.new_changelog.full_version = new_version
        self.new_changelog.major_version = str(major)
        self.new_changelog.minor_version = str(minor)
        self.new_changelog.patch_version = str(patch)
        self.new_changelog.downstream_version = downstream
        
        self.new_version_var.set(new_version)
        self.refresh_all()
    
    def on_new_version_changed(self, event):
        """新版本号改变时的处理"""
        new_version = self.new_version_var.get().strip()
        if new_version:
            self.new_changelog.full_version = new_version
            self.new_changelog._parse_version(new_version)
            self.refresh_all()
    
    def select_all_yaml(self):
        """选择所有 YAML"""
        for widget in self.yaml_widgets.values():
            widget["checkbox_var"].set(True)
    
    def select_none_yaml(self):
        """取消选择所有 YAML"""
        for widget in self.yaml_widgets.values():
            widget["checkbox_var"].set(False)
    
    def update_yaml_config(self):
        """更新 YAML 配置"""
        project_path = self.git.get_repository_path()
        
        for widget_name, widget in self.yaml_widgets.items():
            config = widget["config"]
            yaml_path = os.path.join(project_path, config["path"])
            
            if os.path.isfile(yaml_path):
                old_version = self.extract_version_from_yaml(yaml_path)
                widget["old_version_var"].set(old_version)
                
                # 生成新版本号（替换旧版本号中的当前版本为新版本）
                new_version = old_version.replace(
                    self.current_changelog.full_version,
                    self.new_changelog.full_version
                )
                widget["new_version_var"].set(new_version)
            else:
                widget["old_version_var"].set("--")
                widget["new_version_var"].set("")
    
    def extract_version_from_yaml(self, filepath: str) -> str:
        """从 YAML 文件中提取版本号"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 匹配 version: xxx 格式
            match = re.search(r'^\s*version\s*:\s*([\w\.\-]+)\s*(?:#.*)?$', content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception:
            pass
        
        return ""
    
    def update_yaml_file(self, filepath: str, old_version: str, new_version: str) -> bool:
        """更新 YAML 文件中的版本号"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace(old_version, new_version)
            
            if new_content == content:
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        except Exception as e:
            print(f"Error updating YAML file {filepath}: {e}")
            return False
    
    def refresh_all(self):
        """刷新所有预览"""
        self.update_changelog_preview()
        self.update_commit_preview()
        self.update_git_log_preview()
        self.update_yaml_config()
    
    def update_changelog_preview(self):
        """更新 changelog 预览"""
        # 生成变更列表
        self.new_changelog.changes = [f"chore: Update version to {self.new_changelog.full_version}"]
        
        # 添加 git 提交信息
        commits = self.git.get_commits_since_last_file_change("debian/changelog")
        for commit in commits:
            self.new_changelog.changes.append(commit["subject"])
        
        changelog_text = self.new_changelog.to_changelog_string()
        
        self.changelog_preview.config(state=tk.NORMAL)
        self.changelog_preview.delete(1.0, tk.END)
        self.changelog_preview.insert(1.0, changelog_text)
        self.changelog_preview.config(state=tk.DISABLED)
    
    def update_commit_preview(self):
        """更新提交信息预览"""
        version = self.new_changelog.full_version
        commit_message = f"chore: Update version to {version}\n\n- update version to {version}\n\nlog: update version to {version}"
        
        self.commit_preview.config(state=tk.NORMAL)
        self.commit_preview.delete(1.0, tk.END)
        self.commit_preview.insert(1.0, commit_message)
        self.commit_preview.config(state=tk.DISABLED)
    
    def update_git_log_preview(self):
        """更新 git log 预览"""
        diff_text = self.git.get_worktree_diff()
        
        self.git_log_preview.config(state=tk.NORMAL)
        self.git_log_preview.delete(1.0, tk.END)
        self.git_log_preview.insert(1.0, diff_text if diff_text else "No changes")
        self.git_log_preview.config(state=tk.DISABLED)
    
    def update_version(self):
        """更新版本"""
        project_path = self.git.get_repository_path()
        if not project_path:
            messagebox.showerror("Error", "No project selected!")
            return
        
        try:
            # 更新 changelog
            changelog_path = os.path.join(project_path, "debian/changelog")
            
            # 读取当前内容
            with open(changelog_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # 生成新内容
            new_changelog_text = self.new_changelog.to_changelog_string() + "\n" + current_content
            
            # 写入新内容
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(new_changelog_text)
            
            # 更新 YAML 文件
            for widget in self.yaml_widgets.values():
                if widget["checkbox_var"].get():
                    config = widget["config"]
                    yaml_path = os.path.join(project_path, config["path"])
                    
                    if os.path.isfile(yaml_path):
                        old_version = widget["old_version_var"].get()
                        new_version = widget["new_version_var"].get()
                        
                        if old_version and new_version:
                            if not self.update_yaml_file(yaml_path, old_version, new_version):
                                print(f"Warning: Failed to update {config['path']}")
            
            # 记录历史
            self.add_to_history(f"Updated to {self.new_changelog.full_version}")
            
            # 刷新预览
            self.update_git_log_preview()
            
            self.status_var.set(f"Updated to version {self.new_changelog.full_version}")
            messagebox.showinfo("Success", f"Version updated to {self.new_changelog.full_version}")
            
            # 保存设置
            self.save_settings()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update version: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
    
    def commit_changes(self):
        """提交更改"""
        commit_message = self.commit_preview.get(1.0, tk.END).strip()
        
        if not commit_message:
            messagebox.showerror("Error", "No commit message!")
            return
        
        result = self.git.commit_all(commit_message)
        
        if result["success"]:
            self.status_var.set(f"Committed: {result['commit_hash']}")
            messagebox.showinfo("Success", f"Changes committed successfully!\nCommit: {result['commit_hash']}")
            self.update_git_log_preview()
        else:
            messagebox.showerror("Error", f"Commit failed: {result['error']}")
            self.status_var.set(f"Commit failed: {result['error']}")
    
    def push_changes(self):
        """推送更改"""
        result = self.git.push()
        
        if result["success"]:
            self.status_var.set("Pushed successfully")
            messagebox.showinfo("Success", "Changes pushed successfully!")
        else:
            messagebox.showerror("Error", f"Push failed: {result['error']}")
            self.status_var.set(f"Push failed: {result['error']}")
    
    def open_gitk(self):
        """打开 gitk"""
        project_path = self.git.get_repository_path()
        if not project_path:
            messagebox.showerror("Error", "No project selected!")
            return
        
        try:
            subprocess.Popen(["gitk"], cwd=project_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open gitk: {str(e)}")
    
    def revert_changes(self):
        """回退更改"""
        project_path = self.git.get_repository_path()
        if not project_path:
            messagebox.showerror("Error", "No project selected!")
            return
        
        if not messagebox.askyesno("Confirm", "Are you sure you want to revert all changes?"):
            return
        
        try:
            info = self.git.reset_hard_last_commit()
            self.status_var.set(info)
            messagebox.showinfo("Success", info)
            
            # 刷新项目信息
            self.on_project_path_changed(None)
            self.update_git_log_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to revert changes: {str(e)}")
    
    def open_remote(self):
        """打开远程仓库 URL"""
        remote_url = self.git.get_remote_url()
        
        if not remote_url:
            messagebox.showerror("Error", "无法获取远程仓库URL")
            return
        
        # 转换为浏览器 URL
        if remote_url.startswith("git@"):
            # git@github.com:user/repo.git -> https://github.com/user/repo
            match = re.match(r'git@([^:]+):(.+)(?:\.git)?', remote_url)
            if match:
                host = match.group(1)
                path = match.group(2)
                remote_url = f"https://{host}/{path}"
        elif remote_url.startswith("git://"):
            remote_url = remote_url.replace("git://", "https://").rstrip(".git")
        elif remote_url.startswith("http"):
            remote_url = remote_url.rstrip(".git")
        
        # 确保URL以http://或https://开头
        if not remote_url.startswith("http://") and not remote_url.startswith("https://"):
            remote_url = "https://" + remote_url
        
        # 获取当前分支信息
        current_branch = self.git.get_current_branch()
        if current_branch and current_branch != "main" and current_branch != "master":
            # 如果不是默认分支，添加分支路径
            # 例如：https://github.com/user/repo -> https://github.com/user/repo/tree/branch_name
            remote_url = f"{remote_url}/tree/{current_branch}"
        
        try:
            import webbrowser
            webbrowser.open(remote_url)
            self.status_var.set(f"已打开远程仓库: {remote_url}")
        except Exception as e:
            messagebox.showerror("Error", f"无法打开远程仓库: {remote_url}")
    
    def add_to_history(self, entry: str):
        """添加到历史记录"""
        self.history.insert(0, entry)
        if len(self.history) > 50:
            self.history.pop()
    
    def add_to_project_history(self, project_path: str):
        """添加项目到历史记录"""
        # 规范化路径
        project_path = os.path.normpath(project_path)
        
        # 如果已存在，先移除
        if project_path in self.project_history:
            self.project_history.remove(project_path)
        
        # 添加到开头
        self.project_history.insert(0, project_path)
        
        # 限制历史记录数量
        if len(self.project_history) > 10:
            self.project_history.pop()
        
        # 更新下拉列表
        self.update_project_history_combo()
    
    def update_project_history_combo(self):
        """更新项目历史下拉列表"""
        self.project_history_combo['values'] = self.project_history
    
    def load_settings(self):
        """加载设置"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 加载项目路径
                if "project_path" in settings and settings["project_path"]:
                    self.project_path_var.set(settings["project_path"])
                    self.on_project_path_changed(None)
                
                # 加载作者信息
                if "author" in settings:
                    self.author_var.set(settings["author"])
                if "email" in settings:
                    self.email_var.set(settings["email"])
                
                # 加载历史记录
                if "history" in settings:
                    self.history = settings["history"]
                
                # 加载项目历史记录
                if "project_history" in settings:
                    self.project_history = settings["project_history"]
                    self.update_project_history_combo()
                
                # 加载 YAML 选择状态
                if "yaml_states" in settings:
                    for widget_name, state in settings["yaml_states"].items():
                        if widget_name in self.yaml_widgets:
                            self.yaml_widgets[widget_name]["checkbox_var"].set(state)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            settings = {
                "project_path": self.project_path_var.get(),
                "author": self.author_var.get(),
                "email": self.email_var.get(),
                "history": self.history,
                "project_history": self.project_history,
                "yaml_states": {}
            }
            
            # 保存 YAML 选择状态
            for widget_name, widget in self.yaml_widgets.items():
                settings["yaml_states"][widget_name] = widget["checkbox_var"].get()
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    app = DebianVersionGUI()
    app.run()


if __name__ == "__main__":
    main()
