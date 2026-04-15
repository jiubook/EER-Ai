"""版本检查模块"""

import httpx
from packaging import version

from endfield_essence_recognizer.utils.log import logger
from endfield_essence_recognizer.version import __version__

# 一图流版本检查 API
UPDATE_CHECK_URL = (
    "https://cos.yituliu.cn/endfield/endfield-essence-recognizer/version.json"
)


async def check_for_updates() -> dict | None:
    """检查是否有新版本

    Returns:
        dict: 包含版本信息的字典，如果有更新则返回 {
            "version": "x.x.x",
            "download_url": "...",
            "mirrors": {"global": {"download_url": "..."}, "cn": {"download_url": "..."}}
        }
        None: 无更新或检查失败
    """
    if not __version__:
        logger.warning("无法获取当前版本号")
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(UPDATE_CHECK_URL)
            response.raise_for_status()
            data = response.json()

            latest_version = data["latestVersion"]

            if version.parse(latest_version) > version.parse(__version__):
                logger.info(f"发现新版本: {latest_version}")
                return {
                    "version": latest_version,
                    "download_url": data["downloadUrl"],
                    "mirrors": data.get("mirrors", {}),
                }

            logger.info("当前已是最新版本")
            return None

    except Exception as e:
        logger.warning(f"检查更新失败: {e}")
        return None
