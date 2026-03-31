"""更新进度 WebSocket"""

import asyncio

from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/update", tags=["update"])

# 全局进度状态
progress_state = {
    "downloaded": 0,
    "total": 0,
    "speed": 0,
    "progress": 0,
}


@router.websocket("/progress")
async def update_progress_ws(websocket: WebSocket):
    """更新进度 WebSocket"""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(progress_state)
            await asyncio.sleep(0.5)
    except Exception:
        pass


def update_progress(downloaded: int, total: int, speed: float):
    """更新进度状态"""
    progress_state["downloaded"] = downloaded
    progress_state["total"] = total
    progress_state["speed"] = speed
    progress_state["progress"] = (downloaded / total * 100) if total > 0 else 0
