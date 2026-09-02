from fastapi import FastAPI

# 创建 FastAPI 应用实例
app = FastAPI()

# 定义根路径的 GET 路由
@app.get("/")
async def root():
    return {"message": "Hello World"}