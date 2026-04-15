"""更新相关 API 路由"""

import re

from fastapi import APIRouter, Depends

from endfield_essence_recognizer.api.websockets.update_progress import update_progress
from endfield_essence_recognizer.dependencies.settings import (
    get_user_setting_manager_dep,
)
from endfield_essence_recognizer.services.user_setting_manager import (
    UserSettingManager,
)
from endfield_essence_recognizer.updater.manager import UpdateManager
from endfield_essence_recognizer.updater.mirrors import MIRROR_NAMES
from endfield_essence_recognizer.utils.log import logger

router = APIRouter(prefix="/update", tags=["update"])

update_manager = UpdateManager()


@router.get("/mirrors")
async def get_mirrors():
    """获取可用的镜像源列表"""
    return {
        "mirrors": [{"title": name, "value": key} for key, name in MIRROR_NAMES.items()]
    }


@router.get("/check")
async def check_update():
    """检查更新"""
    try:
        update_info = await update_manager.check_and_prompt()
        if update_info:
            return {"has_update": True, "update_info": update_info}
        return {"has_update": False}
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        return {"has_update": False, "error": str(e)}


@router.post("/install")
async def install_update_route(
    setting_manager: UserSettingManager = Depends(get_user_setting_manager_dep),
):
    """下载并安装更新"""
    try:
        settings = setting_manager.get_user_setting()
        proxy = settings.update_proxy if settings.update_proxy else None
        mirror = settings.update_mirror

        # 转换下载 URL
        download_url = None
        if mirror and mirror != "github" and update_manager.update_info:
            mirrors = update_manager.update_info.get("mirrors", {})
            # 优先使用一图流 API 返回的镜像
            if mirror in mirrors and "downloadUrl" in mirrors[mirror]:
                download_url = mirrors[mirror]["downloadUrl"]
                logger.info(f"使用 API 镜像源: {mirror}")
            elif "cn" in mirrors and "downloadUrl" in mirrors["cn"]:
                # 国内用户默认走 CN 镜像
                download_url = mirrors["cn"]["downloadUrl"]
                logger.info("使用 CN 镜像源")
            else:
                # 回退到 mirrors.py 中的模板镜像
                from endfield_essence_recognizer.updater.mirrors import get_mirror_url

                original_url = update_manager.update_info["download_url"]
                match = re.match(
                    r"https://github\.com/([^/]+)/([^/]+)/releases/download/([^/]+)/(.+)",
                    original_url,
                )
                if match:
                    owner, repo, tag, filename = match.groups()
                    download_url = get_mirror_url(
                        mirror, f"{owner}/{repo}", tag, filename
                    )
                    logger.info(f"使用模板镜像源: {mirror}")

        success = await update_manager.download_and_install(
            progress_callback=update_progress,
            proxy=proxy,
            download_url=download_url,
        )
        return {"success": success}
    except Exception as e:
        logger.error(f"安装更新失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/cancel")
async def cancel_update():
    """取消下载"""
    try:
        update_manager.cancel_download()
        return {"success": True}
    except Exception as e:
        logger.error(f"取消更新失败: {e}")
        return {"success": False, "error": str(e)}
