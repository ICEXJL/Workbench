from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_business_tables
from routers import auth, logistics, reports, sales

app = FastAPI(title="订单管理系统 API", version="1.0.0")

# 允许 Vue 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为前端实际域名，如 https://bi.example.com
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(logistics.router, prefix="/api/v1")


@app.on_event("startup")
def startup() -> None:
    init_business_tables()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
