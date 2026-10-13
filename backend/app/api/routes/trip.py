import asyncio
import json
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.agents.planner import plan_trip_async
from app.models.schemas import TripRequest, TripPlan
from app.services.progress import create_task, get_status, generate_sse, complete_task, fail_task

router = APIRouter(prefix="/trip", tags=["trip"])


@router.post("/plan", response_model=dict)
async def plan_start(req: TripRequest, background_tasks: BackgroundTasks):
    """
    启动异步行程规划任务，立即返回 task_id。
    """
    task = create_task()
    # 后台运行真正的规划逻辑
    background_tasks.add_task(plan_trip_async, req, task.task_id)
    return {"task_id": task.task_id}


@router.get("/plan/{task_id}/status")
def plan_status(task_id: str):
    """返回当前任务进度"""
    return get_status(task_id)


@router.get("/plan/{task_id}/stream")
def plan_stream(task_id: str):
    """
    SSE 流式推送进度。
    前端 EventSource 连接到此处接收实时进度。
    """
    async def event_generator():
        import time
        for _ in range(300):  # 最多 5 分钟
            sse = generate_sse(task_id)
            if sse:
                yield sse
            # 检查是否完成或出错
            from app.services.progress import get_task
            t = get_task(task_id)
            if t and t.status in ("done", "error"):
                # 发送最终结果
                if t.status == "done" and t.result:
                    final_data = {
                        "stage": "完成",
                        "progress": 100,
                        "status": "done",
                        "result": t.result.model_dump(mode="json")
                    }
                else:
                    final_data = {
                        "stage": t.stage or "错误",
                        "progress": 0,
                        "status": t.status,
                        "error": t.error
                    }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
