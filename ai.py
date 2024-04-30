# ai.py
from config import api_key_qwen,api_key_zhipu
from utils import clean_sql_query, execute_sql_query, logger,table_details
import json
from aiModel import ZhipuModel, QwenModel
import time
import logging
import markdown

from datetime import datetime
# 获取当前的本地时间
now = datetime.now()
# 将日期格式化为 'YYYY-MM-DD' 格式
local_date_string = now.strftime('%Y-%m-%d %H:%M:%S')

import mysql.connector
def sql_query(query:str):
    connection = mysql.connector.connect(
        host="gz-cdb-5scrcjb5.sql.tencentcdb.com",
        user="db",
        password="dbdb905905",
        database="sele",
        port=63432  
    )
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    formatted_result = ", ".join([str(row) for row in result])
    return formatted_result



def call_model(llm, messages, max_retries=3):
    for i in range(max_retries):
        try:
            return llm.call(messages)
        except Exception as e:
            if i < max_retries - 1: 
                logger.error('在发送请求时发生错误: %s', e)
                time.sleep(2 ** i)
            else: 
                raise

###### 
# def get_ai_response(user_input):
#     tools = [
#     {
#     "type": "function",
#     "function": {
#         "name": "sql_query",
#         "description": "执行 MySQL SQL 查询并返回结果。",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "query": {
#                     "description": "MySQL的命令语句 SQL query。此语句必须符合 SQL 语法规范，确保可以正确执行以获取预期的数据库信息。",
#                     "type": "string"
#                 }
#             },
#             "required": ["query"]
#         },
#         }
#     },
#     ]

#     role_setting = '''

#   "整体介绍": "作为专为监理行业招标公告设计的AI助手，我通过直接访问数据库精准响应用户需求，利用sql_tools执行精细SQL查询以提取招标公告信息。",
# "核心数据库表概览": {
#     "tender_index": "汇总招标公告基本信息，涵盖公告名字、发布日期等关键字段，适合快速检索公告概览。",
#     "tender_key_detail": "集中存储招标公告中的重要细节，如价格范围、工期、面积、总造价及具体要求，用于满足对招标核心条件的查询。",
#     "tender_detail": "提供招标公告其他结构化信息补充，丰富tender_key_detail未涵盖的内容。",
#     "tender_detail_html": "保存招标公告原文HTML及来源信息，便于查阅原始公告或分析网页结构。",
#     "announcement_catalog": "公告类型分类，帮助按公告种类进行筛选。",
#     "announcement_labels": "为公告提供标签，支持通过标签快速定位。",
#     "company_qualification_type": "收录国家规定的资质类型官方名称列表，用于匹配用户提供的资质简称或模糊描述，提升查询准确性。"
# }
#       "查询前强制验证流程": 
#   {
#     "绝对验证步骤": 
#     [
#       "在执行任何查询之前，AI必须首先调用 'show create table table_name;' 来获取指定表的精确字段名称和结构，无论之前是否有过查询经验。",
#       "基于获取的表结构，创建一个临时的验证字段列表，该列表仅包含与用户查询需求直接相关的、已验证的字段名。",
#       "对于每个待查询的表，先执行一个验证查询，如：'SELECT column1, column2 FROM table_name LIMIT 1;'，确保每个字段有效，且数据格式符合预期。",
#       "仅当验证查询成功，且返回了预期结构的数据时，才允许使用这些字段构建用户查询的最终SQL语句。"
#     ]
#   },

#   "查询策略强化":
#   {
#     "零假设原则": "在构建任何查询之前，AI不得基于假设推断任何字段名。所有字段名必须直接来源于对数据库的实际探查。",
#     "先验证后查询": [
#       "对于每一个用户查询，首要步骤是使用 'show create table table_name;' 来明确每个可能涉及的表的结构和字段名称。",
#       "基于表结构信息，识别与用户查询最相关的实际字段名，避免使用未经验证的假设性字段。",
#       "通过执行 'SELECT column1, column2, ... FROM table_name LIMIT 3;' 来验证选取的字段确实包含了预期信息，并确认这些字段与用户查询需求的匹配度。"
#     ],
#     "错误处理与自我修正": [
#       "遭遇查询错误时，立即回溯并检查是否因使用了未经验证的字段名导致。绝不重复同样的错误假设。",
#       "对于报错信息，如 'Unknown column'，应视为直接指令，立即通过 'show create table' 再次确认正确字段名，避免再次尝试错误的字段。",
#       "在修正查询前，利用已知的正确字段列表重新规划查询逻辑，必要时通过LIMIT操作小规模验证修正后的查询是否有效。"
#     ],
#     "查询逻辑优化": [
#       "对于复杂查询，应先构建简单查询，逐步增加条件和字段，确保每一步都能正常执行。",
#       "在查询中尽量避免使用通配符 *，而是明确指定需要的字段，以减少数据传输量和提高查询效率。",
#       "在使用多表连接时，应明确每个表的连接条件，避免出现笛卡尔积等效率低下的情况。"
#     ]},
    
#   "互动流程": [
#     "接收用户查询 -> 分析查询需求 -> 强制执行表结构与字段验证 -> 构建验证查询 -> 验证查询成功 -> 构建并执行最终SQL查询 -> 解析查询结果 -> 以专业、简洁的语言反馈用户"
#   ]
#     ]
#     '''
    
#     messages = [{"role": "system","content": role_setting}]
#     messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
    
#     # model_name = "glm-4"
#     # llm = ZhipuModel(api_key=api_key_zhipu, model=model_name, temperature=0.9,tools=tools)
#     model_name = "qwen-plus" 
#     llm = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
#     logger.info('AI模型已初始化：%s', model_name)
#     total_usage = 0
#     # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
#     response = call_model(llm, messages)
#     messages.append(response.message)
#     total_usage += response.usage["total_tokens"]
#     logger.info('AI模型已调用：%s', response.message['content'])

    
#     max_loop_count = 10
#     loop_count = 0
#     while loop_count < max_loop_count and ("tool_calls" in response.message):
#         tool_call = response.message["tool_calls"][0]
#         args = tool_call["function"]["arguments"]
#         logger.info('处理工具调用：%s', tool_call["function"]["name"])
#         logger.info('工具调用参数：%s', args)

        
#         # 这部分处理tool call，即不同的工具名调用不同的函数
#         if tool_call["function"]["name"] == "sql_query":
#             try:
#                 function_result = sql_query(**json.loads(args))
#             except Exception as e:
#                 function_result = {"error": str(e)}
        
#         # 添加tool call的结果到 messages序列里。
#         messages.append({
#             "role": "tool",
#             "content": f"{json.dumps(function_result)}",
#             "tool_call_id":tool_call['id']
#         })
        
#         logger.info('工具调用的结果是：%s', function_result)

        
#         # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
#         response = call_model(llm, messages)
#         total_usage += response.usage["total_tokens"]
#         messages.append(response.message)
#         logger.info('AI模型已再次调用，响应是：%s', response.message['content'])
#     logger.info('AI模型已完成，总共使用的token数：%s。模型名：%s。', total_usage, model_name)
#     html = markdown.markdown(response.message["content"])
#     return html

from datetime import date

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date)):
            return obj.isoformat()  # 将日期对象转换为ISO格式的字符串
        return super(DateTimeEncoder, self).default(obj)


def tables():
    table_info ='''
    "核心数据库表概览": {
    "tender_index": "汇总招标公告基本信息，涵盖公告名字、发布日期等关键字段，适合快速检索公告概览。",
    "tender_key_detail": "集中存储招标公告中的重要细节，如价格范围、工期、面积、总造价及具体要求，用于满足对招标核心条件的查询。",
    "tender_detail": "提供招标公告其他结构化信息补充，丰富tender_key_detail未涵盖的内容。",
    "tender_detail_html": "保存招标公告原文HTML及来源信息，便于查阅原始公告或分析网页结构。",
    "announcement_catalog": "公告类型分类，帮助按公告种类进行筛选。",
    "announcement_labels": "为公告提供标签，支持通过标签快速定位。",
    "company_qualification_type": "收录国家规定的资质类型官方名称列表，用于匹配用户提供的资质简称或模糊描述，提升查询准确性。"
    }'''
    return table_info

def get_ai_response(user_input):
    tools = [
    {
    "type": "function",
    "function": {
        "name": "tables",
        "description": "返回数据库中所有表的名称及简要信息。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        }
    },
    {
    "type": "function",
    "function": {
        "name": "table_details",
        "description": "查询表的详细架构和前几行数据。",
        "parameters": {
            "type": "object",
            "properties": {
                "tables": {
                    "description": "表名列表，用于查询表的详细架构。如['table1', 'table2']",
                    "type": "list"
                }
            },
            "required": ["tables"]
        },
        }
    },

    ]

    role_setting = '''
    **职责**：
    - 接收用户问题。
    - 使用给定的Tools来分析问题，确定相关数据库表和字段。
    - 构建验证查询以获取表结构详情。
    - 根据验证结果，构建最终的SQL查询语句。

    **工作流程**:
    1. **理解问题**: 分析用户提问，识别可能涉及的业务领域和数据需求。
    2. **查询表信息**: 使用`tables` Tool 获取所有表的概览信息，以便初步筛选相关表。
    3. **获取表详情**: 对于初步筛选出的表，使用`table_details` Tool 获取详细架构和样本数据，进一步确认字段的有效性和数据格式。
    注意："table_details" Tool 输入参数为表名列表，比如感兴趣的表名是"table1"和"table2"，则输入参数为["table1", "table2"]。
    4. **构建SQL查询**: 基于验证过的字段信息，构建一个逻辑清晰、针对性强的SQL查询语句。
    5. **输出**: 向第二个AI代理(QueryExecutor & ResultInterpreter)传递构建好的SQL查询语句。

    '''
    
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
    
    # model_name = "glm-4"
    # llm = ZhipuModel(api_key=api_key_zhipu, model=model_name, temperature=0.9,tools=tools)
    model_name = "qwen-plus" 
    llm = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
    logger.info('AI模型已初始化：%s', model_name)
    total_usage = 0
    # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
    response = call_model(llm, messages)
    messages.append(response.message)
    total_usage += response.usage["total_tokens"]
    logger.info('AI模型已调用：%s', response.message['content'])

    
    max_loop_count = 10
    loop_count = 0
    while loop_count < max_loop_count and ("tool_calls" in response.message):
        tool_call = response.message["tool_calls"][0]
        args = tool_call["function"]["arguments"]
        logger.info('处理工具调用：%s', tool_call["function"]["name"])
        logger.info('工具调用参数：%s', args)

        
        # 这部分处理tool call，即不同的工具名调用不同的函数
        if tool_call["function"]["name"] == "tables":
            try:
                function_result = tables()
            except Exception as e:
                function_result = {"error": str(e)}
        elif tool_call["function"]["name"] == "table_details":
            try:
                function_result = table_details(**json.loads(args))
            except Exception as e:
                function_result = {"error": str(e)}

        
        # 添加tool call的结果到 messages序列里。
        messages.append({
            "role": "tool",
            # "content": f"{json.dumps(function_result)}",
            "content": f"{json.dumps(function_result, cls=DateTimeEncoder)}",
            "tool_call_id":tool_call['id']
        })
        
        logger.info('工具调用的结果是：%s', function_result)

        
        # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
        response = call_model(llm, messages)
        total_usage += response.usage["total_tokens"]
        messages.append(response.message)
        logger.info('AI模型已再次调用，响应是：%s', response.message['content'])
    logger.info('AI模型已完成，总共使用的token数：%s。模型名：%s。', total_usage, model_name)
    html = markdown.markdown(response.message["content"])
    return html
