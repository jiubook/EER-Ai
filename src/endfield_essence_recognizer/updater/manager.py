"""更新管理器"""

import asyncio
from collections.abc import Callable
from pathlib import Path

from endfield_essence_recognizer.updater.checker import check_for_updates
from endfield_essence_recognizer.updater.downloader import download_update
from endfield_essence_recognizer.updater.installer import install_update
from endfield_essence_recognizer.utils.log import logger


class UpdateManager:
    """更新管理器"""

    def __init__(self, download_dir: Path | None = None):
        self.download_dir = download_dir or Path.cwd() / "_updates"
        self.update_info = None
        self.cancel_event = asyncio.Event()
        self.is_downloading = False
        self.download_lock = asyncio.Lock()

    async def check_and_prompt(self) -> dict | None:
        """检查更新并返回更新信息"""
        self.update_info = await check_for_updates()
        return self.update_info

    async def download_and_install(
        self,
        progress_callback: Callable[[int, int, float], None] | None = None,
        proxy: str | None = None,
    ) -> bool:
        """下载并安装更新"""
        async with self.download_lock:
            if not self.update_info:
                logger.warning("没有可用的更新信息")
                return False

            download_path = self.download_dir / f"update_{self.update_info['version']}.zip"

            self.is_downloading = True
            self.cancel_event.clear()

            # 下载更新
            success = await download_update(
                self.update_info["download_url"],
                download_path,
                progress_callback,
                self.cancel_event,
                proxy,
            )

            self.is_downloading = False

            if not success:
                return False

            # 安装更新
            return install_update(download_path)

    def cancel_download(self):
        """取消下载"""
        if self.is_downloading:
            self.cancel_event.set()
            logger.info("已发送取消下载信号")

