"""数据分析工具：使用 Pandas 进行数据处理和分析。

功能：
- CSV/Excel 读取
- 数据清洗
- 统计分析
- 数据转换
- 结果导出
"""

from __future__ import annotations

import json
from typing import Optional, Any, Dict

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def data_analysis(
    operation: str,
    data_source: Optional[str] = None,
    **kwargs
) -> str:
    """
    数据分析工具函数
    
    参数:
        operation: 操作类型 (read/describe/filter/group/export)
        data_source: 数据源（文件路径或 JSON 字符串）
        **kwargs: 其他参数
    
    返回:
        分析结果
    """
    if not PANDAS_AVAILABLE:
        return "错误: 请安装 pandas: pip install pandas numpy"
    
    try:
        if operation == "read":
            file_type = kwargs.get("file_type", "csv")
            
            if file_type == "csv":
                df = pd.read_csv(data_source)
            elif file_type == "excel":
                df = pd.read_excel(data_source)
            elif file_type == "json":
                df = pd.read_json(data_source)
            else:
                return f"不支持的文件类型: {file_type}"
            
            # 返回基本信息
            info = {
                "行数": len(df),
                "列数": len(df.columns),
                "列名": list(df.columns),
                "前5行": df.head().to_dict(orient="records")
            }
            return json.dumps(info, ensure_ascii=False, indent=2)
        
        elif operation == "describe":
            # 从文件加载或直接使用数据
            if data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            elif data_source.endswith('.xlsx'):
                df = pd.read_excel(data_source)
            else:
                # 假设是 JSON
                df = pd.read_json(data_source)
            
            # 统计描述
            desc = df.describe().to_dict()
            return json.dumps(desc, ensure_ascii=False, indent=2)
        
        elif operation == "filter":
            if data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            else:
                df = pd.read_json(data_source)
            
            # 过滤条件
            column = kwargs.get("column")
            condition = kwargs.get("condition", ">")
            value = kwargs.get("value")
            
            if not column or value is None:
                return "错误: 需要提供 column 和 value"
            
            if condition == ">":
                filtered = df[df[column] > value]
            elif condition == "<":
                filtered = df[df[column] < value]
            elif condition == "==":
                filtered = df[df[column] == value]
            else:
                filtered = df
            
            return json.dumps(
                filtered.head(10).to_dict(orient="records"),
                ensure_ascii=False,
                indent=2
            )
        
        elif operation == "group":
            if data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            else:
                df = pd.read_json(data_source)
            
            group_by = kwargs.get("group_by")
            agg_column = kwargs.get("agg_column")
            agg_func = kwargs.get("agg_func", "mean")
            
            if not group_by or not agg_column:
                return "错误: 需要提供 group_by 和 agg_column"
            
            result = df.groupby(group_by)[agg_column].agg(agg_func)
            return json.dumps(
                result.to_dict(),
                ensure_ascii=False,
                indent=2
            )
        
        elif operation == "export":
            # 从kwargs获取数据
            data = kwargs.get("data", [])
            output_path = kwargs.get("output_path", "output.csv")
            
            df = pd.DataFrame(data)
            
            if output_path.endswith('.csv'):
                df.to_csv(output_path, index=False)
            elif output_path.endswith('.xlsx'):
                df.to_excel(output_path, index=False)
            else:
                df.to_json(output_path, orient="records")
            
            return f"数据已导出到: {output_path}"
        
        else:
            return f"未知操作: {operation}"
    
    except Exception as e:
        return f"数据分析错误: {e}"
