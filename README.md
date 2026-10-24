# 📌 桌面便利贴 - 计划计时系统

一款基于 PyQt5 开发的桌面便签应用：桌面便利贴 + 看板 + 甘特图 + 计时分析，管理你的研发进度。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/Version-1.7-orange)

## 功能特性

| 功能 | 说明 |
|------|------|
| 📅 今日仪表盘 | 一屏聚合：今日计划、计时中、已逾期、今日投入、即将到期看板 |
| 📋 看板视图 | 多看板甬道，拖拽卡片，甬道底部行内快速添加，甬道角色映射状态 |
| 📝 事项列表 | 批量操作、筛选、排序、看板过滤、全局搜索 |
| ⏱️ 计时器 | 精确计时，记录实际耗时，支持手动修正 |
| 📊 甘特图 | 计划/实际双条时间线，今天指示线，拖拽改期 |
| 📌 桌面卡片 | 悬浮便利贴，**标题备注直接编辑**，实时计时 |
| ⚡ 快速捕捉 | 系统级热键 `Ctrl+Alt+N` 随时呼出快速新建 |
| 🗓 智能排期 | 按工作日历（9:00-18:00，午休1小时）自动避开已有计划排期 |
| 🗂 归档分析 | 完成率、准时率统计 + 近 8 周投入与按看板投入图表 |
| 💾 数据安全 | SQLite 本地存储，启动自动备份（保留 7 份），一键导出 JSON |
| 🐱 休息提醒 | 定时提醒休息，保护健康 |

## 安装运行

### 方式一：下载 EXE（推荐）

前往 [Releases 页面](https://github.com/kirk2023/desktop-sticky-notes/releases) 下载最新版 `desktop_sticky_notes.exe`，双击运行即可（首次启动会自动创建数据库）。

### 方式二：源码运行

#### 环境要求
- Python 3.10+
- PyQt5

#### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

### 打包 EXE
```bash
python build_exe.py
```

生成的 EXE 文件位于 `output/` 目录。

## 项目结构

```
desktop_sticky_notes/
├── main.py              # 入口文件（含全局热键注册）
├── main_window.py       # 主窗口（今日仪表盘接线、快速新建、设置）
├── database.py          # 数据库操作（SQLite，含迁移/备份/导出）
├── models.py            # 数据模型
├── today_tab.py         # 今日仪表盘
├── kanban_tab.py        # 看板视图
├── gantt_tab.py         # 甘特图
├── sticky_note.py       # 桌面悬浮便利贴
├── scheduler.py         # 智能排期引擎（工作日历/冲突检测）
├── charts.py            # 轻量条形图组件
├── design_system.py     # 设计系统（配色/字体/样式）
├── notification.py      # 系统通知
├── rest_reminder.py     # 休息提醒
├── build_exe.py         # 打包脚本
├── logo.png             # 应用图标
└── requirements.txt     # 依赖列表
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Alt+N` | 全局快速新建（即使应用在后台） |
| `Ctrl+N` | 新建事项（完整对话框） |
| `Ctrl+F` | 聚焦搜索框 |
| `Delete` | 删除选中事项 |

## 使用说明

1. **今日一屏**：打开软件先看「今日」页——逾期红色预警、今日计划、计时中一目了然
2. **随手记**：任何时刻按 `Ctrl+Alt+N`，输入标题回车即建成事项，默认**自动排期**到第一个空闲的工作时段
3. **智能排期**：往看板甬道里连续添加任务，会按工作日历（周一至五 9:00-18:00、午休 1 小时）自动错开时间；编辑对话框里点「⚡ 自动排期」可随时重算
4. **便利贴直接写**：Pin 到桌面的卡片上点击标题/备注即可编辑，停顿片刻自动保存
5. **看板管理**：右键甬道可设置角色（起始/进行中/完成）以精确联动事项状态；项目完结时右键看板「结项看板」批量清理未完成事项并归档
6. **甘特图改期**：拖动计划条按天调整日期；灰条为计划、琥珀条为实际投入；Ctrl+滚轮缩放时间轴
7. **数据安全**：默认启动自动备份；设置页可一键导出 JSON

## 技术栈

- **前端**：PyQt5 (Qt Framework)
- **后端**：Python 3.10+
- **数据库**：SQLite
- **打包**：PyInstaller

## 版本历史

详见 [RELEASE_NOTES.md](./RELEASE_NOTES.md)

## License

MIT License
