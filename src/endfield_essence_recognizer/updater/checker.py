"""版本检查模块"""

from __future__ import annotations

import re

import certifi
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

# 版本源 JSON 可能由不同发布脚本生成，这里统一兼容常见字段名。
_INCREMENTAL_PACKAGE_KEYS = (
    "incrementalPackages",
    "incremental_packages",
    "deltaPackages",
    "patches",
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


def _get_first(data: dict, *keys: str) -> object | None:
    """按兼容字段名顺序返回第一个非空值。"""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _find_incremental_package(data: dict, latest_version: str) -> dict | None:
    """从版本源中查找可从当前版本升级到最新版本的增量包。"""
    packages: object | None = None
    for key in _INCREMENTAL_PACKAGE_KEYS:
        packages = data.get(key)
        if packages:
            break
    if not isinstance(packages, list):
        return None

    for package in packages:
        if not isinstance(package, dict):
            continue
        from_version = _get_first(package, "fromVersion", "from_version", "from")
        to_version = _get_first(package, "toVersion", "to_version", "to")
        # 增量包只能精确匹配当前版本，避免把错误基线的补丁应用到本地。
        if from_version != __version__:
            continue
        if to_version not in (None, latest_version):
            continue
        download_url = _get_first(package, "downloadUrl", "download_url", "url")
        if not isinstance(download_url, str) or not download_url:
            continue
        return package
    return None


async def _resolve_sha256(
    client: httpx.AsyncClient,
    url: str,
    explicit_sha256: object | None = None,
) -> str | None:
    """优先使用版本源显式提供的 sha256，再回退到 GitHub asset digest。"""
    if isinstance(explicit_sha256, str) and explicit_sha256:
        return explicit_sha256.removeprefix("sha256:")

    match = _GITHUB_RELEASE_RE.match(url)
    if not match:
        return None

    owner, repo, tag, filename = match.groups()
    return await _fetch_github_release_sha256(client, owner, repo, tag, filename)


async def check_for_updates(
    proxy: str | None = None,
) -> dict | NoUpdateAvailable | UpdateCheckError:
    """检查是否有新版本。

    三种返回值互斥，调用方必须按类型分派：
    - dict → 有新版本
    - NoUpdateAvailable → 已是最新
    - UpdateCheckError → 检查失败（不应被伪装成“没有更新”）

    返回的 dict 会优先指向可用增量包，并保留 full_download_url 作为全量包回退。
    dict 中可能包含 ``sha256`` 字段（显式配置或从 GitHub Releases API 获取），
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
            timeout=10.0, verify=certifi.where(), proxy=proxy or None
        ) as client:
            response = await client.get(UPDATE_CHECK_URL)
            response.raise_for_status()
            data = response.json()

            latest_version = data["latestVersion"]

            if version.parse(latest_version) > version.parse(__version__):
                logger.info(f"发现新版本 {latest_version}")
                full_download_url = data["downloadUrl"]
                full_sha256 = await _resolve_sha256(
                    client,
                    full_download_url,
                    _get_first(data, "sha256", "digest"),
                )

                update_info = {
                    "version": latest_version,
                    "download_url": full_download_url,
                    "mirrors": data.get("mirrors", {}),
                    "sha256": full_sha256,
                    "package_type": "full",
                    "full_download_url": full_download_url,
                    "full_mirrors": data.get("mirrors", {}),
                    "full_sha256": full_sha256,
                    "full_size": data.get("size"),
                }

                incremental_package = _find_incremental_package(data, latest_version)
                if incremental_package:
                    incremental_url = _get_first(
                        incremental_package,
                        "downloadUrl",
                        "download_url",
                        "url",
                    )
                    incremental_sha256 = await _resolve_sha256(
                        client,
                        str(incremental_url),
                        _get_first(incremental_package, "sha256", "digest"),
                    )
                    update_info.update(
                        {
                            "download_url": incremental_url,
                            "mirrors": incremental_package.get("mirrors", {}),
                            "sha256": incremental_sha256,
                            "package_type": "incremental",
                            "from_version": __version__,
                            "size": incremental_package.get("size"),
                        }
                    )
                    logger.info(f"将优先使用增量包: {__version__} -> {latest_version}")

                return update_info

            logger.info("当前已是最新版本")
            return NoUpdateAvailable()

    except Exception as e:
        logger.warning(f"检查更新失败: {e}")
        return UpdateCheckError(str(e))
