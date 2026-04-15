"""版本检查模块"""

from __future__ import annotations

import re

import httpx
from packaging import version

from endfield_essence_recognizer.utils.log import logger
from endfield_essence_recognizer.version import __version__

# 一图流版本检查 API
UPDATE_CHECK_URL = (
    "https://cos.yituliu.cn/endfield/endfield-essence-recognizer/version.json"
)

# 从 GitHub release 下载 URL 中提取 owner/repo/tag/filename
_GITHUB_RELEASE_RE = re.compile(
    r"https://github\.com/([^/]+)/([^/]+)/releases/download/([^/]+)/(.+)"
)


class UpdateCheckError(Exception):
    """更新检查失败（网络、解析、源站等错误）。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NoUpdateAvailable:
    """标记：当前已是最新版本。"""

    pass


async def _fetch_github_release_sha256(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    tag: str,
    filename: str,
) -> str | None:
    """从 GitHub Releases API 获取指定 asset 的 sha256 digest。

    GitHub 在 2023+ 为每个 release asset 提供 ``digest`` 字段（sha256）。
    如果 API 不可用或 asset 没有 digest，返回 None（不阻断更新流程）。

    Args:
        client: 已创建的 httpx 异步客户端。
        owner: 仓库所有者。
        repo: 仓库名。
        tag: release tag。
        filename: asset 文件名。

    Returns:
        hex 格式的 sha256 字符串，或 None。
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    try:
        resp = await client.get(
            api_url,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        release_data = resp.json()

        for asset in release_data.get("assets", []):
            if asset.get("name") == filename:
                digest = asset.get("digest", "")
                # GitHub 返回 "sha256:abcdef..." 格式
                if digest.startswith("sha256:"):
                    sha256 = digest[len("sha256:") :]
                    logger.info(f"获取到 asset sha256: {sha256[:16]}...")
                    return sha256
                break

        logger.info(f"GitHub asset {filename} 没有 digest 字段")
        return None
    except Exception as exc:
        logger.warning(f"获取 GitHub release sha256 失败: {exc}")
        return None


async def check_for_updates(
    proxy: str | None = None,
) -> dict | NoUpdateAvailable | UpdateCheckError:
    """检查是否有新版本。

    三种返回值互斥，调用方必须按类型分派：
    - dict          → 有新版本
    - NoUpdateAvailable → 已是最新
    - UpdateCheckError  → 检查失败（不应被伪装成"没有更新"）

    返回的 dict 可能包含 ``sha256`` 字段（从 GitHub Releases API 获取），
    供下载后校验使用。

    Args:
        proxy: 代理地址（如 "http://127.0.0.1:7890"）。

    Returns:
        见上方说明。
    """
    if not __version__:
        return UpdateCheckError("无法获取当前版本号")

    try:
        async with httpx.AsyncClient(
            timeout=10.0, proxy=proxy or None
        ) as client:
            response = await client.get(UPDATE_CHECK_URL)
            response.raise_for_status()
            data = response.json()

            latest_version = data["latestVersion"]

            if version.parse(latest_version) > version.parse(__version__):
                logger.info(f"发现新版本: {latest_version}")

                update_info = {
                    "version": latest_version,
                    "download_url": data["downloadUrl"],
                    "mirrors": data.get("mirrors", {}),
                    "sha256": None,
                }

                # 尝试从 GitHub Releases API 获取 sha256
                match = _GITHUB_RELEASE_RE.match(data["downloadUrl"])
                if match:
                    owner, repo, tag, filename = match.groups()
                    sha256 = await _fetch_github_release_sha256(
                        client, owner, repo, tag, filename
                    )
                    if sha256:
                        update_info["sha256"] = sha256

                return update_info

            logger.info("当前已是最新版本")
            return NoUpdateAvailable()

    except Exception as e:
        logger.warning(f"检查更新失败: {e}")
        return UpdateCheckError(str(e))
