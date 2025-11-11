"""SQL 数据库工具：支持多种数据库的查询和操作。

支持的数据库：
- SQLite (本地文件)
- PostgreSQL
- MySQL
- SQL Server
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text, inspect
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class DatabaseTool:
    """数据库操作工具"""
    
    def __init__(self, connection_string: str):
        """
        初始化数据库连接
        
        参数:
            connection_string: SQLAlchemy 连接字符串
                例如: sqlite:///./data.db
                     postgresql://user:pass@localhost/db
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("需要安装: pip install sqlalchemy")
        
        self.engine = create_engine(connection_string)
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        执行 SELECT 查询
        
        参数:
            query: SQL 查询语句
            params: 查询参数
        
        返回:
            结果列表（字典格式）
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            
            # 转换为字典列表
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def execute_command(self, command: str, params: Optional[Dict] = None) -> int:
        """
        执行 INSERT/UPDATE/DELETE 命令
        
        参数:
            command: SQL 命令
            params: 命令参数
        
        返回:
            受影响的行数
        """
        with self.engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text(command), params or {})
                return result.rowcount
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """
        获取表结构
        
        返回:
            列信息列表
        """
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        return [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True)
            }
            for col in columns
        ]


def sql_database(
    operation: str,
    connection_string: str,
    query: Optional[str] = None,
    table: Optional[str] = None,
    **kwargs
) -> str:
    """
    SQL 数据库工具函数
    
    参数:
        operation: 操作类型 (query/command/tables/schema)
        connection_string: 数据库连接字符串
        query: SQL 语句
        table: 表名
        **kwargs: 其他参数
    
    返回:
        操作结果的 JSON 字符串
    """
    if not SQLALCHEMY_AVAILABLE:
        return "错误: 请安装 sqlalchemy: pip install sqlalchemy"
    
    try:
        db = DatabaseTool(connection_string)
        
        if operation == "query":
            if not query:
                return "错误: 需要提供 query 参数"
            results = db.execute_query(query, kwargs.get("params"))
            return json.dumps(results, ensure_ascii=False, indent=2)
        
        elif operation == "command":
            if not query:
                return "错误: 需要提供 query 参数"
            affected = db.execute_command(query, kwargs.get("params"))
            return f"成功: 影响了 {affected} 行"
        
        elif operation == "tables":
            tables = db.get_tables()
            return f"数据库表: {', '.join(tables)}"
        
        elif operation == "schema":
            if not table:
                return "错误: 需要提供 table 参数"
            schema = db.get_table_schema(table)
            return json.dumps(schema, ensure_ascii=False, indent=2)
        
        else:
            return f"未知操作: {operation}"
    
    except Exception as e:
        return f"数据库错误: {e}"


# 便捷函数：SQLite
def sqlite_query(db_path: str, query: str) -> str:
    """
    快速查询 SQLite 数据库
    
    参数:
        db_path: SQLite 数据库文件路径
        query: SQL 查询
    """
    conn_str = f"sqlite:///{db_path}"
    return sql_database("query", conn_str, query=query)
