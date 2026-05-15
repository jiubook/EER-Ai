# 热更新功能说明

## 功能概述

应用内更新用于让用户在不手动重新下载完整压缩包的情况下升级到新版本。当前方案支持：

- 多镜像源下载与代理配置
- WebSocket 实时下载进度
- 更新包 SHA-256 校验（当发布资产提供 digest 时）
- 基于 manifest 的文件级更新
- 基于旧/新 dist 对比生成增量包，只下载变更文件
- 增量包基线不匹配或预安装校验失败时自动回退全量包
- 独立 Rust 更新器 `_internal/eer_updater.exe`
- 更新器随 manifest 复制并可被后续更新替换
- 失败时尽力回滚到旧版本文件

## 核心原则

热更新的第一目标不是“尽快覆盖文件”，而是“安全地把安装目录收敛到目标版本”。因此需要遵守以下原则：

1. **目标状态明确**：发布包中的 `_internal/manifest.json` 声明该版本应包含的文件和 protected 路径。
2. **用户数据不动**：`config.json`、`profiles.json`、`logs/`、`screenshots/`、`.env` 等路径不会被删除或覆盖；`_updates/` 和系统临时目录中的更新解压目录会在更新完成后尽量清理。
3. **路径不可越界**：Python 解压阶段和 Rust 执行阶段都会拒绝路径穿越。
4. **失败优先保旧版本可用**：删除或覆盖旧文件前先备份；复制失败、源文件缺失或路径非法时写入失败状态并尽力回滚。
5. **更新器放在内部目录**：`eer_updater.exe` 固定放在 `_internal/` 下，避免用户在安装根目录误启动。

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
- `scripts/generate_incremental_package.py`：对比旧/新 PyInstaller 产物并生成文件级增量 zip。
- `main.spec`：PyInstaller 打包脚本，会在本地存在 release updater 时复制 `_internal/eer_updater.exe` 到 dist 的 `_internal` 目录。

## Manifest 与 Plan

### `_internal/manifest.json`

manifest 是发布包的目标状态声明，由 CI 或本地发布流程生成：

```json
{
  "version": "0.9.0",
  "files": [
    "endfield-essence-recognizer.exe",
    "_internal/eer_updater.exe",
    "_internal/python3.dll",
    "_internal/manifest.json",
    "README.md"
  ],
  "protected": [
    "config.json",
    "profiles.json",
    "logs/",
    "screenshots/",
    ".env"
  ]
}
```

`_internal/eer_updater.exe` 必须在 `files` 中，但不能在 `protected` 中，否则后续无法替换更新器。

### 临时解压目录中的 `_plan.json`

安装开始前，Python 侧会把 manifest 转换为 updater 可执行的 plan：

```json
{
  "package_type": "manifest",
  "remove_list": ["_internal/old.dll"],
  "copy_list": ["endfield-essence-recognizer.exe", "_internal/eer_updater.exe"],
  "protected_list": ["config.json", ".env"]
}
```

协议要求：`_plan.json` 是 Python installer 与 Rust updater 之间的协议。新增字段应优先保持可选，避免破坏双方调用关系。

### `_internal/incremental_update.json`

增量包额外包含该文件，用于声明包内有哪些可复制文件、需要删除哪些旧文件，以及该包只能从哪个版本升级：

```json
{
  "format": 1,
  "package_type": "incremental",
  "from_version": "0.8.0",
  "to_version": "0.9.2",
  "target_manifest": "_internal/manifest.json",
  "files": [
    "endfield-essence-recognizer.exe",
    "_internal/manifest.json",
    "_internal/endfield_essence_recognizer/webui_dist/assets/index-BDeaBJ68.js"
  ],
  "remove": [
    "_internal/endfield_essence_recognizer/webui_dist/assets/index-D32FmWFi.js"
  ],
  "protected": ["config.json", "profiles.json", "logs/", "screenshots/", ".env"]
}
```

增量包仍然必须包含目标版本的 `_internal/manifest.json`，这样安装完成后本地 manifest 会收敛到新版本完整状态。

## 更新流程

1. 用户点击“一键更新”。
2. 后端检查版本并确定下载地址。
3. `download_update()` 下载 zip 到 `_updates/`，前端通过 WebSocket 显示进度。
4. 如果可获得 SHA-256，`UpdateManager` 校验下载包完整性。
5. `install_update()` 解压 zip 到系统临时目录中的独立更新目录，并校验 zip 条目不能路径穿越。
6. Python 读取 `_internal/manifest.json`；如果同时存在 `_internal/incremental_update.json`，先校验本地 manifest 版本必须等于 `from_version`。
7. 全量包根据目标 manifest 计算完整 `remove_list` / `copy_list`；增量包只复制 metadata 中声明的变更文件，并只删除 metadata 中声明的旧文件。
8. Python 写入临时解压目录中的 `_plan.json`。
9. Python 优先启动临时解压目录中的 `_internal/eer_updater.exe`；如果更新包没有 updater，才回退到安装目录中的 `_internal/eer_updater.exe`。
10. 当前主程序延迟退出，Rust updater 等待父进程退出。
11. Rust updater 拒绝安装在盘符根目录的场景，并校验 plan 中所有路径不能越界。
12. 需要删除或覆盖的旧文件先移动到安装目录同盘的 `_update_backup_{pid}/`，避免 Windows 跨盘 `rename` 失败。
13. Rust updater 按 `copy_list` 从临时解压目录复制新文件到安装目录。
14. 如果复制失败、源文件缺失或路径非法，Rust updater 删除本次新增文件并从 `_update_backup_{pid}/` 恢复旧文件。
15. 更新成功后写入 `logs/{旧版本}_{新版本}_updater_success.txt`，删除同版本失败状态文件、更新包，并重启主程序。
16. 如果 updater 正从临时解压目录运行，会在退出后延迟删除该目录；`_updates/` 在更新包删除后也会尝试删除空目录。
17. `_update_backup_{pid}/` 会在更新成功或失败回滚后删除；如果 Windows 暂时拒绝访问，会安排延迟重试，并在下次更新开始前再次清理遗留目录。
18. 每次更新使用 `update-{时间戳}-{进程ID}` 形式的唯一临时目录，并在开始前清理超过 24 小时的旧更新临时目录。

## 更新器位置与运行方式

`eer_updater.exe` 不是给用户直接打开的程序，因此打包产物中固定放在 `_internal/` 下：

- 发布包路径：`_internal/eer_updater.exe`。
- 解压后的运行路径：系统临时目录中的 `_internal/eer_updater.exe`。
- 安装目录回退路径：`_internal/eer_updater.exe`。
- 该文件必须写入 manifest 的 `files`，并且不能加入 `protected`。
- 如果下载到的测试包不包含 updater，installer 会保留当前安装目录里的 `_internal/eer_updater.exe`，避免移动正在运行的更新器。
- 临时解压目录使用唯一名称，避免上一次清理失败影响下一次更新。

## 安全特性

### 文件保护

默认 protected 路径定义在 `scripts/generate_manifest.py` 的 `PROTECTED_PATHS` 中：

- `config.json`：用户配置
- `profiles.json`：多账号配置
- `logs/`：运行日志
- `screenshots/`：用户截图
- `_updates/`：下载缓存；更新成功后会删除本次下载包，并尝试删除空目录
- 系统临时目录中的更新解压目录：使用唯一目录名，更新成功后会尽量删除；下次更新会清理超过 24 小时的旧目录
- `_update_backup_{pid}/`：安装目录同盘的临时回滚备份；更新结束后会尽量删除，失败时会延迟重试并在下次更新前清理
- `.env`：环境变量配置

修改 protected 列表时，请同步更新单元测试。

### 路径穿越防护

- Python 解压 zip 前使用 `Path.resolve()` 与 `relative_to()` 拒绝 `../`、绝对路径等可疑条目。
- Rust updater 执行 plan 时再次拒绝绝对路径、盘符路径、根路径、`..` 和空路径。

### 回滚策略

- 删除和覆盖前先移动到 `_update_backup_{pid}/`。
- 若 copy 阶段失败，先删除本次新增文件，再把 `_update_backup_{pid}/` 中的旧文件恢复到原位置。
- `_update_backup_{pid}/` 删除前会清理只读属性；若被杀毒软件或系统短暂占用导致删除失败，会安排后台延迟重试。
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

## 版本源 JSON

`checker.py` 兼容原有全量字段，并会优先选择与当前版本精确匹配的增量包：

```json
{
  "latestVersion": "0.9.2",
  "downloadUrl": "https://github.com/owner/repo/releases/download/v0.9.2/endfield-essence-recognizer-v0.9.2-windows.zip",
  "sha256": "full-package-sha256",
  "size": 16777216,
  "mirrors": {
    "cn": {
      "downloadUrl": "https://cdn.example.com/endfield-essence-recognizer-v0.9.2-windows.zip"
    }
  },
  "incrementalPackages": [
    {
      "fromVersion": "0.8.0",
      "toVersion": "0.9.2",
      "downloadUrl": "https://cdn.example.com/endfield-essence-recognizer-0.8.0-to-0.9.2-windows-delta.zip",
      "sha256": "delta-package-sha256",
      "size": 1441792,
      "mirrors": {
        "cn": {
          "downloadUrl": "https://cdn.example.com/endfield-essence-recognizer-0.8.0-to-0.9.2-windows-delta.zip"
        }
      }
    }
  ]
}
```

兼容别名：增量列表也可使用 `incremental_packages`、`deltaPackages` 或 `patches`；包内字段也兼容 `from_version` / `to_version` / `download_url` / `url`。

## 本地开发与验证

```bash
# Python 侧 manifest / installer 测试
uv run pytest tests/unit/updater/test_manifest.py

# Python 侧 lint
uv run ruff check scripts/generate_manifest.py scripts/generate_incremental_package.py src/endfield_essence_recognizer/updater/installer.py tests/unit/updater/test_manifest.py

# Rust updater
cargo fmt --manifest-path updater/Cargo.toml --check
cargo clippy --manifest-path updater/Cargo.toml -- -D warnings
cargo test --manifest-path updater/Cargo.toml
```

## 发布新版本

1. 更新 `pyproject.toml` 中的版本号。
2. 构建前端产物。
3. 构建 release updater：`cargo build --release --manifest-path updater/Cargo.toml`。
4. 使用 PyInstaller 构建应用，`main.spec` 会复制 release updater 到 dist 的 `_internal` 目录。
5. 执行 `scripts/generate_manifest.py` 写入 `_internal/manifest.json`。
6. 打包全量 zip 并创建 GitHub Release。
7. 如需增量包，保留上一版本解压后的 dist 目录，并执行 `scripts/generate_incremental_package.py` 生成 delta zip。
8. 在版本源 JSON 中增加 `incrementalPackages`，用户端检查到匹配当前版本的增量包后会优先下载；不匹配则仍走全量包。

本地生成 manifest：

```bash
uv run python scripts/generate_manifest.py --dist-dir dist/endfield-essence-recognizer
```

本地生成 `0.8.0 -> 0.9.2` 增量包：

```bash
uv run python scripts/generate_incremental_package.py \
  --old-dist-dir dist/endfield-essence-recognizer-0.8.0 \
  --new-dist-dir dist/endfield-essence-recognizer \
  --from-version 0.8.0 \
  --to-version 0.9.2 \
  --output dist/endfield-essence-recognizer-0.8.0-to-0.9.2-windows-delta.zip
```

## 常见问题

### 更新器缺失

如果安装目录中没有 `_internal/eer_updater.exe`，应用内更新会失败。请确认发布包中包含该文件，并且构建流程已先执行 Rust release build。

### 更新失败后如何排查

- 查看 `logs/updater.log`。
- 查看 `logs/{旧版本}_{新版本}_updater_failure.txt`。
- 检查更新包是否缺少 manifest 声明的文件。
- 检查是否被杀毒软件、权限策略或磁盘空间问题阻止写入。

### 为什么临时解压目录有时不会立刻删除

当 updater 从临时解压目录运行时，Windows 会锁定正在运行的 exe。为避免删除正在运行的文件，updater 会启动延迟清理命令，在自身退出后删除该目录。安装目录下历史遗留的 `_update_temp/` 会在安装开始前尝试清理。

### 为什么 `_update_backup_{pid}` 有时不会立刻删除

`_update_backup_{pid}/` 是更新过程中的临时回滚备份，必须放在安装目录同盘，否则 Windows 无法使用 `rename` 快速移动旧文件。更新结束后 updater 会清理该目录；如果 Windows Defender、杀毒软件或系统文件句柄短暂占用旧 DLL/PYD，可能先返回“拒绝访问”。这种情况下 updater 会安排延迟清理，并且下次更新开始前会再次清理遗留的 `_update_backup_*` 目录。
