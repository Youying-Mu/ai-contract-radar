import os
from dotenv import load_dotenv
import pinecone
import time

# 加载环境变量
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "contract-rag")  # 默认名为contract-rag

def init_pinecone():
    """
    初始化 Pinecone 并返回索引对象
    """
    try:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY 环境变量未设置")
        
        # 初始化 Pinecone
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
        
        # 检查索引是否存在
        indexes = [idx['name'] for idx in pc.list_indexes()]
        print(f"可用的索引: {indexes}")
        
        if PINECONE_INDEX not in indexes:
            raise ValueError(f"Pinecone 索引 {PINECONE_INDEX} 未初始化，请用 Pinecone 控制台先创建并开启Integrated Embedding功能。")
        
        index = pc.Index(PINECONE_INDEX)
        return index
    except Exception as e:
        print(f"[init_pinecone] 初始化 Pinecone 失败: {e}")
        raise

def upsert_documents(docs):
    """
    批量插入文档到 Pinecone（使用 Integrated Embedding）

    参数:
        docs: 列表, 每个元素为 {"id": str, "text": str, "metadata": dict}
    返回:
        upsert 结果
    """
    index = init_pinecone()
    
    try:
        # 转换为 Pinecone Records API 需要的格式
        records = []
        for doc in docs:
            record = {
                "_id": doc["id"],  # 注意字段名是 _id 不是 id
                "text": doc["text"],  # 这是用于生成向量的字段
            }
            # 添加其他元数据字段（可选）
            if doc.get("metadata"):
                for key, value in doc["metadata"].items():
                    record[key] = value
            
            records.append(record)
        
        print(f"准备插入 {len(records)} 条记录")
        
        # 【修改点1】将 namespace="" 改为 namespace="__default__"
        res = index.upsert_records(
            namespace="__default__",  # ✅ 修改这里
            records=records
        )
        
        print(f"成功插入 {len(records)} 条记录")
        return res
    except Exception as e:
        print(f"[upsert_documents] 插入文档失败: {e}")
        # 打印更多调试信息
        import traceback
        traceback.print_exc()
        raise

def search_similar(query, top_k=3, namespace=""):
    """
    检索与 query 类似的合同条款（使用 Integrated Embedding）

    参数:
        query: str, 检索文本
        top_k: 返回结果条数
        namespace: 可选，索引空间
    返回:
        列表，每个元素包含 text、score 和 metadata
    """
    index = init_pinecone()
    
    try:
        # 【修改点2】处理空 namespace
        if namespace == "":
            namespace = "__default__"  # ✅ 修改这里
        
        # 使用 search_records 方法进行文本检索
        result = index.search(
            namespace=namespace,
            query={
                "inputs": {"text": query},  # 直接传入文本，Pinecone 自动转向量
                "top_k": top_k
            },
            fields=["text"]  # 指定要返回的字段
        )
        
        matches = []
        # 解析返回结果
        if result and 'result' in result and 'hits' in result['result']:
            for hit in result['result']['hits']:
                text = hit['fields'].get('text', '') if hit.get('fields') else ''
                score = hit.get('_score', 0)
                # 收集其他元数据
                metadata = {}
                if hit.get('fields'):
                    for key, value in hit['fields'].items():
                        if key != 'text':  # text 已经单独处理
                            metadata[key] = value
                
                matches.append({
                    "text": text,
                    "score": score,
                    "metadata": metadata,
                    "id": hit.get('_id', '')
                })
        
        return matches
    except Exception as e:
        print(f"[search_similar] 检索失败: {e}")
        import traceback
        traceback.print_exc()
        # 如果 search 方法失败，尝试备用方法
        try:
            print("尝试备用检索方法...")
            # 备用方法也要用 __default__
            result = index.query(
                top_k=top_k,
                include_metadata=True,
                text=query,
                namespace="__default__"  # ✅ 备用方法也要改
            )
            matches = []
            for match in result.get('matches', []):
                text = match['metadata'].get('text', '') if match.get('metadata') else ''
                score = match.get('score', 0)
                matches.append({
                    "text": text,
                    "score": score,
                    "metadata": match.get('metadata', {}),
                    "id": match.get('id', '')
                })
            return matches
        except:
            # 如果都失败，重新抛出原始异常
            raise

# ========== 测试示例 ==========
if __name__ == "__main__":
    print("=" * 50)
    print("开始测试 Pinecone Integrated Embedding")
    print("=" * 50)
    
    # 测试初始化
    print("\n>> 1. 初始化 Pinecone...")
    try:
        idx = init_pinecone()
        print("✅ Pinecone 索引对象获取成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        exit(1)
    
    # 示例合同条款数据
    docs = [
        {
            "id": "001",
            "text": "甲方应在收到货物后三日内支付合同约定的全部货款。",
            "metadata": {"clause_type": "付款条款"}
        },
        {
            "id": "002",
            "text": "乙方应保证所交付产品符合国家相关质量标准，如不符合应负责免费更换。",
            "metadata": {"clause_type": "质量保证"}
        },
        {
            "id": "003",
            "text": "如任一方违约，守约方有权要求对方赔偿全部损失。",
            "metadata": {"clause_type": "违约责任"}
        }
    ]
    
    # 测试插入
    print("\n>> 2. 批量upsert示例条款...")
    try:
        res = upsert_documents(docs)
        print(f"✅ upsert 返回: {res}")
        print("⏳ 等待2秒以确保向量生成...")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Upsert 失败: {e}")
    
    # 测试检索
    test_queries = [
        "货款支付时间",
        "产品质量问题",
        "违约赔偿"
    ]
    
    for query in test_queries:
        print(f"\n>> 3. 检索相似条款: [{query}] ...")
        try:
            results = search_similar(query, top_k=2)
            if results:
                for i, item in enumerate(results, 1):
                    print(f"\n   第{i}条 (相似度: {item['score']:.3f}):")
                    print(f"   条文: {item['text']}")
                    if item.get('metadata'):
                        print(f"   类型: {item['metadata'].get('clause_type', '未知')}")
            else:
                print("   没有找到相似条款")
        except Exception as e:
            print(f"❌ 检索失败: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)