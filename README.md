# 📌 桌面便利贴 - 计划计时系统

一款基于PyQt5开发的桌面便签应用，支持事项管理、看板视图、计时器、甘特图和桌面悬浮卡片功能。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 功能特性

| 功能 | 说明 |
|------|------|
| 📋 看板视图 | 拖拽式看板，分类管理事项 |
| 📝 事项列表 | 支持批量操作、筛选、排序 |
| ⏱️ 计时器 | 精确计时，记录实际耗时 |
| 📊 甘特图 | 可视化时间线展示 |
| 📌 桌面卡片 | 悬浮便签，实时查看进度 |
| 🗂 归档分析 | 统计完成率、准时率等数据 |
| 🐱 休息提醒 | 定时提醒休息，保护健康 |
| 💾 数据存储 | SQLite本地存储，绿色便携 |

## 界面预览

- **看板视图**：拖拽式管理事项
- **事项列表**：批量操作更高效
- **桌面卡片**：悬浮便签实时查看
- **甘特图**：时间线可视化

## 安装运行

### 环境要求
- Python 3.10+
- PyQt5

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

### 打包EXE
```bash
python build_exe.py
```

生成的EXE文件位于 `output/` 目录。

## 项目结构

```
desktop_sticky_notes/
├── main.py              # 入口文件
├── main_window.py       # 主窗口
├── database.py          # 数据库操作
├── models.py            # 数据模型
├── kanban_tab.py        # 看板视图
├── gantt_tab.py         # 甘特图
├── sticky_note.py       # 桌面悬浮卡片
├── notification.py      # 系统通知
├── rest_reminder.py     # 休息提醒
├── build_exe.py         # 打包脚本
├── logo.png             # 应用图标
└── requirements.txt     # 依赖列表
```

## 使用说明

1. **创建事项**：点击"新建"或使用快捷键
2. **开始计时**：点击事项的"开始"按钮
3. **Pin到桌面**：右键事项选择"Pin到桌面"
4. **查看统计**：切换到"归档分析"标签页

## 技术栈

- **前端**：PyQt5 (Qt Framework)
- **后端**：Python 3.10+
- **数据库**：SQLite
- **打包**：PyInstaller

## License

MIT License