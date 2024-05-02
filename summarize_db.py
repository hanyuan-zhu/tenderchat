from config import api_key_qwen
from aiModel import QwenModel
from ai import call_model

import mysql.connector
import json

        
def table_sum_agent(structure,samples):
    '''
    ai agent to create the summary of the table
    '''
    tools = [
        {
        "type": "function",
        "function": {
            "name": "save_summary",
            "description": "将总结信息保存到数据库中。包对对整个表格以及每一列字段的总结。",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_summary": {
                        "description": "对表格功能用户的一句话总结",
                        "type": "string"
                    },
                        "column_summaries": {
                        "description": """
                        对每一个字段的一个总结，{
                            "column1_name": "Summary for column 1 based on the samples and structure.",
                            "column2_name": "Summary for column 2 based on the samples and structure."}
                            """,
                        "type": "dict"
                    }
                },
                "required": ["table_summary"]
            },
        },
        }
    ]

    role_setting = '''
    Prompt: "根据表格的结构和样本条目，总结表格的整体用途和每列存储的信息类型。为表格的总体用途生成一句详尽的总结，并为每一列创建一个详尽的总结字典。使用'save_summary'函数保存这些总结。"


        任务:
        1. 分析表格结构，确定其预定功能。
        2. 查看样本条目，了解每一列存储的数据类型及其对表格功能的贡献。
        3. 生成表格目的的详尽单句总结。
        4. 创建一个字典，为每一列生成总结，说明基于结构和样本的信息类型。
        5. 使用'save_summary'工具将生成的总结保存到数据库中。

        工具:
        - save_summary: 将生成的总结保存到数据库中的函数。该函数需要表格的一句话总结和每一列的总结字典。

        预期输出:
        - 表格整体的一句话总结。
        - 包含每列总结的字典。
        - 成功执行'save_summary'函数以保存这些总结。

        确保总结的准确性和相关性以符合所提供的结构和样本数据，并遵守使用'save_summary'函数的所需格式和详细要求。

      '''
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '数据表结构是：' + structure})
    messages.append({"role": "user","content": '表格样本条目是：' + samples})
    
    model_name = "qwen-plus" 
    response = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
    total_usage = 0
    call_model(response, messages)
    messages.append(response.message_to_append)
    total_usage += response.total_tokens

    max_loop_count = 10
    loop_count = 0
    while loop_count < max_loop_count and response.tool_calls:
        args = response.function_args

        if response.function_name == "save_summary":
            try:
                # function_result = save_summary(**json.loads(args))
                return args
            except Exception as e:
                function_result = {"error": str(e)}

        messages.append({
            "role": "tool",
            "content": f"{function_result}",
            "tool_call_id":response.tool_calls['id']
        })
        
        call_model(response, messages)
        total_usage += response.total_tokens
        messages.append(response.message_to_append)
    return response.content


# 建立数据库连接
connection = mysql.connector.connect(
    host="gz-cdb-5scrcjb5.sql.tencentcdb.com",
    user="db",
    password="dbdb905905",
    database="sele",
    port=63432
)

def get_tables(cursor):
    cursor.execute("SHOW TABLES")
    return [table[0] for table in cursor.fetchall()]

def get_table_structure(cursor, table_name):
    cursor.execute(f"SHOW CREATE TABLE {table_name}")
    return cursor.fetchone()[1]

def get_sample_data(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()
    # 将行数据转换成字符串，以便传递给AI分析器
    sample_str = "\n".join([str(row) for row in rows])
    return sample_str




def summarize_db():
    cursor = connection.cursor()
    tables = get_tables(cursor)
    results = []

    for table in tables:
        structure = get_table_structure(cursor, table)
        samples = get_sample_data(cursor, table)
        response = table_sum_agent(structure, samples)
        table_summary, columns_summary = table_sum_agent(**json.loads(response))
        results.append({
            "table": table,
            "summary": table_summary,
            "columns": columns_summary
        })

    cursor.close()
    connection.close()

    # 将结果保存为JSON文件
    with open('database_summary.json', 'w') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    summarize_db()

