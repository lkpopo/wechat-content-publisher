# WeChat Content Publisher

微信公众号文章 → AI重新编辑 → 人工审核 → 今日头条自动发布

## 项目结构

```
wechat-content-publisher/
├── backend/          # Python FastAPI 后端
├── frontend/         # React + Vite 前端
├── data/             # 本地数据存储
│   ├── app.db        # SQLite 数据库
│   └── articles/     # 文章图片等文件
├── .env.example      # 环境变量模板
└── .gitignore
```

## 快速开始

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 OPENCODE_API_KEY
```

### 2. 安装后端依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. 安装前端依赖并启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 开发阶段

- [x] 第一阶段：微信文章解析 + 图片下载
- [ ] 第二阶段：AI 编辑集成
- [ ] 第三阶段：前端审核页面
- [ ] 第四阶段：今日头条自动发布
- [ ] 第五阶段：批量处理和稳定性

## API 文档

启动后端后访问：
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
