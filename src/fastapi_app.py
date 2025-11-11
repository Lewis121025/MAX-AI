"""FastAPI Web 界面：提供高性能的异步 REST API。"""

from __future__ import annotations

import os
import sys
import json
import uuid
import traceback
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 彻底禁用 LangSmith 追踪
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from langchain_core.messages import HumanMessage, AIMessage, message_to_dict, messages_from_dict

from orchestrator.graph import create_graph
from agent.state import init_state
from utils.error_handling import get_logger, format_error_for_user, PerformanceMonitor

# 初始化日志
logger = get_logger(__name__)

# 明确指定static和templates目录
current_dir = Path(__file__).parent
app = FastAPI(title="Max AI Agent", version="2.0.0")

# 静态文件和模板
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(current_dir / "templates"))

# 添加自定义 url_for 过滤器以兼容 Flask 模板
def make_url_for(request: Request):
    """创建 url_for 函数工厂"""
    def url_for(name: str, **path_params):
        if name == "static":
            # Flask: url_for('static', filename='css/style.css')
            # FastAPI: /static/css/style.css
            filename = path_params.get('filename', '')
            return f"/static/{filename}"
        # 其他路由使用标准方式
        try:
            return request.url_for(name, **path_params)
        except:
            return f"/{name}"
    return url_for

# 不在这里设置全局，而是在每个响应中传入

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# 会话缓存
conversation_sessions: dict[str, dict] = {}

# 文件上传配置
UPLOAD_FOLDER = Path(__file__).parent.parent / 'data' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'docx', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'py', 'md', 'json', 'html', 'css', 'js', 'xlsx', 'xls', 'pptx', 'ppt'}

# 会话持久化
SESSIONS_DIR = Path(__file__).parent.parent / 'data' / 'sessions'
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# 初始化 LangGraph
graph = create_graph()


# --- Pydantic 模型 --- #
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    created_at: str
    title: str


# --- 辅助函数 --- #
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def save_session(session_id: str, messages: list):
    """保存会话到 JSON 文件，并同步到内存缓存。"""
    path = get_session_path(session_id)
    session_data = {
        'session_id': session_id,
        'created_at': datetime.now().isoformat(),
        'messages': [message_to_dict(msg) for msg in messages]
    }
    if path.exists():
        existing_data = json.loads(path.read_text('utf-8'))
        session_data['created_at'] = existing_data.get('created_at', session_data['created_at'])

    path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding='utf-8')

    conversation_sessions[session_id] = {
        "messages": messages,
        "created_at": datetime.fromisoformat(session_data['created_at'])
    }


def load_session(session_id: str) -> list:
    """从持久化或内存缓存加载会话。"""
    if session_id in conversation_sessions:
        return conversation_sessions[session_id].get("messages", [])

    path = get_session_path(session_id)
    if not path.exists():
        return []

    data = json.loads(path.read_text('utf-8'))
    messages = messages_from_dict(data.get('messages', []))
    created_at_str = data.get('created_at', datetime.now().isoformat())
    conversation_sessions[session_id] = {
        "messages": messages,
        "created_at": datetime.fromisoformat(created_at_str)
    }
    return messages


def delete_session_file(session_id: str):
    """删除会话（文件 + 内存）。"""
    path = get_session_path(session_id)
    if path.exists():
        path.unlink()
    conversation_sessions.pop(session_id, None)


def list_sessions() -> list:
    """列出所有会话，合并文件与内存记录。"""
    sessions: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for path in SESSIONS_DIR.glob('*.json'):
        try:
            data = json.loads(path.read_text('utf-8'))
            session_id = data.get('session_id')
            if not session_id:
                continue

            title = "新对话"
            if data.get('messages'):
                first_user_msg = next((msg for msg in data['messages'] if msg['type'] == 'human'), None)
                if first_user_msg:
                    title = first_user_msg['data']['content'][:50]

            sessions.append({
                'id': session_id,
                'created_at': data.get('created_at', '未知'),
                'title': title
            })
            seen_ids.add(session_id)
        except Exception as exc:
            logger.warning(f"无法加载会话 {path.name}: {exc}")

    for session_id, meta in conversation_sessions.items():
        if session_id not in seen_ids:
            messages = meta.get("messages", [])
            title = "新对话"
            if messages:
                first_user_msg = next((msg for msg in messages if isinstance(msg, HumanMessage)), None)
                if first_user_msg:
                    title = first_user_msg.content[:50]
            
            sessions.append({
                'id': session_id,
                'created_at': meta.get('created_at', datetime.now()).isoformat(),
                'title': title
            })

    sessions.sort(key=lambda x: x['created_at'], reverse=True)
    return sessions


def sanitize_input(text: str) -> str:
    """清理用户输入，防止 XSS。"""
    if not text:
        return ""
    
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text.strip()


def validate_session_id(session_id: str) -> bool:
    """验证会话 ID 格式。"""
    if not session_id or len(session_id) > 100:
        return False
    pattern = r'^[a-z0-9\-]+$'
    return bool(re.match(pattern, session_id.lower()))


# --- 路由 --- #
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "url_for": make_url_for(request)
    })


@app.post("/api/chat")
async def chat(
    query: str = Form(""),
    session_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(None)
):
    """处理聊天请求（流式响应，支持上下文）。"""
    try:
        query = query.strip()
        
        # 输入验证
        if not query and not files:
            raise HTTPException(status_code=400, detail='请输入查询内容或上传文件')
        
        # 清理输入，防止XSS
        query = sanitize_input(query)
        
        # 检测脚本标签
        if '<script' in query.lower() or 'javascript:' in query.lower():
            raise HTTPException(status_code=400, detail='输入包含不允许的脚本内容')

        # 检查查询长度
        if len(query) > 10000:
            raise HTTPException(status_code=400, detail='查询内容过长，请控制在10000字符以内')

        if not session_id:
            session_id = str(uuid.uuid4())
        elif not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail='无效的会话ID')

        # 处理文件上传
        uploaded_file_paths = []
        rejected_files = []
        if files:
            for file in files:
                if not file.filename:
                    continue
                    
                if not allowed_file(file.filename):
                    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '无扩展名'
                    rejected_files.append(f"{file.filename} (不支持的文件类型: .{file_ext})")
                    logger.warning(f"文件类型不支持: {file.filename}")
                    continue
                
                # 安全的文件名
                filename = "".join(c for c in file.filename if c.isalnum() or c in '._- ')
                save_path = UPLOAD_FOLDER / filename
                try:
                    content = await file.read()
                    save_path.write_bytes(content)
                    # 使用绝对路径字符串（Windows格式）
                    uploaded_file_paths.append(str(save_path.absolute()))
                    logger.info(f"文件已保存: {save_path.absolute()}")
                except Exception as e:
                    logger.warning(f"文件保存失败: {e}")
                    rejected_files.append(f"{file.filename} (保存失败: {str(e)})")
        
        # 如果有被拒绝的文件，返回错误
        if rejected_files:
            error_msg = f"以下文件无法上传:\n" + "\n".join(rejected_files)
            raise HTTPException(status_code=400, detail=error_msg)

        # 将文件路径附加到查询中
        if uploaded_file_paths:
            file_references = "\n".join([f"[用户上传了文件: '{path}']" for path in uploaded_file_paths])
            query = f"{query}\n{file_references}" if query else file_references
        
        # 从文件加载历史消息
        history_messages = load_session(session_id)
        
        async def generate():
            """生成流式响应（FastAgent 模式）。"""
            try:
                # 构建包含历史的状态
                current_messages = history_messages + [HumanMessage(content=query)]
                state = {
                    "messages": current_messages,
                    "uploaded_files": uploaded_file_paths
                }
                
                # 发送session_id给前端
                yield f"data: {json.dumps({'node': 'session', 'data': {'session_id': session_id}}, ensure_ascii=False)}\n\n"
                
                # FastAgent 执行（在线程池中运行同步代码）
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, graph.invoke, state)
                
                # 提取最终答案
                final_answer = result.get('final_answer', '')
                total_time_ms = result.get('total_time_ms', 0)
                llm_calls = result.get('llm_calls', 0)
                success_rate = result.get('success_rate', 'N/A')
                
                # 发送 FastAgent 结果
                response_data = {
                    'node': 'fast_agent',
                    'data': {
                        'final_answer': final_answer,
                        'total_time_ms': total_time_ms,
                        'llm_calls': llm_calls,
                        'success_rate': success_rate,
                        'is_complete': True
                    }
                }
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                
                # 保存历史
                final_messages = current_messages + [AIMessage(content=final_answer)]
                save_session(session_id, final_messages)
                
                # 发送完成信号
                yield f"data: {json.dumps({'node': 'done', 'data': {}})}\n\n"
            
            except Exception as e:
                logger.error(f"处理聊天请求时发生错误: {e}", exc_info=True)
                error_response = format_error_for_user(e)
                error_data = {'node': 'error', 'data': error_response}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(generate(), media_type='text/event-stream')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"初始化聊天请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=format_error_for_user(e))


@app.post("/api/save_session")
async def save_session_api(request: Request):
    """保存会话消息（用于在创建新会话前保存当前会话）"""
    try:
        data = await request.json()
        session_id = data.get('session_id')
        messages = data.get('messages', [])
        
        if not session_id or not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail='无效的会话ID')
        
        # 将前端传来的消息格式转换为 LangChain 消息格式
        from langchain_core.messages import HumanMessage, AIMessage
        langchain_messages = []
        for msg in messages:
            if msg.get('type') == 'human':
                langchain_messages.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('type') == 'ai':
                langchain_messages.append(AIMessage(content=msg.get('content', '')))
        
        if langchain_messages:
            save_session(session_id, langchain_messages)
        
        return JSONResponse(content={'success': True, 'message': '会话已保存'})
    except Exception as e:
        logger.error(f"保存会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'保存会话失败: {str(e)}')


@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话列表"""
    sessions = list_sessions()
    return JSONResponse(content={'success': True, 'sessions': sessions})


@app.post("/api/delete_session")
async def delete_session_api(request: Request):
    """删除会话"""
    try:
        data = await request.json()
        session_id = data.get('session_id')
        
        if not session_id or not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail='无效的会话ID')
        
        delete_session_file(session_id)
        return JSONResponse(content={'success': True, 'message': '会话已删除'})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'删除会话失败: {str(e)}')


@app.post("/api/clear_session")
async def clear_session(session_id: str = Form(...)):
    """清空指定会话"""
    if not validate_session_id(session_id):
        raise HTTPException(status_code=400, detail='无效的会话ID')
    
    delete_session_file(session_id)
    return JSONResponse(content={'status': 'success', 'message': '会话已清空'})


@app.get("/api/session_history")
async def session_history(session_id: str):
    """获取会话历史"""
    if not validate_session_id(session_id):
        raise HTTPException(status_code=400, detail='无效的会话ID')
    
    messages = load_session(session_id)
    return JSONResponse(content={
        'success': True,
        'session_id': session_id,
        'history': [message_to_dict(msg) for msg in messages]
    })


@app.get("/api/status")
async def status():
    """系统状态检查"""
    # 检查各个服务的配置状态
    import os
    
    return JSONResponse(content={
        "status": "running",
        "version": "2.0.0",
        "framework": "FastAPI",
        "sessions_count": len(conversation_sessions),
        "timestamp": datetime.now().isoformat(),
        # 前端兼容字段
        "llm": bool(os.environ.get('OPENROUTER_API_KEY') or os.environ.get('OPENAI_API_KEY')),
        "tools": {
            "tavily": bool(os.environ.get('TAVILY_API_KEY')),
            "e2b": bool(os.environ.get('E2B_API_KEY')),
            "firecrawl": bool(os.environ.get('FIRECRAWL_API_KEY'))
        },
        "memory": bool(os.environ.get('WEAVIATE_URL'))
    })


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "Max AI Agent",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/api/templates")
async def get_templates():
    """获取任务模板"""
    from utils.task_templates import task_templates
    return JSONResponse(content=task_templates)


@app.get("/api/cache_stats")
async def cache_stats():
    """获取缓存统计"""
    try:
        from utils.cache import get_cache_stats
        stats = get_cache_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache_clear")
async def cache_clear():
    """清空缓存"""
    try:
        from utils.cache import clear_cache
        clear_cache()
        return JSONResponse(content={'status': 'success', 'message': '缓存已清空'})
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def metrics():
    """获取系统指标"""
    try:
        import psutil
        
        metrics_data = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "sessions_count": len(conversation_sessions),
            "timestamp": datetime.now().isoformat()
        }
        return JSONResponse(content=metrics_data)
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    
    debug_mode = '--debug' in sys.argv or os.environ.get('FASTAPI_DEBUG') == '1'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    print("=" * 60)
    print("🚀 Max AI Agent (FastAPI)")
    print(f"📍 访问: http://{host}:{port}")
    print(f"🔧 调试模式: {'开启' if debug_mode else '关闭'}")
    print(f"📚 API 文档: http://{host}:{port}/docs")
    print(f"🔍 ReDoc: http://{host}:{port}/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "fastapi_app:app",
        host=host,
        port=port,
        reload=debug_mode,
        log_level="info"
    )
