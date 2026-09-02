# WeChat Content Publisher - 项目开发手册

## 一、项目整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户 (浏览器)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓ HTTP (JSON)
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ App.tsx │  │  api.ts │  │ index.css│  │  components  │  │
│  │ 主界面   │  │ API请求 │  │  样式    │  │  (内联在App) │  │
│  └─────────┘  └─────────┘  └──────────┘  └──────────────┘
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓ HTTP REST API (/api/v1/*)
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    api/ (路由层)                     │    │
│  │  articles.py  │  drafts.py  │  publish.py  │ config  │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  services/ (业务逻辑)                 │    │
│  │  article_service.py │ ai_service.py │ publish_service│    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   clients/ (外部服务)                 │    │
│  │  ai/__init__.py      │  wechat/__init__.py           │    │
│  │  (OpenCode/DeepSeek) │  (微信文章抓取)                │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   models/ (数据模型)                  │    │
│  │  Article │ ArticleImage │ PublishRecord              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
        ┌──────────┐   ┌──────────┐   ┌──────────────┐
        │  SQLite  │   │  文件系统 │   │ 外部 AI API  │
        │  app.db  │   │  data/   │   │  OpenCode等  │
        └──────────┘   └──────────┘   └──────────────┘
```

---

## 二、项目目录结构

```
wechat-content-publisher/
├── start.bat              ← 一键启动脚本
├── stop.bat               ← 一键停止脚本
├── .gitignore
├── README.md
│
├── frontend/              ← 前端 (React + TypeScript + Vite)
│   ├── src/
│   │   ├── api.ts         ← 所有 API 请求函数
│   │   ├── App.tsx        ← 主界面 + 所有页面组件
│   │   ├── index.css      ← 全局样式
│   │   └── main.tsx       ← 入口文件
│   ├── package.json       ← 依赖配置
│   ├── tsconfig.json      ← TypeScript 配置
│   └── vite.config.ts     ← Vite 配置 (含代理)
│
├── backend/               ← 后端 (Python FastAPI)
│   ├── app/
│   │   ├── main.py        ← FastAPI 入口，注册路由
│   │   ├── config.py      ← 读取 .env 配置
│   │   ├── database.py    ← 数据库连接 + 初始化
│   │   ├── logging_config.py ← 日志配置
│   │   ├── provider_config.py ← AI 提供商配置
│   │   │
│   │   ├── api/           ← 路由层 (接收请求、返回响应)
│   │   │   ├── articles.py   ← 文章 CRUD
│   │   │   ├── drafts.py     ← AI 编辑
│   │   │   ├── publish.py    ← 发布
│   │   │   ├── images.py     ← 图片服务
│   │   │   └── config.py     ← 配置 API
│   │   │
│   │   ├── services/      ← 业务逻辑层
│   │   │   ├── article_service.py  ← 抓取、查询、保存
│   │   │   ├── ai_service.py       ← AI 编辑逻辑
│   │   │   └── publish_service.py  ← 头条发布
│   │   │
│   │   ├── clients/       ← 外部服务调用
│   │   │   ├── ai/        ← AI API 调用
│   │   │   │   └── __init__.py
│   │   │   └── wechat/    ← 微信文章抓取
│   │   │       ├── __init__.py
│   │   │       └── image_downloader.py
│   │   │
│   │   ├── models/        ← 数据库模型 (SQLAlchemy)
│   │   │   └── __init__.py
│   │   │
│   │   └── schemas/       ← 数据校验 (Pydantic)
│   │       └── __init__.py
│   │
│   ├── .env               ← 环境变量 (API Key 等)
│   ├── .env.example       ← 环境变量模板
│   └── requirements.txt   ← Python 依赖
│
└── data/                  ← 数据存储
    ├── app.db             ← SQLite 数据库
    ├── config.json        ← AI 提供商配置
    ├── logs/              ← 日志文件
    │   ├── app.log
    │   └── ai.log
    └── articles/          ← 文章图片
        └── {article_id}/
            ├── image_001.jpg
            ├── image_002.jpg
            └── ...
```

---

## 三、核心调用链

### 1. 抓取文章调用链

```
前端按钮点击
  → App.tsx:handleSubmit()
    → api.ts:api.fetchArticle(url)
      → fetch('/api/v1/articles/fetch', {method:'POST', body:{url}})
        ↓
后端路由
  → api/articles.py:fetch_article()
    → article_service.py:create_article_from_url()  ← 创建 Article 记录
    → article_service.py:fetch_and_parse()           ← 抓取+解析
      → wechat/__init__.py:fetch_html()              ← 下载网页
      → wechat/__init__.py:parse_article()           ← 解析 HTML
      → article_service.py:_download_images()        ← 下载图片
        → wechat/image_downloader.py                 ← 异步下载
      → 更新 Article (fetch_status='completed')
        ↓
前端响应
  → App.tsx:setArticle(article)
  → 显示文章列表
```

### 2. AI 编辑调用链

```
前端按钮点击
  → App.tsx:handleAIEdit()
    → api.ts:api.aiEdit(article.id)
      → fetch('/api/v1/ai/edit/{id}', {method:'POST'})
        ↓
后端路由
  → api/drafts.py:ai_edit()
    → ai_service.py:ai_edit_article()
      → 检查 ai_edit_status != 'processing'
      → 设置 ai_edit_status = 'processing'
      → clients/ai/__init__.py:generate_draft()
        → provider_config.py:get_provider_config()  ← 获取 AI 配置
        → _call_opencode() 或 _call_deepseek()      ← 调用 AI API
        → _parse_opencode_response()                ← 解析 JSON
      → 更新 Article.current_title/current_content
      → 设置 ai_edit_status = 'completed'
        ↓
前端响应
  → App.tsx:setArticle(updated)
  → 刷新编辑区域显示新内容
```

### 3. 保存文章调用链

```
前端按钮点击
  → App.tsx:handleSave()
    → api.ts:api.updateArticle(id, {title, content})
      → fetch('/api/v1/articles/{id}', {method:'PUT', body})
        ↓
后端路由
  → api/articles.py:update_article()
    → article_service.py:update_article_content()
      → 更新 Article.current_title/current_content
        ↓
前端响应
  → 显示保存成功
```

### 4. 发布调用链

```
前端按钮点击
  → App.tsx:handlePublish()
    → api.ts:api.publish(article.id)
      → fetch('/api/v1/publish/{id}', {method:'POST'})
        ↓
后端路由
  → api/publish.py:publish_article()
    → 查找最新 completed/approved 草稿
    → publish_service.py:publish_to_toutiao()
      → Playwright 连接 Chrome CDP
      → 打开头条创作页面
      → 填写标题和正文
      → 上传图片
      → 点击发布
    → ai_service.py:record_publish()  ← 创建 PublishRecord
        ↓
前端响应
  → 显示发布结果
```

### 5. 前端页面切换调用链

```
App.tsx 状态管理
  → page: 'list' | 'detail' | 'settings'
  → selectedArticleId: string | null

用户点击文章
  → handleSelectArticle(article)
    → setSelectedArticleId(article.id)
    → setPage('detail')

用户点击返回
  → handleBack()
    → setPage('list')
    → refreshList()
```

---

## 四、数据库结构

### articles 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | UUID |
| source_url | TEXT (UNIQUE) | 微信文章 URL |
| source_title | TEXT | 原始标题 |
| source_account | TEXT | 公众号名称 |
| author | TEXT | 作者 |
| publish_time | TEXT | 发布时间 |
| cover_path | TEXT | 封面路径 |
| original_html | TEXT | 原始 HTML |
| clean_html | TEXT | 清理后 HTML |
| content_text | TEXT | 纯文本正文 |
| **current_title** | TEXT | **当前编辑标题** |
| **current_content** | TEXT | **当前编辑内容** |
| **fetch_status** | TEXT | **抓取状态** |
| **ai_edit_status** | TEXT | **AI 编辑状态** |
| ai_edit_error | TEXT | AI 错误信息 |
| ai_edit_started_at | TEXT | AI 开始时间 |
| ai_edit_finished_at | TEXT | AI 完成时间 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### article_images 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | UUID |
| article_id | TEXT (FK) | 关联文章 |
| image_index | INTEGER | 图片序号 |
| original_url | TEXT | 原始 URL |
| local_path | TEXT | 本地路径 |
| created_at | TEXT | 创建时间 |

### publish_records 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | UUID |
| article_id | TEXT (FK) | 关联文章 |
| platform | TEXT | 平台 (toutiao) |
| title | TEXT | 发布时标题快照 |
| content_snapshot | TEXT | 发布时内容快照 |
| status | TEXT | 发布状态 |
| error_message | TEXT | 错误信息 |
| published_at | TEXT | 发布时间 |
| created_at | TEXT | 创建时间 |

---

## 五、API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/articles/fetch | 抓取文章 |
| GET | /api/v1/articles | 文章列表 |
| GET | /api/v1/articles/{id} | 文章详情 |
| PUT | /api/v1/articles/{id} | 保存内容 |
| DELETE | /api/v1/articles/{id} | 删除文章 |
| POST | /api/v1/ai/edit/{id} | AI 编辑 |
| POST | /api/v1/publish/{id} | 发布 |
| GET | /api/v1/images/{article_id}/{name} | 获取图片 |
| GET | /api/v1/config/providers | AI 提供商列表 |
| GET | /api/v1/config/provider | 当前配置 |
| POST | /api/v1/config/provider | 切换提供商 |
| POST | /api/v1/config/api-key | 保存 API Key |
| POST | /api/v1/config/model | 保存模型 |
| GET | /api/v1/config/models/{provider} | 获取模型列表 |

---

## 六、修改地图

| 需求 | 主要文件 | 可能涉及 |
|------|----------|----------|
| 修改文章列表显示 | `frontend/src/App.tsx` | `frontend/src/api.ts` |
| 修改 AI 提示词 | `backend/app/clients/ai/__init__.py` | - |
| 修改微信文章解析 | `backend/app/clients/wechat/__init__.py` | - |
| 修改图片下载 | `backend/app/clients/wechat/image_downloader.py` | - |
| 修改今日头条发布 | `backend/app/services/publish_service.py` | `backend/app/api/publish.py` |
| 添加新 AI 提供商 | `backend/app/provider_config.py` | `backend/app/clients/ai/__init__.py` |
| 修改数据库结构 | `backend/app/models/__init__.py` | `backend/app/database.py` |
| 修改前端样式 | `frontend/src/index.css` | - |
| 修改环境变量 | `backend/.env` | `backend/app/config.py` |

---

## 七、Debug 方法

### 前端按钮没反应

1. 浏览器 F12 → Console 查看 JS 错误
2. F12 → Network 查看请求是否发出
3. 检查请求 URL 和 HTTP Status
4. 查看后端日志 `data/logs/app.log`

### 后端返回 500

1. 查看 `data/logs/app.log` 中的错误堆栈
2. 检查 `backend/app/api/*.py` 路由是否正确
3. 检查 `backend/app/services/*.py` 业务逻辑

### AI 编辑失败

1. 检查 `data/logs/ai.log` 中的详细日志
2. 检查 API Key 是否配置
3. 检查网络连接
4. 检查 AI 返回格式是否合法 JSON

### 今日头条发布失败

1. 检查 Chrome 是否开启 `--remote-debugging-port=9222`
2. 检查是否已登录头条
3. 查看 `data/debug/toutiao_error.png` 截图
4. 检查页面 Selector 是否正确

---

## 八、启动和停止

### 启动
```bash
# 双击 start.bat
# 或
cd D:\workspace\IwanMoney\wechat-content-publisher
.\start.bat
```

### 停止
```bash
# 双击 stop.bat
# 或
.\stop.bat
```

### 访问
- 前端: http://localhost:5173
- 后端: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs

---

## 九、重要技术概念

### React useState
```tsx
const [page, setPage] = useState('list');
// page 是当前页面状态
// setPage('detail') 会触发组件重新渲染
```

### React useEffect
```tsx
useEffect(() => {
  loadArticle();  // 组件加载时执行
}, [articleId]);  // articleId 变化时重新执行
```

### async/await
```tsx
const handleAIEdit = async () => {
  const result = await api.aiEdit(id);  // 等待 API 返回
  setArticle(result);  // 更新状态
};
```

### FastAPI Router
```python
@router.post("/fetch")
def fetch_article(request: ArticleCreate, db = Depends(get_db)):
    # 路由函数接收请求，调用 service，返回响应
```

### SQLAlchemy Model
```python
class Article(Base):
    __tablename__ = "articles"
    id = Column(String(36), primary_key=True)
    # 定义数据库表结构
```

---

## 十、今日头条发布功能开发位置

```
Frontend:
  frontend/src/App.tsx → handlePublish() 函数
  frontend/src/api.ts → api.publish() 函数

Backend API:
  backend/app/api/publish.py → publish_article()

Service:
  backend/app/services/publish_service.py → publish_to_toutiao()

Playwright 逻辑:
  backend/app/services/publish_service.py 中的 Playwright 代码
```

---

## 十一、常见问题

### 数据库结构变更后
删除 `data/app.db`，重启后端会自动重建。

### 端口被占用
```bash
# 查找占用 8000 端口的进程
netstat -ano | findstr :8000
# 结束任务
taskkill /F /PID <pid>
```

### 前端代理配置
`frontend/vite.config.ts` 中配置了 `/api` 代理到后端。

---

*文档版本: v1.0*
*最后更新: 2026-09-02*
