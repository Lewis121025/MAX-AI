"""文档摄入脚本：将本地文档导入 Weaviate。"""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.weaviate_client import get_weaviate_client
from memory.rag_pipeline import ingest_document


def ingest_file(file_path: Path):
    """摄入单个文件。"""
    try:
        content = file_path.read_text(encoding="utf-8")
        
        metadata = {
            "filename": file_path.name,
            "file_type": file_path.suffix,
        }
        
        success = ingest_document(
            content=content,
            source=str(file_path),
            metadata=metadata,
        )
        
        if success:
            print(f"✅ {file_path.name}")
        else:
            print(f"❌ {file_path.name}")
    
    except Exception as e:
        print(f"❌ {file_path.name}: {e}")


def ingest_directory(directory: Path, extensions: list[str]):
    """摄入目录中的所有文件。"""
    files = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    
    if not files:
        print(f"⚠️ 未找到匹配的文件（扩展: {extensions}）")
        return
    
    print(f"📁 找到 {len(files)} 个文件")
    print("=" * 60)
    
    for file_path in files:
        ingest_file(file_path)


def main():
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="将文档导入 Weaviate 向量数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 摄入单个文件
  python scripts/ingest_docs.py --file docs/guide.md

  # 摄入整个目录
  python scripts/ingest_docs.py --dir docs/ --ext .md .txt

  # 初始化 schema
  python scripts/ingest_docs.py --init-schema
        """,
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="单个文件路径"
    )
    
    parser.add_argument(
        "--dir",
        type=str,
        help="目录路径"
    )
    
    parser.add_argument(
        "--ext",
        nargs="+",
        default=[".md", ".txt"],
        help="文件扩展名（默认: .md .txt）"
    )
    
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="初始化 Weaviate schema"
    )
    
    args = parser.parse_args()
    
    # 初始化 schema
    if args.init_schema:
        print("🔧 初始化 Weaviate schema...")
        client = get_weaviate_client()
        client.create_schema()
        return
    
    # 摄入文件
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {args.file}")
            return
        ingest_file(file_path)
    
    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"❌ 目录不存在: {args.dir}")
            return
        ingest_directory(dir_path, args.ext)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
