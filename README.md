# DDE File Manager Extra Context Menu Plugins

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.4.4-blue.svg)](https://github.com/your-repo/dfm-xmenu-plugins)

为深度桌面环境（DDE）文件管理器提供额外上下文菜单插件的集合，增强开发者的工作效率。

## 项目简介

`dfm-xmenu-plugins` 是一个为 DDE 文件管理器设计的扩展插件包，通过右键菜单提供常用的开发工具快捷访问。该项目采用模块化设计，每个功能都是独立的 Debian 包，用户可以根据需要选择性安装。

## 功能特性

### 🛠️ 开发工具集成

- **DEB 包构建器** - 快速构建 Debian 软件包
- **Gitk** - Git 仓库历史可视化工具
- **Git Cola** - 图形化 Git 操作界面
- **Visual Studio Code** - 跨平台代码编辑器，智能检测工程目录
- **Qt Creator** - 跨平台 Qt 开发 IDE，智能检测 qmake/CMake 工程
- **Deepin 项目下载器** - 从各种来源下载和管理深度项目
- **DDE DConfig 编辑器** - 系统和应用程序配置管理
- **D-Feet** - D-Bus 调试和检查工具
- **更新日志管理** - 自动更新 Debian 更新日志和版本信息

### 📦 模块化设计

每个功能都是独立的 Debian 包，支持：
- 灵活的依赖管理
- 独立的功能更新
- 按需安装和卸载
- 清晰的职责分离

## 安装方式

### 安装所有插件

```bash
sudo apt install dfm-xmenu-plugins
```

### 单独安装插件

```bash
# DEB 包构建器
sudo apt install dfm-xmenu-deb-builder

# Git 工具
sudo apt install dfm-xmenu-gitk dfm-xmenu-git-cola

# 代码编辑器和 IDE
sudo apt install dfm-xmenu-vscode dfm-xmenu-qtcreator

# 项目管理工具
sudo apt install dfm-xmenu-deepin-project-downloader

# 系统工具
sudo apt install dfm-xmenu-dde-dconfig-editor dfm-xmenu-d-feet

# 更新日志工具
sudo apt install dfm-xmenu-changelog-update

# 集成菜单（包含所有工具）
sudo apt install dfm-xmenu-integration-all
```

## 使用方法

安装完成后，在 DDE 文件管理器中右键点击空白区域或文件夹，即可看到新增的上下文菜单选项。

### 支持的菜单类型

- `EmptyArea` - 空白区域右键菜单
- `SingleDir` - 单个目录右键菜单
- `MultiFileDirs` - 多文件/目录右键菜单

## 项目结构

```
dfm-xmenu-plugins/
├── LICENSE                    # MIT 许可证
├── README.md                  # 项目说明文档
├── build-deb/                 # DEB 包构建工具
│   ├── quick-build-deb.sh     # 快速构建脚本
│   ├── deb-builder.desktop    # DEB 构建器菜单项
│   └── deb-package-icon.svg   # 图标文件
├── cat-gitk/                  # Gitk 集成
│   ├── gitk.desktop           # Gitk 菜单项
│   ├── gitk-launcher.sh       # Gitk 启动脚本
│   └── gitk-icon.svg          # 图标文件
├── git-cola/                  # Git Cola 集成
│   └── git-cola.desktop       # Git Cola 菜单项
├── vscode/                    # Visual Studio Code 集成
│   ├── vscode.desktop         # VSCode 菜单项
│   ├── vscode-launcher.sh     # VSCode 启动脚本
│   └── vscode-icon.svg        # 图标文件
├── qtcreator/                # Qt Creator 集成
│   ├── qtcreator.desktop      # Qt Creator 菜单项
│   ├── qtcreator-launcher.sh  # Qt Creator 启动脚本
│   └── qtcreator-icon.svg     # 图标文件
├── dde-dconfig-editor/        # DConfig 编辑器
│   ├── dde-dconfig-editor.desktop
│   └── dde-dconfig-editor.svg
├── d-feet/                    # D-Feet D-Bus 调试器
│   ├── d-feet.desktop
│   └── d-feet.svg
├── deepin-project-downloader/ # 项目下载器
│   ├── deepin-project-downloader.desktop
│   ├── deepin-project-downloader-backen.py
│   ├── dde-project-downloader.sh
│   └── deepin-project-downloader.svg
├── integration-all/           # 集成菜单
│   ├── integration-all.desktop
│   └── integration.svg
├── debian-changelog/          # 更新日志工具
│   ├── changelog-update.desktop
│   ├── changelog-update-launcher.sh
│   ├── debian_version_gui.py
│   ├── debian_version_update.py
│   └── update-changelog.svg
└── debian/                    # Debian 打包配置
    ├── changelog
    ├── control
    ├── rules
    └── *.install 文件
```

## 开发构建

### 构建环境要求

- Debian/Ubuntu 系统
- debhelper (>= 13)
- dpkg-dev
- build-essential

### 构建步骤

1. 克隆项目
```bash
git clone https://github.com/your-repo/dfm-xmenu-plugins.git
cd dfm-xmenu-plugins
```

2. 使用快速构建脚本
```bash
./build-deb/quick-build-deb.sh
```

3. 或使用标准 Debian 构建流程
```bash
dpkg-buildpackage -us -uc -b
```

### 构建选项

快速构建脚本支持多种选项：
```bash
# 使用所有 CPU 核心（默认）
./build-deb/quick-build-deb.sh

# 使用一半 CPU 核心
./build-deb/quick-build-deb.sh . yes half

# 指定并行任务数
./build-deb/quick-build-deb.sh . yes 8

# 构建后不清理缓存
./build-deb/quick-build-deb.sh . no
```

## 版本历史

- **v1.4.4** (2025-11-12) - 添加 Visual Studio Code 和 Qt Creator 插件，统一通知系统
- **v1.4.1** (2025-11-07) - 添加媒体调试器仓库链接
- **v1.4** (2025-11-04) - 重命名包名为 dfm-xmenu-* 模式
- **v1.3** (2025-10-31) - 添加 D-Feet D-Bus 调试器，改进包配置
- **v1.2** (2025-10-30) - 添加 D-Feet 集成
- **v1.1** (2025-10-27) - 添加 Deepin 项目下载器
- **v1.0** (2025-10-27) - 初始版本发布

## 依赖关系

### 核心依赖
- `dde-file-manager` - DDE 文件管理器
- `debhelper-compat (= 13)` - Debian 构建助手

### 功能依赖
- `git`, `gitk` - Git 版本控制
- `git-cola` - Git 图形界面
- `code` - Visual Studio Code 编辑器
- `qtcreator` - Qt Creator IDE
- `zenity | kdialog` - 图形对话框支持
- `dpkg-dev`, `debhelper` - DEB 包构建
- `python3`, `python3-tk` - Python 运行环境
- `dde-dconfig-editor` - DDE 配置编辑器
- `devscripts` - 开发脚本工具
- `d-feet` - D-Bus 调试工具

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 作者

- **zhanghongyuan** - *初始开发* - [zhanghongyuan@uniontech.com](mailto:zhanghongyuan@uniontech.com)

## 致谢

- 深度桌面环境（DDE）团队
- Debian 打包社区
- 所有贡献者和用户

## 链接

- [项目主页](https://github.com/your-repo/dfm-xmenu-plugins)
- [问题反馈](https://github.com/your-repo/dfm-xmenu-plugins/issues)
- [深度桌面环境](https://www.deepin.org/)