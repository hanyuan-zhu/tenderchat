# ai.py
# from zhipuai import ZhipuAI
from config import api_key
from utils import clean_sql_query, execute_sql_query, logger
import json
from aiModel import ZhipuModel, QwenModel
import time
import logging
# client = ZhipuAI(api_key=api_key)

from datetime import datetime
# 获取当前的本地时间
now = datetime.now()
# 将日期格式化为 'YYYY-MM-DD' 格式
local_date_string = now.strftime('%Y-%m-%d %H:%M:%S')

# system_message = {
#     "role": "system",
#     "content": {
#          "整体介绍": "作为一个招投标AI助手，你会帮助用户回答招标公告相关的信息",
#          "规则":"用户可能会使用不完整的名称或近似的文字，例如，'标'可能代表'招标公告'的项目；'资质'可能代表公司资质。项目名称可能只会给部分,而不是全称;今天的本地日期和时间是 {local_date_string}。",
#          "工具使用":"你的主要工作是识别用户的问题应该使用什么工具:当用户询问关于招标公告或监理招标的信息时，你会优先用sql_tools，根据问题的具体内容选择恰当的数据表进行SQL查询，用查询后返回的自有监理招标数据库内容回答。若不需要使用任何工具，则以专业的助手口吻回复。如果用户给的信息不足，则列出需要补充的信息。",
#     },
# }

# sql_tools = [
#     {
#         "type": "function",
#         "function": {
#             "name": "execute_sql_query",
#             "description":"""
#             我们需要生成一个SQL查询语句，它将用于从数据库中检索特定信息。在创建sql_query时，请遵循以下指南：
#             1. 查询语句应该简洁并符合数据库结构，同时满足用户查询的意图。
#             2. 对于时间相关的查询，优先在'tender_index'表中进行。
#             3. 对于价格、资质的查询，先在'tender_key_detail'表中尝试，资质优先考虑'qualification_type'和'qualification_level'字段,价格优先考虑'tender_key_detail'表中的'bid_price'字段
#             """,
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "sql_query": {
#                         "description": "将要在 MySQL 数据库上执行的命令语句 SQL query。此语句必须符合 SQL 语法规范，确保可以正确执行以获取预期的数据库信息。在数据库中，日期的格式是 'YYYY-MM-DD'，例如 '2024-04-24',搜索时检查不要加其他多余的符号",
#                         "type": "string"
#                         }
#                     },
#                 "required": ["sql_query"]
#             }
#         }
#     }
# ]

# database_intro={
#   "relations": "tender_index主表通过id关联tender_detail和tender_key_detail的tender_id。",
#    "tables": {
#     "tender_index": {
#       "purpose": "索引表，快速检索招标项目基本信息。",
#       "key_data": "id为唯一标识，title为项目名称，publish_time为发布时间，province为项目省份，source_platform为信息平台，info_type描述信息类别，business_type描述商业性质，industry为行业分类，detail_link为详细链接，detail_info_fetched标记详细信息是否已提取。"
#     },
#     "tender_detail": {
#       "purpose": "详细信息表，扩展tender_index内容。",
#       "key_data": "id为自增主键，tender_id关联tender_index，tender_document_start_time和end_time为招标文件有效期，question_deadline为答疑截止，answer_announcement_time为答疑公告，bid_submission_deadline为投标截止，bid_opening_time为开标时间，tenderer为招标人，tender_contact为招标联系人，contact_phone为联系电话，tender_agency为招标代理，tender_agency_contact为代理联系人，tender_agency_contact_phone为代理电话，supervision_qualification_requirement为公司资质要求，business_license_requirement为营业许可，chief_supervisor_qualification_requirement为总监资质，consortium_bidding_requirement为联合投标要求，project_name为项目名称，investment_project_code为投资代码，tender_project_name为招标项目，implementation_site为项目地点，funding_source为资金来源，tender_scope_and_scale为范围规模，duration为工期，maximum_bid_price为最高投标价，qualification_review_method为评审方法。"
#     },
#     "tender_key_detail": {
#       "purpose": "关键信息表，评估招标项目价格和资质。",
#       "key_data": "tender_id为关联主表的外键，bid_price为投标价格，construction_duration为工期天数，construction_area为建设面积，construction_cost为建安费，qualification_type为资质类型，qualification_level为资质级别，qualification_profession为总监专业资质要求，title_level为总监职称级别，education为总监教育背景要求，performance_requirements为总监业绩要求，simultaneous_projects_limit为总监同时项目限制，qualification_profession_addition为总监附加要求。"
#     }
#   },
# }

# llm = QwenModel(api_key="", model="qwen-turbo", temperature=0.9,tools=sql_tools)
# def first_response(messages):

#     logger.info('接收到消息')
#     response_one = llm(messages)
#     logger.info(f"这次对话使用的token总数: {response_one.usage.total_tokens}")
#     messages.append(response_one.message)
    
#     # 处理第一次ai结果
#     # 如果模型返回的消息中tool call了
#     if "tool_calls" in response_one.message:
#         role = "tool"
#         # 获取第一个tool调用
#         tool_call = response_one.message["tool_calls"][0]
#         # 获取tool调用时的参数arg
#         args = json.loads(tool_call["function"]["arguments"])
#         # sql_query = args['sql_query']
#         # logger.info('uncleaned sql query:'+sql_query)
#         # 初始化函数结果字典
#         function_result = {}
#         # cleaned_query = clean_sql_query(sql_query)
#         # 根据tools调用的函数选择，执行对应的函数
#         if tool_call["function"]["name"] == "execute_sql_query":
#             logger.info('启用数据库机器人')
#             # function_result = execute_sql_query(cleaned_query)
#             function_result = execute_sql_query(**args)
#             answer = json.dumps(function_result, ensure_ascii=False)
#     #没有tool call
#     else:
#         role = "assistant"
#         logger.info('默认助手分析中..')
#         answer =  response_one.message["content"]
#     return answer, role

# def ai_response(messages):
#     # log出最新的一条message
#     # logger.info('第一次的消息结果:' + json.dumps(messages[-1], ensure_ascii=False))
    
#     response = llm(messages)
#     logger.info(f"这次对话使用的token总数: {response.usage.total_tokens}")
#     answer ={}
#     if "tool_calls" in response.message:
#         role = "tool"
#         # 获取第一个tool调用
#         tool_call = response.message["tool_calls"][0]
#         # 获取tool调用时的参数arg
#         args = json.loads(tool_call["function"]["arguments"])
#         # sql_query = args['sql_query']
#         # logger.info('uncleaned sql query:'+sql_query)
#         # 初始化函数结果字典
#         function_result = {}
#         # cleaned_query = clean_sql_query(sql_query)
#         # 根据tools调用的函数选择，执行对应的函数
#         if tool_call["function"]["name"] == "execute_sql_query":
#             logger.info('启用数据库机器人')
#             # function_result = execute_sql_query(cleaned_query)
#             function_result = execute_sql_query(**args)
#             answer = json.dumps(function_result, ensure_ascii=False)
#             logger.info('返回答案：'+answer)
#     else:
#         answer=response.message["content"]
#         logger.info('返回答案：'+answer)
#         return answer

# def get_ai_response(user_input):
    
#     messages = [
#         system_message,
#         {
#             "role": "user",
#             "content": user_input
#         },
#         {
#             "role": "system",
#             "content": json.dumps(database_intro)
#         }
#     ]

#     first_answer, role = first_response(messages)
#     logger.info('第1次的消息结果:' + str(first_answer))
#     #第二次的system prompt
    
        
    
#     if role == "tool":
#         messages.append({
#             "role": role,
#             "content": "从数据库搜索后的结果是：" + str(first_answer) + "请判断是否成功查询，若未成功,请提供反馈告诉用户该如何正确提问，若成功查询，请以对话形式返回，确保用户能够直观地理解查询内容和结果,注意不要把sql语句发送给用户"
#         })
#         result = ai_response(messages)
#     else:  # role is "assistant"
#         result = first_answer
    
#     return result


# #####################################################
# #####################################################
# #####################################################
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
def get_ai_response(user_input):
    tools = [
    {
    "type": "function",
    "function": {
        "name": "sql_query",
        "description": "执行 MySQL SQL 查询并返回结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "description": "MySQL的命令语句 SQL query。此语句必须符合 SQL 语法规范，确保可以正确执行以获取预期的数据库信息。",
                    "type": "string"
                }
            },
            "required": ["query"]
        },
        }
    },
    ]

    role_setting = '''

    "整体介绍": "作为专为监理行业招标公告设计的AI助手，我通过直接访问数据库来精准响应用户的查询需求。我的核心能力在于利用唯一的工具sql_tools，针对结构化的招标公告信息执行SQL查询。",
    "数据库概况": "我所访问的数据库汇集了最新监理招标公告的结构化数据，这些数据经由AI处理，分布在多个精心设计的表格中，每个表格承载着不同维度的公告信息。",
    
    "查询策略":
    {
        "初步探索": [
        "首先，我将执行 'show tables;' 命令以获取所有数据表的名称列表，这有助于识别可能与用户查询相关联的表。",
        "随后，针对几个疑似相关的表，我将逐一执行 'show create table table_name;' 查询，以深入了解各表的结构、字段及其关联情况。"
        ],
        "信息筛选": [
        "基于表结构分析，我将精心挑选若干关键字段，这些字段应当与用户查询最为贴近。为避免信息过载，初期查询将限制展示条目数量，如：'SELECT column1, column2, ... FROM table_name LIMIT 3;'"
        ],
        "确认与构建查询": [
        "在初步验证所选字段包含解答所需信息后，我将构建一个针对性的SQL查询，确保该查询能够精确提取解答用户问题所需的所有数据。"
        ]
    },
    
    "互动流程": [
        "接收用户查询 -> 分析查询需求 -> 应用查询策略探索数据库 -> 确认信息适用性 -> 构建并执行SQL查询 -> 解析查询结果 -> 以专业、简洁的语言反馈用户"
    ],

    "注意事项": [
        "在整个过程中，我将保持对用户查询意图的高度敏感，确保每一步都紧密围绕用户需求进行。如果在任何阶段发现信息不足或不明确，我将主动向用户请求更多细节，以提升查询的准确性和效率。"
    ]

    
    '''
    
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
    # model = ZhipuModel(api_key=api_key, model="glm-4", temperature=0.9,tools=sql_tools)
    llm = QwenModel(api_key="", model="qwen-max", temperature=0.2,tools=tools)
    
    # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
    response = call_model(llm, messages)
    messages.append(response.message)
    logger.info('AI模型已调用，响应已添加到消息列表，响应是：%s', response.message['content'])

    
    max_loop_count = 3
    loop_count = 0
    while loop_count < max_loop_count and ("tool_calls" in response.message):
        tool_call = response.message["tool_calls"][0]
        args = tool_call["function"]["arguments"]
        logger.info('处理工具调用：%s', tool_call["function"]["name"])
        logger.info('工具调用参数：%s', args)

        
        # 这部分处理tool call，即不同的工具名调用不同的函数
        if tool_call["function"]["name"] == "sql_query":
            try:
                function_result = sql_query(**json.loads(args))
            except Exception as e:
                function_result = {"error": str(e)}
        
        # 添加tool call的结果到 messages序列里。
        messages.append({
            "role": "tool",
            "content": f"{json.dumps(function_result)}",
            "tool_call_id":tool_call['id']
        })
        
        logger.info('工具调用的结果已添加到消息列表，结果是：%s', function_result)

        
        # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
        response = call_model(llm, messages)
        messages.append(response.message)
        logger.info('AI模型已再次调用，响应已添加到消息列表，响应是：%s', response.message['content'])

    return response.message["content"]