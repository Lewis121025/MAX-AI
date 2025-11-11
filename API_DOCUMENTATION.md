# 🚀 API 文档

Max AI Agent 提供 RESTful API 和 Web 界面两种交互方式。

## 📋 目录

- [Web 界面](#web-界面)
- [API 端点](#api-端点)
- [身份验证](#身份验证)
- [错误处理](#错误处理)
- [限流策略](#限流策略)

## 🌐 Web 界面

### 启动服务

```bash
# 开发模式
python start_web.py
# 或
python start_fastapi.py

# 生产模式
uvicorn src.fastapi_app:app --host 0.0.0.0 --port 5000 --workers 4
```

### 访问地址

- **主页**: http://localhost:5000
- **健康检查**: http://localhost:5000/health
- **性能指标**: http://localhost:5000/api/metrics

## 🔌 API 端点

### 1. 聊天接口

#### `POST /api/chat`

发送用户查询并获取 AI 响应（支持流式输出）。

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户查询内容 |
| session_id | string | 否 | 会话 ID（UUID 格式） |
| files | file[] | 否 | 上传的文件列表 |

**请求示例**:

```bash
curl -X POST http://localhost:5000/api/chat \
  -F "query=搜索最新的 AI 新闻" \
  -F "session_id=123e4567-e89b-12d3-a456-426614174000"
```

**响应格式** (Server-Sent Events):

```json
data: {"node": "session", "data": {"session_id": "..."}}

data: {"node": "fast_agent", "data": {
  "final_answer": "...",
  "total_time_ms": 1234,
  "llm_calls": 1,
  "success_rate": "3/3",
  "is_complete": true
}}

data: {"node": "done", "data": {}}
```

**错误响应**:

```json
{
  "error": true,
  "category": "validation_error",
  "message": "输入验证失败，请检查请求格式。",
  "details": {},
  "timestamp": "2025-11-11T10:30:00Z"
}
```

### 2. 会话管理

#### `GET /api/sessions`

获取所有会话列表。

**响应示例**:

```json
{
  "success": true,
  "sessions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2025-11-11T10:00:00",
      "title": "搜索最新的 AI 新闻"
    }
  ]
}
```

#### `POST /api/clear_session`

删除指定会话。

**请求体**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**响应**:

```json
{
  "success": true,
  "message": "会话已删除"
}
```

#### `GET /api/export_session`

导出会话历史。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| format | string | 否 | 导出格式（json/markdown，默认 json） |

**响应**:

- `format=json`: 返回 JSON 格式的会话数据
- `format=markdown`: 返回 Markdown 格式的对话记录

### 3. 健康检查

#### `GET /health`

检查系统健康状态。

**响应示例**:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-11T10:30:00Z",
  "components": {
    "web_server": "ok",
    "graph": "ok",
    "sessions_storage": "ok",
    "upload_storage": "ok"
  },
  "config": {
    "has_openrouter_key": true,
    "has_e2b_key": true,
    "has_tavily_key": true
  }
}
```

**状态码**:

- `200`: 系统健康
- `503`: 系统不健康（缺少必要配置或组件失败）

### 4. 性能指标

#### `GET /api/metrics`

获取系统性能指标。

**响应示例**:

```json
{
  "active_sessions": 5,
  "total_session_files": 12,
  "upload_folder_size_mb": 3.5,
  "timestamp": "2025-11-11T10:30:00Z"
}
```

### 5. 缓存管理

#### `GET /api/cache_stats`

获取缓存统计信息。

**响应示例**:

```json
{
  "total_entries": 100,
  "hit_rate": 0.85,
  "size_mb": 12.5
}
```

#### `POST /api/cache_clear`

清空所有缓存。

**响应**:

```json
{
  "success": true,
  "message": "缓存已清空"
}
```

## 🔐 身份验证

当前版本不包含身份验证。生产环境部署时建议添加：

- API Token 验证
- OAuth 2.0 集成
- JWT 认证

## ❌ 错误处理

### 错误分类

| 类别 | 说明 |
|------|------|
| `validation_error` | 输入验证错误 |
| `api_error` | 外部 API 调用失败 |
| `tool_error` | 工具执行错误 |
| `system_error` | 系统内部错误 |
| `timeout_error` | 请求超时 |
| `configuration_error` | 配置错误 |

### 错误响应格式

```json
{
  "error": true,
  "category": "error_category",
  "message": "用户友好的错误消息",
  "details": {
    "error_type": "ValueError",
    "error_message": "技术细节..."
  },
  "timestamp": "2025-11-11T10:30:00Z"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

## ⚡ 限流策略

### 请求限制

| 端点 | 限制 | 时间窗口 |
|------|------|----------|
| /api/chat | 10 请求 | 每分钟 |
| 其他 API | 60 请求 | 每分钟 |

### 文件上传限制

- **最大文件大小**: 16 MB
- **允许的文件类型**: txt, pdf, png, jpg, jpeg, gif, csv, py, md, json, html, css, js

## 🔒 安全特性

### 输入验证

- XSS 防护（移除脚本标签）
- SQL 注入防护
- 路径遍历防护
- 文件类型验证

### 会话管理

- UUID 格式验证
- 会话隔离
- 敏感数据过滤

### CORS 配置

通过环境变量 `ALLOWED_ORIGINS` 配置允许的来源：

```bash
export ALLOWED_ORIGINS="https://example.com,https://app.example.com"
```

## 📊 性能指标

### FastAgent 性能目标

- **简单查询**: < 800ms
- **复杂任务**: < 5s
- **LLM 调用**: 仅 1 次（仅用于结果润色）
- **幻觉风险**: 0（零 LLM 规划）

### 监控建议

1. 使用 `/health` 端点进行健康检查
2. 监控 `/api/metrics` 的性能指标
3. 设置日志告警（错误率、响应时间）

## 🚀 部署建议

### 开发环境

```bash
python start_fast_web.py
```

### 生产环境

使用 uvicorn：

```bash
# Uvicorn (推荐)
uvicorn src.fastapi_app:app --host 0.0.0.0 --port 5000 --workers 4

# 或使用 Gunicorn + Uvicorn workers
gunicorn src.fastapi_app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["uvicorn", "src.fastapi_app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
```

### 环境变量

```bash
# API 密钥
export OPENROUTER_API_KEY=your_key
export E2B_API_KEY=your_key
export TAVILY_API_KEY=your_key
export FIRECRAWL_API_KEY=your_key
export WEAVIATE_URL=http://localhost:8080

# 服务配置
export PORT=5000
export HOST=0.0.0.0
export ALLOWED_ORIGINS=https://your-domain.com
```

## 📝 示例代码

### Python 客户端

```python
import requests

# 发送聊天请求
response = requests.post(
    "http://localhost:5000/api/chat",
    data={
        "query": "搜索最新的 AI 新闻",
        "session_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    stream=True
)

# 处理流式响应
for line in response.iter_lines():
    if line:
        data = line.decode('utf-8')
        if data.startswith('data: '):
            print(data[6:])
```

### JavaScript 客户端

```javascript
// 使用 EventSource 接收流式响应
const eventSource = new EventSource('/api/chat?query=hello&session_id=xxx');

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  console.log('收到数据:', data);
  
  if (data.node === 'done') {
    eventSource.close();
  }
});

eventSource.addEventListener('error', (error) => {
  console.error('连接错误:', error);
  eventSource.close();
});
```

## 📚 更多资源

- [快速开始指南](QUICK_START_GUIDE.md)
- [部署文档](DEPLOYMENT.md)
- [故障排除](TROUBLESHOOT.md)
- [最终报告](FINAL_REPORT.md)
