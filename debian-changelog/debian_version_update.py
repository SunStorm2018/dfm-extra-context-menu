#!/usr/bin/env python3
"""
Debian Changelog 自动生成脚本 (Python版本)
功能：自动生成changelog，创建版本提交，更新YAML文件版本，并提供可视化查看选项

作者: zhanghongyuan <zhanghongyuan@uniontech.com>
"""

import os
import sys
import re
import subprocess
import argparse
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

class DebianVersionUpdater:
    """Debian包版本更新器"""
    
    def __init__(self):
        # 配置信息
        self.maintainer = "zhanghongyuan"
        self.email = "zhanghongyuan@uniontech.com"
        self.full_maintainer = f"{self.maintainer} <{self.email}>"
        
        # 默认 YAML 文件路径配置
        self.default_yaml_files = [
            "sw64/linglong.yaml",
            "loong64/linglong.yaml", 
            "arm64/linglong.yaml",
            "mips64/linglong.yaml",
            "linglong.yaml"
        ]
        
        # 目录特定的 YAML 文件配置
        self.directory_yaml_files = {
            "sw64": "sw64/linglong.yaml",
            "loong64": "loong64/linglong.yaml",
            "arm64": "arm64/linglong.yaml",
            "mips64": "mips64/linglong.yaml",
            "root": "linglong.yaml",
            "all": "all"  # 特殊标记，表示使用所有默认文件
        }
        
        # 颜色定义
        self.colors = {
            'RED': '\033[0;31m',
            'GREEN': '\033[0;32m',
            'YELLOW': '\033[1;33m',
            'BLUE': '\033[0;34m',
            'PURPLE': '\033[0;35m',
            'CYAN': '\033[0;36m',
            'NC': '\033[0m'  # No Color
        }

    def log_info(self, message: str):
        """信息日志"""
        print(f"{self.colors['GREEN']}[INFO]{self.colors['NC']} {message}")

    def log_warn(self, message: str):
        """警告日志"""
        print(f"{self.colors['YELLOW']}[WARN]{self.colors['NC']} {message}")

    def log_error(self, message: str):
        """错误日志"""
        print(f"{self.colors['RED']}[ERROR]{self.colors['NC']} {message}")

    def log_step(self, message: str):
        """步骤日志"""
        print(f"{self.colors['BLUE']}[STEP]{self.colors['NC']} {message}")

    def log_debug(self, message: str):
        """调试日志"""
        print(f"{self.colors['PURPLE']}[DEBUG]{self.colors['NC']} {message}")

    def run_command(self, cmd: List[str], cwd: str = None, capture_output: bool = False) -> Tuple[bool, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                capture_output=capture_output, 
                text=True, 
                check=True
            )
            if capture_output:
                return True, result.stdout
            return True, ""
        except subprocess.CalledProcessError as e:
            if capture_output:
                return False, e.stderr
            return False, str(e)

    def check_requirements(self, target_dir: str) -> bool:
        """检查系统依赖"""
        self.log_step("检查系统依赖...")
        
        required_commands = ['git', 'dch', 'dpkg-parsechangelog']
        
        for cmd in required_commands:
            if not shutil.which(cmd):
                self.log_error(f"{cmd} 未安装，请先安装必要的包")
                return False
        
        # 检查是否是目录路径
        if target_dir != "." and os.path.isdir(target_dir):
            # 在指定目录中检查
            if not os.path.isdir(os.path.join(target_dir, ".git")):
                self.log_error(f"目录 {target_dir} 不是 git 仓库")
                return False
            
            if not os.path.isdir(os.path.join(target_dir, "debian")):
                self.log_error(f"目录 {target_dir} 没有 debian 文件夹")
                return False
        else:
            # 在当前目录中检查
            if not os.path.isdir(".git"):
                self.log_error("当前目录不是 git 仓库")
                return False
            
            if not os.path.isdir("debian"):
                self.log_error("当前目录没有 debian 文件夹，请在项目根目录运行脚本")
                return False
        
        return True

    def get_current_version(self, target_dir: str) -> str:
        """获取当前版本"""
        if target_dir == ".":
            changelog_path = "debian/changelog"
        else:
            changelog_path = os.path.join(target_dir, "debian/changelog")
        
        if os.path.isfile(changelog_path):
            try:
                success, output = self.run_command(
                    ['dpkg-parsechangelog', '-l', 'changelog', '-S', 'version'],
                    cwd=os.path.dirname(changelog_path),
                    capture_output=True
                )
                if success:
                    return output.strip()
            except:
                pass
        
        return "0.0.1-1"

    def generate_new_version(self, current_version: str, version_type: str) -> str:
        """生成新版本号"""
        self.log_step(f"生成新版本号 (当前: {current_version}, 类型: {version_type})")
        
        # 分离主版本号和Debian修订号
        had_revision = '-' in current_version
        if had_revision:
            base_version, debian_rev = current_version.rsplit('-', 1)
            if debian_rev.isdigit():
                debian_rev = int(debian_rev)
            else:
                # 如果修订号不是数字，重置为1
                base_version = current_version
                debian_rev = 1
                had_revision = True  # 保持有修订号
        else:
            base_version = current_version
            debian_rev = 1  # 如果没有修订号，默认为1
        
        # 解析主版本号
        version_parts = base_version.split('.')
        if len(version_parts) >= 3:
            try:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                patch = int(version_parts[2])
            except ValueError:
                # 如果版本号解析失败，使用默认值
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
            debian_rev = 1  # 主版本更新时重置修订号为1
        elif version_type == "minor":
            minor += 1
            patch = 0
            debian_rev = 1  # 次版本更新时重置修订号为1
        else:  # patch
            patch += 1
            debian_rev = 1  # 补丁版本更新时重置修订号为1
        
        # 构建新版本号
        new_base_version = f"{major}.{minor}.{patch}"
        
        # 如果原始版本没有修订号，新版本也不添加修订号
        if had_revision:
            return f"{new_base_version}-{debian_rev}"
        else:
            return new_base_version

    def get_project_name(self, target_dir: str) -> str:
        """从changelog中提取项目名称"""
        if target_dir == ".":
            changelog_path = "debian/changelog"
        else:
            changelog_path = os.path.join(target_dir, "debian/changelog")
        
        if os.path.isfile(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    # 提取项目名称，格式为：project (version) distribution; urgency=level
                    match = re.search(r'^([a-zA-Z0-9-]+)\s*\(', first_line)
                    if match:
                        return match.group(1)
            except:
                pass
        
        return "unknown-project"

    def get_git_log(self, target_dir: str) -> str:
        """获取两次changelog提交之间的git提交历史"""
        # 切换到目标目录
        original_cwd = os.getcwd()
        if target_dir != ".":
            os.chdir(target_dir)
        
        try:
            # 1. 获取changelog文件的提交历史，取第一个提交的hash
            cmd = ['git', 'log', '--oneline', 'debian/changelog']
            success, result = self.run_command(cmd, capture_output=True)
            
            if not success or not result.strip():
                self.log_warn("无法获取changelog提交历史，使用所有提交")
                # 如果获取失败，使用所有提交
                log_cmd = ['git', 'log', '--format=  * %s']
                success, log_entries = self.run_command(log_cmd, capture_output=True)
                if success and log_entries.strip():
                    return log_entries.strip()
                return "  * 初始版本"
            
            # 解析输出，取第一个提交的hash
            lines = result.strip().split('\n')
            if not lines:
                self.log_warn("changelog提交历史为空，使用所有提交")
                log_cmd = ['git', 'log', '--format=  * %s']
                success, log_entries = self.run_command(log_cmd, capture_output=True)
                if success and log_entries.strip():
                    return log_entries.strip()
                return "  * 初始版本"
            
            # 取第一个提交的hash（第一行的第一个单词）
            first_commit_hash = lines[0].split()[0]
            self.log_debug(f"找到changelog的第一个提交hash: {first_commit_hash}")
            
            # 2. 使用该hash获取从该提交到当前的所有提交信息
            log_cmd = ['git', 'log', '--format=  * %s', f'{first_commit_hash}..']
            success, log_entries = self.run_command(log_cmd, capture_output=True)
            
            if not success or not log_entries.strip():
                self.log_warn(f"无法获取从 {first_commit_hash} 开始的提交历史")
                return "  * 无新功能提交"
            
            # 直接返回所有提交，不进行任何过滤
            if not log_entries.strip():
                return "  * 无新功能提交"
            
            self.log_debug(f"找到 {len(log_entries.strip().split('\n'))} 条相关提交")
            
            return log_entries
        
        finally:
            # 切换回原目录
            if target_dir != ".":
                os.chdir(original_cwd)

    def generate_changelog(self, new_version: str, git_log: str, target_dir: str) -> bool:
        """生成 changelog"""
        self.log_step("生成Debian Changelog...")
        
        # 确定 debian 目录路径
        if target_dir == ".":
            debian_dir = "debian"
        else:
            debian_dir = os.path.join(target_dir, "debian")
        
        changelog_file = os.path.join(debian_dir, "changelog")
        
        if not os.path.isfile(changelog_file):
            self.log_error(f"Changelog文件不存在: {changelog_file}")
            return False
        
        # 获取项目名称
        project_name = self.get_project_name(target_dir)
        self.log_info(f"检测到项目名称: {project_name}")
        
        # 备份原文件
        backup_file = f"{changelog_file}.bak"
        shutil.copy2(changelog_file, backup_file)
        
        try:
            # 读取当前changelog内容
            with open(changelog_file, 'r', encoding='utf-8') as f:
                changelog_content = f.read()
            
            # 创建新的changelog条目
            current_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            new_entry = f"""{project_name} ({new_version}) unstable; urgency=medium
    
  * chore: Update version to {new_version}
{git_log}

 -- {self.full_maintainer}  {current_date}

"""
            
            # 将新条目插入到changelog开头
            with open(changelog_file, 'w', encoding='utf-8') as f:
                f.write(new_entry)
                f.write(changelog_content)
            
            # 检查是否成功更新
            with open(changelog_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if new_version in content:
                    self.log_info(f"Changelog 手动更新成功 - 版本: {new_version} (目录: {target_dir})")
                    os.remove(backup_file)
                    return True
                else:
                    self.log_error("Changelog 手动更新失败")
                    shutil.move(backup_file, changelog_file)
                    return False
        
        except Exception as e:
            self.log_error(f"Changelog 更新过程中出错: {e}")
            if os.path.exists(backup_file):
                shutil.move(backup_file, changelog_file)
            return False

    def get_yaml_files_for_directory(self, target_dir: str) -> List[str]:
        """根据目标目录获取 YAML 文件列表"""
        self.log_debug(f"获取 YAML 文件列表，目标目录: {target_dir}")
        
        if target_dir in self.directory_yaml_files:
            if target_dir == "all":
                return self.default_yaml_files
            else:
                return [self.directory_yaml_files[target_dir]]
        elif target_dir == ".":
            return self.default_yaml_files
        elif os.path.isdir(target_dir):
            # 在指定目录中查找 YAML 文件
            yaml_files = []
            for yaml_file in self.default_yaml_files:
                full_path = os.path.join(target_dir, yaml_file)
                if os.path.isfile(full_path):
                    yaml_files.append(full_path)
                    self.log_debug(f"找到文件: {full_path}")
                else:
                    self.log_warn(f"YAML 文件不存在，跳过: {full_path}")
            return yaml_files
        else:
            self.log_error(f"不支持的目录: {target_dir}")
            return []

    def update_yaml_files(self, new_version: str, yaml_files: List[str]) -> bool:
        """更新 YAML 文件中的版本信息"""
        self.log_step("更新 YAML 文件版本信息...")
        
        # 过滤存在的文件
        existing_files = [f for f in yaml_files if os.path.isfile(f)]
        
        if not existing_files:
            self.log_warn("没有找到任何存在的 YAML 文件，跳过更新")
            return True
        
        self.log_info(f"找到 {len(existing_files)} 个 YAML 文件需要处理:")
        for file in existing_files:
            self.log_info(f"  - {file}")
        
        # 将 Debian 版本格式 (x.y.z-r) 转换为 linglong 格式 (x.y.z.r)
        linglong_version = new_version.replace('-', '.')
        
        updated_count = 0
        for yaml_file in existing_files:
            self.log_info(f"处理 YAML 文件: {yaml_file}")
            
            # 备份原文件
            backup_file = f"{yaml_file}.bak"
            shutil.copy2(yaml_file, backup_file)
            
            try:
                # 读取文件内容
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单字符串替换：查找并替换版本号
                # 查找格式为 "version: x.y.z.w" 的行
                lines = content.split('\n')
                updated_lines = []
                old_version = None
                version_updated = False
                
                for line in lines:
                    # 检查是否是版本行
                    if line.strip().startswith('version:'):
                        # 提取当前版本号
                        version_match = re.search(r'version:\s*([0-9][0-9.]*)', line)
                        if version_match:
                            old_version = version_match.group(1)
                            # 替换版本号
                            new_line = line.replace(old_version, linglong_version)
                            updated_lines.append(new_line)
                            version_updated = True
                            self.log_info(f"在 {yaml_file} 中找到版本号: {old_version} → {linglong_version}")
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                if not version_updated:
                    self.log_warn(f"在 {yaml_file} 中未找到版本号，跳过更新")
                    continue
                
                # 写入新内容
                new_content = '\n'.join(updated_lines)
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                # 检查是否成功更新
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    updated_content = f.read()
                    if f"version: {linglong_version}" in updated_content or f'version: "{linglong_version}"' in updated_content:
                        updated_count += 1
                        os.remove(backup_file)
                        self.log_info(f"YAML 文件更新成功: {yaml_file}")
                    else:
                        self.log_warn(f"更新后未检测到新版本号，可能更新失败")
                        shutil.move(backup_file, yaml_file)
            
            except Exception as e:
                self.log_error(f"更新 YAML 文件时出错: {e}")
                if os.path.exists(backup_file):
                    shutil.move(backup_file, yaml_file)
        
        if updated_count > 0:
            self.log_info(f"成功更新 {updated_count}/{len(existing_files)} 个 YAML 文件")
            return True
        else:
            self.log_warn(f"没有成功更新任何 YAML 文件 (处理了 {len(existing_files)} 个文件)")
            return False

    def create_git_commit(self, version: str, yaml_files: List[str], target_dir: str) -> bool:
        """创建 git 提交"""
        self.log_step("创建Git提交...")
        
        # 切换到目标目录
        original_cwd = os.getcwd()
        if target_dir != ".":
            os.chdir(target_dir)
        
        try:
            # 设置 git 用户信息（仅本次操作）
            self.run_command(['git', 'config', 'user.name', self.maintainer])
            self.run_command(['git', 'config', 'user.email', self.email])
            
            # 添加更改的文件
            self.run_command(['git', 'add', 'debian/changelog'])
            
            # 添加存在的 YAML 文件到 git
            yaml_added = 0
            for yaml_file in yaml_files:
                if os.path.isfile(yaml_file):
                    success, _ = self.run_command(['git', 'add', yaml_file])
                    if success:
                        yaml_added += 1
                        self.log_debug(f"已添加 YAML 文件到 Git: {yaml_file}")
                    else:
                        self.log_warn(f"无法添加 YAML 文件到 git: {yaml_file}")
            
            self.log_info(f"添加了 {yaml_added} 个 YAML 文件到 Git")
            
            # 检查是否有文件需要提交
            success, status = self.run_command(['git', 'status', '--porcelain'], capture_output=True)
            if success and status.strip():
                # 创建提交 - 使用完整的提交信息格式
                commit_message = f"""chore: Update version to {version}
    
- update version to {version}

 log: update version to {version}"""
                
                success, _ = self.run_command(['git', 'commit', '-m', commit_message])
                if success:
                    self.log_info(f"Git 提交创建成功 - 版本: {version}")
                    return True
                else:
                    self.log_error("Git 提交创建失败")
                    return False
            else:
                self.log_warn("没有需要提交的更改，跳过 Git 提交")
                return True  # 没有更改不是错误
        
        except Exception as e:
            self.log_error(f"Git 提交过程中出错: {e}")
            return False
        finally:
            # 切换回原目录
            if target_dir != ".":
                os.chdir(original_cwd)

    def check_and_launch_gitk(self, target_dir: str, yaml_files: List[str]):
        """检查并启动 gitk"""
        self.log_step("检查可视化工具...")
        
        # 切换到目标目录
        original_cwd = os.getcwd()
        if target_dir != ".":
            os.chdir(target_dir)
        
        try:
            if shutil.which("gitk"):
                response = input("检测到 gitk 已安装，是否在 debian 目录启动 gitk？(y/N): ")
                if response.lower() in ['y', 'yes']:
                    self.log_info("启动 gitk...")
                    subprocess.Popen(['gitk', '.'], cwd='debian')
                else:
                    self.log_info("跳过 gitk 启动")
                    self.show_git_log(yaml_files)
            else:
                self.log_warn("未检测到 gitk，使用 git log 显示提交信息")
                self.show_git_log(yaml_files)
        
        finally:
            # 切换回原目录
            if target_dir != ".":
                os.chdir(original_cwd)

    def show_git_log(self, yaml_files: List[str]):
        """显示 git 日志"""
        self.log_info("显示最近提交历史...")
        self.run_command(['git', 'log', '--oneline', '-n', '5', '--graph', '--decorate'])
        
        print()
        self.log_info("显示当前更改...")
        self.run_command(['git', 'diff', '--stat'])
        
        # 检查是否有未提交的更改
        success, status = self.run_command(['git', 'status', '--porcelain'], capture_output=True)
        if success and status.strip():
            print()
            self.run_command(['git', 'diff'])
        
        # 显示 YAML 文件的更改
        has_yaml_changes = False
        for yaml_file in yaml_files:
            if os.path.isfile(yaml_file):
                success, diff = self.run_command(['git', 'diff', yaml_file], capture_output=True)
                if success and diff.strip():
                    if not has_yaml_changes:
                        print()
                        self.log_info("YAML 文件更改:")
                        has_yaml_changes = True
                    print()
                    self.log_info(f"显示 {yaml_file} 的更改:")
                    print(diff)

    def select_version_type(self, auto_confirm: bool = False) -> str:
        """用户交互选择版本类型"""
        if auto_confirm:
            return "patch"
        
        print("请选择版本更新类型:")
        print("1) 主要版本 (major)")
        print("2) 次要版本 (minor)") 
        print("3) 修订版本 (patch)")
        print("4) 手动输入版本号")
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "1":
            return "major"
        elif choice == "2":
            return "minor"
        elif choice == "3":
            return "patch"
        elif choice == "4":
            manual_version = input("请输入版本号 (格式: x.y.z-r): ").strip()
            return manual_version
        else:
            self.log_warn("无效选择，使用默认修订版本")
            return "patch"

    def confirm_operation(self, auto_confirm: bool, new_version: str, target_dir: str, yaml_files: List[str]) -> bool:
        """确认操作"""
        if auto_confirm:
            return True
        
        print()
        print(f"{self.colors['CYAN']}=== 操作摘要 ==={self.colors['NC']}")
        print(f"目标目录: {self.colors['GREEN']}{target_dir}{self.colors['NC']}")
        print(f"新版本号: {self.colors['GREEN']}{new_version}{self.colors['NC']}")
        print(f"影响的 YAML 文件:")
        
        existing_count = 0
        for yaml_file in yaml_files:
            if os.path.isfile(yaml_file):
                print(f"  - {self.colors['GREEN']}{yaml_file}{self.colors['NC']}")
                existing_count += 1
            else:
                print(f"  - {self.colors['YELLOW']}{yaml_file} (不存在，将跳过){self.colors['NC']}")
        
        print(f"实际处理文件: {self.colors['GREEN']}{existing_count}/{len(yaml_files)}{self.colors['NC']}")
        print()
        
        response = input("是否继续生成 changelog 和提交？(Y/n): ").strip().lower()
        return response in ['', 'y', 'yes']

    def parse_arguments(self):
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="Debian Changelog 自动生成脚本",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
目标目录:
   指定目录路径        在该目录的debian文件夹中执行操作
   sw64               更新 sw64/linglong.yaml
   loong64            更新 loong64/linglong.yaml
   arm64              更新 arm64/linglong.yaml
   mips64             更新 mips64/linglong.yaml
   root               更新 linglong.yaml (根目录)
   all                更新所有 YAML 文件 (默认)

示例:
  debian_version_update.py                               # 在当前目录更新所有 YAML 文件
  debian_version_update.py /path/to/project             # 在指定目录的debian文件夹中执行
  debian_version_update.py sw64                         # 只更新 sw64 目录的 YAML
  debian_version_update.py -t minor /path/to/project    # 在指定目录升级次要版本
  debian_version_update.py -v 2.0.0-1 all               # 指定版本号更新所有文件
  debian_version_update.py -y /path/to/project          # 自动确认，在指定目录执行
            """
        )
        
        parser.add_argument('-v', '--version', help='指定版本号 (例如: 1.2.3-1)')
        parser.add_argument('-t', '--type', choices=['major', 'minor', 'patch'], 
                           default='patch', help='版本类型: major, minor, patch')
        parser.add_argument('-y', '--yes', action='store_true', 
                           help='自动确认所有提示')
        parser.add_argument('--no-notify', action='store_true', 
                           help='禁用桌面通知')
        parser.add_argument('target_directory', nargs='?', default='.', 
                           help='目标目录路径或类型')
        
        return parser.parse_args()

    def main(self):
        """主函数"""
        args = self.parse_arguments()
        
        self.log_step(f"开始 Debian 包版本更新流程 - 目标目录: {args.target_directory}")
        
        # 检查环境
        if not self.check_requirements(args.target_directory):
            sys.exit(1)
        
        # 获取 YAML 文件列表
        yaml_files = self.get_yaml_files_for_directory(args.target_directory)
        self.log_info(f"配置的 YAML 文件: {yaml_files}")
        
        # 获取当前版本
        current_version = self.get_current_version(args.target_directory)
        self.log_info(f"当前版本: {current_version}")
        
        # 确定新版本号
        if args.version:
            new_version = args.version
            self.log_info(f"使用指定版本号: {new_version}")
        else:
            version_type = self.select_version_type(args.yes)
            if re.match(r'\d+\.\d+\.\d+', version_type):
                new_version = version_type
            else:
                new_version = self.generate_new_version(current_version, version_type)
        
        # 清理版本号，保留完整版本字符串（包括修订号）
        # 匹配格式: x.y.z 或 x.y.z.w 或 x.y.z-r
        version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?(?:-\d+)?)', new_version)
        if version_match:
            new_version = version_match.group(1)
        else:
            self.log_error("无法生成有效的新版本号")
            sys.exit(1)
        
        self.log_info(f"新版本: {new_version}")
        
        # 确认操作
        if not self.confirm_operation(args.yes, new_version, args.target_directory, yaml_files):
            self.log_info("用户取消操作")
            sys.exit(0)
        
        # 获取 git 日志
        git_log = self.get_git_log(args.target_directory)
        self.log_info("获取到 Git 提交历史")
        
        # 生成 changelog
        if self.generate_changelog(new_version, git_log, args.target_directory):
            # 更新 YAML 文件
            self.update_yaml_files(new_version, yaml_files)
            
            # 创建 git 提交
            if self.create_git_commit(new_version, yaml_files, args.target_directory):
                self.log_info(f"版本更新流程完成 - 目录: {args.target_directory}, 版本: {new_version}")
                
                # 提供可视化选项
                if not args.yes:
                    self.check_and_launch_gitk(args.target_directory, yaml_files)
            else:
                self.log_error("Git 提交失败")
                sys.exit(1)
        else:
            self.log_error("Changelog 生成失败")
            sys.exit(1)


if __name__ == "__main__":
    updater = DebianVersionUpdater()
    updater.main()