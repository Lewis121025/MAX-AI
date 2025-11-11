"""Weaviate 客户端：向量数据库连接和操作。"""

from __future__ import annotations

from typing import Any

try:
    import weaviate
    from weaviate.classes.init import Auth
    from weaviate.classes.config import Property, DataType
except ImportError:
    weaviate = None

from config.settings import settings


class WeaviateClient:
    """Weaviate 向量数据库客户端。"""
    
    def __init__(self):
        """初始化客户端（懒加载）。"""
        self._client = None
        self._collection_name = "AgentMemory"
    
    @property
    def client(self):
        """获取或创建 Weaviate 客户端。"""
        if self._client is None:
            if not weaviate:
                raise ImportError(
                    "weaviate-client 未安装。请运行: pip install weaviate-client"
                )
            
            if not settings.weaviate_url:
                raise ValueError("WEAVIATE_URL 未配置")
            
            # 设置代理（如果配置了）
            import os
            if settings.http_proxy:
                os.environ['HTTP_PROXY'] = settings.http_proxy
            if settings.https_proxy:
                os.environ['HTTPS_PROXY'] = settings.https_proxy
            
            # 连接 Weaviate（支持云端和本地）
            if settings.weaviate_api_key:
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=settings.weaviate_url,
                    auth_credentials=Auth.api_key(settings.weaviate_api_key),
                )
            else:
                # 本地实例（无需认证）
                # 提取主机名（去掉协议和端口）
                host = settings.weaviate_url.replace("http://", "").replace("https://", "").split(":")[0]
                self._client = weaviate.connect_to_local(
                    host=host,
                    skip_init_checks=True,  # 跳过gRPC启动检查（本地开发环境）
                )
        
        return self._client
    
    def create_schema(self):
        """创建 AgentMemory 集合 schema。"""
        try:
            # 检查集合是否存在
            if self.client.collections.exists(self._collection_name):
                print(f"✅ 集合 '{self._collection_name}' 已存在")
                return
            
            # 创建集合（使用v4 API）
            self.client.collections.create(
                name=self._collection_name,
                description="Agent 对话和文档的长期记忆",
                properties=[
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="文本内容",
                    ),
                    Property(
                        name="source",
                        data_type=DataType.TEXT,
                        description="来源（conversation/document/tool）",
                    ),
                    Property(
                        name="timestamp",
                        data_type=DataType.TEXT,
                        description="时间戳",
                    ),
                    Property(
                        name="metadata",
                        data_type=DataType.TEXT,
                        description="JSON 格式的元数据",
                    ),
                ],
                # 本地Weaviate使用none vectorizer（无需外部API）
                vectorizer_config=None,
            )
            
            print(f"✅ 成功创建集合 '{self._collection_name}'")
        
        except Exception as e:
            print(f"⚠️ Schema 创建失败: {e}")
    
    def add_memory(
        self,
        content: str,
        source: str = "conversation",
        metadata: dict | None = None,
    ) -> str | None:
        """添加一条记忆。
        
        参数：
            content: 文本内容
            source: 来源类型
            metadata: 额外元数据
        
        返回：
            记忆 ID，或 None（如果失败）
        """
        try:
            from datetime import datetime
            import json
            
            collection = self.client.collections.get(self._collection_name)
            
            uuid = collection.data.insert(
                properties={
                    "content": content,
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": json.dumps(metadata or {}),
                }
            )
            
            return str(uuid)
        
        except Exception as e:
            print(f"⚠️ 添加记忆失败: {e}")
            return None
    
    def search_similar(
        self,
        query: str,
        limit: int = 5,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """相似度搜索。
        
        参数：
            query: 查询文本
            limit: 返回数量
            source_filter: 来源过滤（可选）
        
        返回：
            相似记忆列表
        """
        try:
            collection = self.client.collections.get(self._collection_name)
            
            # 构建查询
            query_builder = collection.query.near_text(
                query=query,
                limit=limit,
            )
            
            # 添加过滤（如果需要）
            if source_filter:
                query_builder = query_builder.where(
                    weaviate.classes.query.Filter.by_property("source").equal(source_filter)
                )
            
            response = query_builder.execute()
            
            # 格式化结果
            results = []
            for obj in response.objects:
                results.append({
                    "content": obj.properties.get("content", ""),
                    "source": obj.properties.get("source", ""),
                    "timestamp": obj.properties.get("timestamp", ""),
                    "metadata": obj.properties.get("metadata", "{}"),
                    "score": obj.metadata.distance if hasattr(obj.metadata, "distance") else None,
                })
            
            return results
        
        except Exception as e:
            print(f"⚠️ 搜索失败: {e}")
            return []
    
    def close(self):
        """关闭连接。"""
        if self._client:
            self._client.close()
            self._client = None


# 全局单例
_weaviate_client = None


def get_weaviate_client() -> WeaviateClient:
    """获取全局 Weaviate 客户端。"""
    global _weaviate_client
    if _weaviate_client is None:
        _weaviate_client = WeaviateClient()
    return _weaviate_client
