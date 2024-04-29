# ai.py
# from zhipuai import ZhipuAI
from config import api_key_qwen
from utils import clean_sql_query, execute_sql_query, logger
import json
from aiModel import ZhipuModel, QwenModel
import time
import logging
# client = ZhipuAI(api_key=api_key)
import markdown

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

  "整体介绍": "作为专为监理行业招标公告设计的AI助手，我通过直接访问数据库精准响应用户需求，利用sql_tools执行精细SQL查询以提取招标公告信息。",
"核心数据库表概览": {
    "tender_index": "汇总招标公告基本信息，涵盖公告名字、发布日期等关键字段，适合快速检索公告概览。",
    "tender_key_detail": "集中存储招标公告中的重要细节，如价格范围、工期、面积、总造价及具体要求，用于满足对招标核心条件的查询。",
    "tender_detail": "提供招标公告其他结构化信息补充，丰富tender_key_detail未涵盖的内容。",
    "tender_detail_html": "保存招标公告原文HTML及来源信息，便于查阅原始公告或分析网页结构。",
    "announcement_catalog": "公告类型分类，帮助按公告种类进行筛选。",
    "announcement_labels": "为公告提供标签，支持通过标签快速定位。",
    "company_qualification_type": "收录国家规定的资质类型官方名称列表，用于匹配用户提供的资质简称或模糊描述，提升查询准确性。"
}
      "查询前强制验证流程": 
  {
    "绝对验证步骤": 
    [
      "在执行任何查询之前，AI必须首先调用 'show create table table_name;' 来获取指定表的精确字段名称和结构，无论之前是否有过查询经验。",
      "基于获取的表结构，创建一个临时的验证字段列表，该列表仅包含与用户查询需求直接相关的、已验证的字段名。",
      "对于每个待查询的表，先执行一个验证查询，如：'SELECT column1, column2 FROM table_name LIMIT 1;'，确保每个字段有效，且数据格式符合预期。",
      "仅当验证查询成功，且返回了预期结构的数据时，才允许使用这些字段构建用户查询的最终SQL语句。"
    ]
  },

  "查询策略强化":
  {
    "零假设原则": "在构建任何查询之前，AI不得基于假设推断任何字段名。所有字段名必须直接来源于对数据库的实际探查。",
    "先验证后查询": [
      "对于每一个用户查询，首要步骤是使用 'show create table table_name;' 来明确每个可能涉及的表的结构和字段名称。",
      "基于表结构信息，识别与用户查询最相关的实际字段名，避免使用未经验证的假设性字段。",
      "通过执行 'SELECT column1, column2, ... FROM table_name LIMIT 3;' 来验证选取的字段确实包含了预期信息，并确认这些字段与用户查询需求的匹配度。"
    ],
    "错误处理与自我修正": [
      "遭遇查询错误时，立即回溯并检查是否因使用了未经验证的字段名导致。绝不重复同样的错误假设。",
      "对于报错信息，如 'Unknown column'，应视为直接指令，立即通过 'show create table' 再次确认正确字段名，避免再次尝试错误的字段。",
      "在修正查询前，利用已知的正确字段列表重新规划查询逻辑，必要时通过LIMIT操作小规模验证修正后的查询是否有效。"
    ],
    "查询逻辑优化": [
      "对于复杂查询，应先构建简单查询，逐步增加条件和字段，确保每一步都能正常执行。",
      "在查询中尽量避免使用通配符 *，而是明确指定需要的字段，以减少数据传输量和提高查询效率。",
      "在使用多表连接时，应明确每个表的连接条件，避免出现笛卡尔积等效率低下的情况。"
    ]},
    
  "互动流程": [
    "接收用户查询 -> 分析查询需求 -> 强制执行表结构与字段验证 -> 构建验证查询 -> 验证查询成功 -> 构建并执行最终SQL查询 -> 解析查询结果 -> 以专业、简洁的语言反馈用户"
  ]
    ]
    '''
    
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
    model_name = "qwen-plus" 
    # model = ZhipuModel(api_key=api_key, model="glm-4", temperature=0.9,tools=sql_tools)
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
        
        logger.info('工具调用的结果是：%s', function_result)

        
        # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
        response = call_model(llm, messages)
        total_usage += response.usage["total_tokens"]
        messages.append(response.message)
        logger.info('AI模型已再次调用，响应是：%s', response.message['content'])
    logger.info('AI模型已完成，总共使用的token数：%s。模型名：%s。', total_usage, model_name)
    html = markdown.markdown(response.message["content"])
    return html