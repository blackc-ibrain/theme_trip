from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.trip import router as trip_router

app = FastAPI(title="Happy Trip Planner API")

# CORS:后面 L9 接前端时需要,先打开
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 健康检查
@app.get("/health")
def health():
    return {"status": "ok"}

# 业务路由
app.include_router(trip_router, prefix="/api")