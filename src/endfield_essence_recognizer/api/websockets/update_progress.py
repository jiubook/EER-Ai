"""更新进度 WebSocket"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from endfield_essence_recognizer.utils.log import logger

router = APIRouter(prefix="/update", tags=["update"])

# 全局进度状态
progress_state = {
    "downloaded": 0,
    "total": 0,
    "speed": 0,
    "progress": 0,
}
_lock = asyncio.Lock()


@router.websocket("/progress")
async def update_progress_ws(websocket: WebSocket):
    """更新进度 WebSocket"""
    await websocket.accept()
    try:
        while True:
            async with _lock:
                data = progress_state.copy()
            await websocket.send_json(data)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")


def update_progress(downloaded: int, total: int, speed: float):
    """更新进度状态"""

    async def _update():
        async with _lock:
            progress_state["downloaded"] = downloaded
            progress_state["total"] = total
            progress_state["speed"] = speed
            progress_state["progress"] = (downloaded / total * 100) if total > 0 else 0

    def _log_task_exception(task: asyncio.Task):
        try:
            task.result()
        except Exception as e:
            logger.error(f"更新进度任务失败: {e}")

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_update())
        task.add_done_callback(_log_task_exception)
    except RuntimeError:
        # 同步上下文中直接更新
        progress_state["downloaded"] = downloaded
        progress_state["total"] = total
        progress_state["speed"] = speed
        progress_state["progress"] = (downloaded / total * 100) if total > 0 else 0
