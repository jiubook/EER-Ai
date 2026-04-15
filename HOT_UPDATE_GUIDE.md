# 热更新功能说明

## 功能概述

应用内一键更新到最新版本，支持多镜像源、代理配置、实时进度显示。

## 实现原理

1. **版本检查** - 启动时自动检查一图流 API
2. **下载更新** - 后台下载更新包，WebSocket 实时推送进度
3. **自动安装** - 批处理脚本替换文件并重启程序

## 核心功能

### 一键更新
- 点击"一键更新"按钮直接完成下载和安装
- 实时显示下载进度、速度、文件大小
- 支持取消下载（使用任务取消机制立即中断网络请求）
- 失败时显示错误信息和重试按钮，无需重新检查更新

### 多镜像源
- 一图流 API 返回的镜像（global、cn）
- GitHub 官方
- ghproxy 镜像（多个节点）
- gitmirror、gh.con.sh、githubproxy.cc 等镜像
- fastgit 镜像
- 下载过程中可动态切换

### 代理支持
- 可配置代理端口（默认 7890）
- 下载过程中可启用/禁用
- 格式：`http://127.0.0.1:{port}`

## 新增文件

### 后端
- `src/endfield_essence_recognizer/updater/` - 更新模块
  - `__init__.py` - 模块入口
  - `checker.py` - 版本检查
  - `downloader.py` - 下载管理
  - `installer.py` - 安装逻辑
  - `manager.py` - 更新管理器
  - `mirrors.py` - 镜像源配置
- `src/endfield_essence_recognizer/api/routes/update.py` - 更新 API
- `src/endfield_essence_recognizer/api/websockets/update_progress.py` - 进度推送

### 前端
- 修改 `frontend/src/composables/useUpdateChecker.ts` - 一键更新逻辑
- 修改 `frontend/src/components/UpdateDialogs.vue` - 进度对话框
- 修改 `frontend/src/pages/settings.vue` - 更新设置

### 配置
- `pyproject.toml` - 添加 `packaging`、`aiofiles` 依赖
- `src/endfield_essence_recognizer/schemas/user_setting.py` - 新增 `update_mirror` 和 `update_proxy` 字段
- `src/endfield_essence_recognizer/api/router.py` - 注册更新路由

## API 接口

### GET /api/update/check
检查是否有新版本（数据来源：一图流 API）

```json
{
  "has_update": true,
  "update_info": {
    "version": "0.9.0",
    "download_url": "https://github.com/.../release.zip",
    "mirrors": {
      "global": {"downloadUrl": "https://github.com/..."},
      "cn": {"downloadUrl": "https://cos.yituliu.cn/..."}
    }
  }
}
```

### POST /api/update/install
下载并安装更新

```json
{
  "success": true
}
```

### POST /api/update/cancel
取消当前下载

### GET /api/update/mirrors
获取可用镜像源列表

```json
{
  "mirrors": [
    {"title": "GitHub 官方", "value": "github"},
    {"title": "ghproxy 镜像", "value": "ghproxy"}
  ]
}
```

### WebSocket /ws/update/progress
实时推送下载进度

```json
{
  "progress": 45.5,
  "downloaded": 5242880,
  "total": 11534336,
  "speed": 1048576
}
```

## 使用方式

1. **自动检查** - 程序启动时自动检查
2. **手动检查** - 点击顶部工具栏更新按钮
3. **一键更新** - 发现新版本后点击"一键更新"
4. **配置设置** - 在设置页面配置镜像源和代理

## 更新流程

1. 用户点击"一键更新"
2. 显示进度对话框，建立 WebSocket 连接
3. 后端下载更新包到 `_updates` 目录
4. 实时推送下载进度
5. 解压到临时目录 `_update_temp`
6. 创建批处理脚本 `_updater.bat`
7. 启动脚本并退出当前程序
8. 脚本等待进程完全退出和文件句柄释放
9. 删除旧版本程序文件
10. 复制新文件（失败时自动重试最多5次）
11. 自动启动新版本程序
12. 清理临时文件和更新包

## 安全特性

更新脚本会删除以下旧版本文件：
- `endfield-essence-recognizer.exe`
- `_internal/`
- `logs/`
- `resources/`
- `README.md`
- `界面白屏解决方法.md`
- `遇到报错解决方法.webp`

以下文件会被保留：
- `config.json` - 用户配置

如需修改删除列表，编辑 `src/endfield_essence_recognizer/updater/installer.py` 中的批处理脚本。

## 注意事项

1. 需要管理员权限
2. 更新过程中会短暂关闭程序
3. 确保网络连接正常
4. 更新包从 GitHub Releases 获取

## 配置说明

### 后端配置
修改 `src/endfield_essence_recognizer/updater/checker.py`：

```python
UPDATE_CHECK_URL = "https://cos.yituliu.cn/endfield/endfield-essence-recognizer/version.json"
```

### 用户配置
在设置页面或更新对话框中配置：
- 镜像源选择
- 代理端口（默认 7890）
- 是否启用代理

## 发布新版本

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `src/endfield_essence_recognizer/version.py` 中的 `__version__`
3. 构建并打包应用
4. 在 GitHub 创建 Release 并上传 zip 包
5. 用户端会自动检测到新版本
