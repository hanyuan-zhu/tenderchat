from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
import json

def embedding():
    # 假设已经有一个包含数据库所有表及其字段摘要的JSON文件
    with open('database_summary.json', 'r') as f:
        database_summary = json.load(f)

    # 提取字段总结和对应的字段名
    field_summaries = []
    metadata_list = []

    for table in database_summary:
        # 对表级总结的处理
        field_summaries.append(table["summary"])
        metadata_list.append({"field_name": "", "table_name": table["table"]})

        # 对字段级总结的处理
        for column_name, column_summary in table["columns"].items():
            field_summaries.append(column_summary)  # 直接使用字段摘要字符串
            metadata_list.append({"field_name": column_name, "table_name": table["table"]})

    # 初始化 DashScope 嵌入模型
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v1", dashscope_api_key="sk-cbcc1fb859b1456885a270eecbec6369"
    )
    # # backup openai embedding
    # from langchain.embeddings import OpenAIEmbeddings
    # # 初始化嵌入模型
    # embeddings = OpenAIEmbeddings(openai_api_key="sk-proj-CmkZhJbSwXJv3FNYMv49T3BlbkFJHpq8bV7zuQOpe7ikfiSN")

    # 初始化向量存储,并添加嵌入向量和元数据
    vector_store = Chroma.from_texts(
        texts=field_summaries, 
        embedding=embeddings, 
        metadatas=metadata_list,
        persist_directory="vector_store"
        )

    # clear method 
    # vector_store.delete_collection()

if __name__ == '__main__':
    embedding()