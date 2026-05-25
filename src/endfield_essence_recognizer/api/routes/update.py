"""更新相关 API 路由"""

import re

from fastapi import APIRouter, Depends

from endfield_essence_recognizer.api.websockets.update_progress import (
    reset_progress,
    update_progress,
)
from endfield_essence_recognizer.dependencies.settings import (
    get_user_setting_manager_dep,
)
from endfield_essence_recognizer.services.user_setting_manager import (
    UserSettingManager,
)
from endfield_essence_recognizer.updater.checker import (
    NoUpdateAvailable,
)
from endfield_essence_recognizer.updater.manager import UpdateManager
from endfield_essence_recognizer.updater.mirrors import (
    GITHUB_MIRROR_NAMES,
    get_mirror_url,
)
from endfield_essence_recognizer.updater.sources import (
    GITHUB_FLOW,
    UPDATE_FLOW_NAMES,
    get_enabled_update_flows,
)
from endfield_essence_recognizer.utils.log import logger

router = APIRouter(prefix="/update", tags=["update"])

update_manager = UpdateManager()


@router.get("/mirrors")
async def get_mirrors():
    """获取可用的 GitHub 下载镜像列表。"""
    return {
        "mirrors": [
            {"title": name, "value": key} for key, name in GITHUB_MIRROR_NAMES.items()
        ]
    }


@router.get("/flows")
async def get_update_flows():
    """获取后端启用的更新流程列表。"""
    return {
        "flows": [
            {"title": UPDATE_FLOW_NAMES[flow], "value": flow}
            for flow in get_enabled_update_flows()
        ]
    }


@router.get("/check")
async def check_update(
    setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
):
    """检查更新。

    前端可通过 has_update + error 两个字段区分三种状态：
    - has_update=true              → 有新版本
    - has_update=false, error=null → 已是最新
    - has_update=false, error=xxx  → 检查失败
    """
    try:
        settings = setting_manager.get_user_setting()
        proxy = settings.update_proxy if settings.update_proxy else None

        result = await update_manager.check_and_prompt(
            proxy=proxy,
            update_flow=getattr(settings, "update_flow", None),
            mirror_chyan_res_id=getattr(settings, "update_mirrorchyan_res_id", ""),
            mirror_chyan_cdk=getattr(settings, "update_mirrorchyan_cdk", ""),
            mirror_chyan_user_agent=getattr(
                settings,
                "update_mirrorchyan_user_agent",
                "",
            ),
        )

        if isinstance(result, dict):
            return {"has_update": True, "update_info": result}
        elif isinstance(result, NoUpdateAvailable):
            return {"has_update": False, "error": None}
        else:
            # UpdateCheckError
            return {"has_update": False, "error": result.message}
    except Exception as e:
        logger.error(f"检查更新异常: {e}")
        return {"has_update": False, "error": str(e)}


@router.post("/install")
async def install_update_route(
    body: dict | None = None,
    setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
):
    """下载并安装更新。

    请求体可选字段：
    - skip_verify: bool — 跳过 SHA-256 校验（用户在前端确认风险后主动选择）

    返回值包含 success + error（如有），其中 error="sha256_mismatch" 时
    附带 sha256_expected / sha256_actual 供前端展示。
    """
    try:
        skip_verify = bool((body or {}).get("skip_verify", False))

        settings = setting_manager.get_user_setting()
        proxy = settings.update_proxy if settings.update_proxy else None
        github_mirror = getattr(settings, "update_github_mirror", "github")

        # 仅 GitHub 流程允许在 GitHub 官方与代理镜像之间切换；其他流程不跨源改写 URL。
        download_url = None
        if (
            github_mirror
            and github_mirror != "github"
            and update_manager.update_info
            and update_manager.update_info.get("source") == GITHUB_FLOW
        ):
            original_url = update_manager.update_info["download_url"]
            match = re.match(
                r"https://github\.com/([^/]+)/([^/]+)/releases/download/([^/]+)/(.+)",
                original_url,
            )
            if match:
                owner, repo, tag, filename = match.groups()
                download_url = get_mirror_url(
                    github_mirror, f"{owner}/{repo}", tag, filename
                )
                logger.info(f"使用 GitHub 镜像源: {github_mirror}")

        # 重置进度状态，避免上一轮残留值
        reset_progress()

        result = await update_manager.download_and_install(
            progress_callback=update_progress,
            proxy=proxy,
            download_url=download_url,
            skip_verify=skip_verify,
        )
        return result
    except Exception as e:
        logger.error(f"安装更新失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/cancel")
async def cancel_update():
    """取消下载

    只有在确实有活跃下载任务时才返回 success: true，
    避免前端在不确定取消结果时误触发重试逻辑。
    """
    try:
        cancelled = update_manager.cancel_download()
        return {"success": cancelled}
    except Exception as e:
        logger.error(f"取消更新失败: {e}")
        return {"success": False, "error": str(e)}
