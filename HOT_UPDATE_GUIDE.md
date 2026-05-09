# 热更新功能说明

## 功能概述

应用内更新用于让用户在不手动重新下载完整压缩包的情况下升级到新版本。当前方案支持：

- 多镜像源下载与代理配置
- WebSocket 实时下载进度
- 更新包 SHA-256 校验（当发布资产提供 digest 时）
- 基于 manifest 的文件级更新
- 独立 Rust 更新器 `eer_updater.exe`
- `eer_updater.exe` 自更新
- 失败时尽力回滚到旧版本文件

## 核心原则

热更新的第一目标不是“尽快覆盖文件”，而是“安全地把安装目录收敛到目标版本”。因此需要遵守以下原则：

1. **目标状态明确**：发布包中的 `_internal/manifest.json` 声明该版本应包含的文件和 protected 路径。
2. **用户数据不动**：`config.json`、`profiles.json`、`logs/`、`screenshots/`、`_updates/`、`_update_temp/`、`.env` 等路径不会被删除或覆盖。
3. **路径不可越界**：Python 解压阶段和 Rust 执行阶段都会拒绝路径穿越。
4. **失败优先保旧版本可用**：删除或覆盖旧文件前先备份；复制失败、源文件缺失或路径非法时写入失败状态并尽力回滚。
5. **更新器可自更新**：优先运行更新包中的新版 `eer_updater.exe`，由新版更新器替换安装目录中的旧 updater。

## 模块结构

### 后端

- `src/endfield_essence_recognizer/updater/checker.py`：检查版本、解析下载地址、获取 GitHub asset digest。
- `src/endfield_essence_recognizer/updater/downloader.py`：下载更新包并回调进度。
- `src/endfield_essence_recognizer/updater/installer.py`：解压更新包、读取 manifest、生成 `_plan.json`、启动 updater。
- `src/endfield_essence_recognizer/updater/manager.py`：串联检查、下载、校验和安装流程。
- `src/endfield_essence_recognizer/updater/mirrors.py`：维护镜像源模板。
- `src/endfield_essence_recognizer/api/routes/update.py`：更新相关 HTTP API。
- `src/endfield_essence_recognizer/api/websockets/update_progress.py`：下载进度 WebSocket。

### 独立更新器

- `updater/`：Rust 编写的独立更新器工程。
- `updater/src/main.rs`：等待主程序退出、执行文件删除/复制/回滚、重启主程序。
- `updater/Cargo.toml` / `updater/Cargo.lock`：Rust 依赖和锁文件。

### 发布辅助

- `scripts/generate_manifest.py`：扫描 PyInstaller 产物并生成 `_internal/manifest.json`。
- `main.spec`：PyInstaller 打包脚本，会在本地存在 release updater 时复制 `eer_updater.exe` 到 dist 根目录。

## Manifest 与 Plan

### `_internal/manifest.json`

manifest 是发布包的目标状态声明，由 CI 或本地发布流程生成：

```json
{
  "version": "0.9.0",
  "files": [
    "endfield-essence-recognizer.exe",
    "eer_updater.exe",
    "_internal/python3.dll",
    "_internal/manifest.json",
    "README.md"
  ],
  "protected": [
    "config.json",
    "profiles.json",
    "logs/",
    "screenshots/",
    "_updates/",
    "_update_temp/",
    ".env"
  ]
}
```

`eer_updater.exe` 必须在 `files` 中，但不能在 `protected` 中，否则无法自更新。

### `_update_temp/_plan.json`

安装开始前，Python 侧会把 manifest 转换为 updater 可执行的 plan：

```json
{
  "package_type": "manifest",
  "remove_list": ["_internal/old.dll"],
  "copy_list": ["endfield-essence-recognizer.exe", "eer_updater.exe"],
  "protected_list": ["config.json", ".env"]
}
```

兼容要求：`_plan.json` 是 Python installer 与 Rust updater 之间的协议。新增字段必须向后兼容，不能破坏旧主程序调用新版 updater。

## 更新流程

1. 用户点击“一键更新”。
2. 后端检查版本并确定下载地址。
3. `download_update()` 下载 zip 到 `_updates/`，前端通过 WebSocket 显示进度。
4. 如果可获得 SHA-256，`UpdateManager` 校验下载包完整性。
5. `install_update()` 解压 zip 到 `_update_temp/`，并校验 zip 条目不能路径穿越。
6. Python 读取 `_internal/manifest.json`，计算 `remove_list`、`copy_list`、`protected_list`。
7. Python 写入 `_update_temp/_plan.json`。
8. Python 优先启动 `_update_temp/eer_updater.exe`；如果更新包没有 updater，才回退到安装目录中的 `eer_updater.exe`。
9. 当前主程序延迟退出，Rust updater 等待父进程退出。
10. Rust updater 拒绝安装在盘符根目录的场景，并校验 plan 中所有路径不能越界。
11. 需要删除或覆盖的旧文件先移动到 `_update_temp/_backup/`。
12. Rust updater 按 `copy_list` 从 `_update_temp/` 复制新文件到安装目录。
13. 如果复制失败、源文件缺失或路径非法，Rust updater 删除本次新增文件并从 `_backup/` 恢复旧文件。
14. 更新成功后写入 `_update_success.txt`，删除失败状态文件、更新包，并重启主程序。
15. 如果 updater 正从 `_update_temp/` 运行，为避免 Windows 删除正在运行的 exe，临时目录会延后到下次更新前清理。

## 自更新说明

Windows 不允许删除或替换正在运行的 exe，因此不能让安装目录中的旧 `eer_updater.exe` 直接替换自己。当前方案是：

- 更新包内携带新版 `eer_updater.exe`。
- Python installer 优先启动 `_update_temp/eer_updater.exe`。
- 新版 updater 作为独立进程运行，安装目录中的旧 updater 没有被占用。
- 新版 updater 复制 `eer_updater.exe` 到安装目录，完成自更新。

这意味着新版 updater 必须能理解旧主程序生成的 `_plan.json`。如需升级 plan 协议，请只添加可选字段，并保持旧字段语义不变。

## 安全特性

### 文件保护

默认 protected 路径定义在 `scripts/generate_manifest.py` 的 `PROTECTED_PATHS` 中：

- `config.json`：用户配置
- `profiles.json`：多账号配置
- `logs/`：运行日志
- `screenshots/`：用户截图
- `_updates/`：下载缓存
- `_update_temp/`：临时解压目录
- `.env`：环境变量配置

修改 protected 列表时，请同步更新单元测试。

### 路径穿越防护

- Python 解压 zip 前使用 `Path.resolve()` 与 `relative_to()` 拒绝 `../`、绝对路径等可疑条目。
- Rust updater 执行 plan 时再次拒绝绝对路径、盘符路径、根路径、`..` 和空路径。

### 回滚策略

- 删除和覆盖前先移动到 `_backup/`。
- 若 copy 阶段失败，先删除本次新增文件，再把 `_backup/` 中的旧文件恢复到原位置。
- 回滚是“尽力而为”：权限错误、磁盘错误或杀进程仍可能导致手动修复需求。

## API 接口

### `GET /api/update/check`

检查是否有新版本。

### `POST /api/update/install`

下载并安装更新。

```json
{
  "success": true
}
```

### `POST /api/update/cancel`

取消当前下载任务。

### `GET /api/update/mirrors`

获取可用镜像源列表。

### `WebSocket /ws/update/progress`

实时推送下载进度。

```json
{
  "progress": 45.5,
  "downloaded": 5242880,
  "total": 11534336,
  "speed": 1048576
}
```

## 本地开发与验证

```bash
# Python 侧 manifest / installer 测试
uv run pytest tests/unit/updater/test_manifest.py

# Python 侧 lint
uv run ruff check scripts/generate_manifest.py src/endfield_essence_recognizer/updater/installer.py tests/unit/updater/test_manifest.py

# Rust updater
cargo fmt --manifest-path updater/Cargo.toml --check
cargo clippy --manifest-path updater/Cargo.toml -- -D warnings
cargo test --manifest-path updater/Cargo.toml
```

## 发布新版本

1. 更新 `pyproject.toml` 中的版本号。
2. 构建前端产物。
3. 构建 release updater：`cargo build --release --manifest-path updater/Cargo.toml`。
4. 使用 PyInstaller 构建应用，`main.spec` 会复制 release updater 到 dist 根目录。
5. 执行 `scripts/generate_manifest.py` 写入 `_internal/manifest.json`。
6. 打包 zip 并创建 GitHub Release。
7. 用户端检查到新版本后即可应用内更新。

本地生成 manifest：

```bash
uv run python scripts/generate_manifest.py --dist-dir dist/endfield-essence-recognizer
```

## 常见问题

### 更新器缺失

如果安装目录中没有 `eer_updater.exe`，应用内更新会失败。请确认发布包中包含该文件，并且构建流程已先执行 Rust release build。

### 更新失败后如何排查

- 查看 `logs/updater.log`。
- 查看安装目录中的 `_update_failure.txt`。
- 检查更新包是否缺少 manifest 声明的文件。
- 检查是否被杀毒软件、权限策略或磁盘空间问题阻止写入。

### 为什么 `_update_temp/` 有时不会立刻删除

当新版 updater 从 `_update_temp/` 运行时，Windows 会锁定正在运行的 exe。为支持 updater 自更新，临时目录会延后清理，下一次更新开始前 Python installer 会先删除旧的 `_update_temp/`。
