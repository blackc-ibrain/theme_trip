"""
任务进度跟踪(内存版,支持 SSE 推送)。

生产环境应该用 Redis,但 L9/L10 这个量级内存字典够用。
"""
import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskProgress:
    task_id: str
    status: str = "pending"          # pending / running / done / error
    stage: str = ""                  # 当前阶段中文描述
    progress: int = 0                # 0-100
    result: Any = None               # TripPlan (status=done 时)
    error: str | None = None
    created_at: float = field(default_factory=time.time)


_tasks: dict[str, TaskProgress] = {}
_lock = threading.Lock()
_async_lock = asyncio.Lock()

# 任务过期时间(秒),超过会被清理
TASK_TTL = 600


def create_task() -> TaskProgress:
    """创建新任务，返回 task_id"""
    task_id = uuid.uuid4().hex[:8]
    task = TaskProgress(task_id=task_id)
    with _lock:
        _cleanup_expired()
        _tasks[task_id] = task
    return task


def start_task(task_id: str) -> None:
    """标记任务开始运行"""
    with _lock:
        if task_id in _tasks:
            _tasks[task_id].status = "running"


def update_progress(task_id: str, stage: str, progress: int) -> None:
    """更新任务进度"""
    with _lock:
        if task_id in _tasks:
            t = _tasks[task_id]
            t.status = "running"
            t.stage = stage
            t.progress = progress


def complete_task(task_id: str, result: Any) -> None:
    """标记任务完成"""
    with _lock:
        if task_id in _tasks:
            t = _tasks[task_id]
            t.status = "done"
            t.stage = "完成"
            t.progress = 100
            t.result = result


def fail_task(task_id: str, error: str) -> None:
    """标记任务失败"""
    with _lock:
        if task_id in _tasks:
            t = _tasks[task_id]
            t.status = "error"
            t.error = error


def get_task(task_id: str) -> TaskProgress | None:
    """获取任务状态"""
    with _lock:
        return _tasks.get(task_id)


def get_status(task_id: str) -> dict:
    """返回 {stage, progress}"""
    t = get_task(task_id)
    if not t:
        return {"stage": "", "progress": 0}
    return {"stage": t.stage, "progress": t.progress, "status": t.status}


def generate_sse(task_id: str) -> str:
    """生成 SSE 格式的字符串"""
    t = get_task(task_id)
    if not t:
        data = {"stage": "任务不存在", "progress": 0, "status": "error"}
    else:
        data = {
            "stage": t.stage,
            "progress": t.progress,
            "status": t.status,
        }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _cleanup_expired() -> None:
    """清理超过 TTL 的已完成任务。"""
    now = time.time()
    expired = [
        tid for tid, t in _tasks.items()
        if now - t.created_at > TASK_TTL and t.status in ("done", "error")
    ]
    for tid in expired:
        _tasks.pop(tid, None)
