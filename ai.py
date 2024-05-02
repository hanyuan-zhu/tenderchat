# ai.py
from config import api_key_qwen
from utils import logger, sql_query,table_info
import json
import time
from aiModel import QwenModel

from datetime import datetime
# 获取当前的本地时间
now = datetime.now()
local_date_string = now.strftime('%Y-%m-%d %H:%M:%S')

def call_model(llm, messages, max_retries=3):
    for i in range(max_retries):
        try:
            llm.call(messages)
            return
        except Exception as e:
            if i < max_retries - 1: 
                logger.error('在发送请求时发生错误: %s', e)
                time.sleep(2 ** i)
            else: 
                raise

def sqlAgent(user_input):
    tools = [
        {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "此函数负责执行传入的MySQL查询语句，并返回查询结果。它专门用于检索数据，不支持修改、删除或更新数据库的操作。这包括但不限于仅执行SELECT查询语句。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "一个有效的MySQL SELECT查询语句，用于从数据库中检索数据。",
                        "type": "string"
                    }
                },
                "required": ["query"]
            },
        },
        },
        {
        "type": "function",
        "function": {
            "name": "table_info",
            "description": "此函数接受一个关键词列表，基于这些关键词进行语义搜索，以识别和返回相关数据库表的结构和样例数据。主要用于获取和展示表的字段结构和前几条记录作为样本，辅助用户理解表的内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "description": "一个包含关键词的列表，这些关键词用于通过语义搜索来确定相关的数据库表和字段。",
                        "type": "list[string]"
                    }
                },
                "required": ["keywords"]
            },
        },
        }

    ]

    role_setting = '''
    AI Agent 概述：

    本AI Agent旨在提供一个智能的查询系统，专门为用户提供关于招标和投标信息的查询服务。通过先进的自然语言处理技术，本系统能够理解复杂的用户查询，返回准确的数据库查询结果。

    理解用户问题：

    输入：用户通过界面提出查询请求，例如：“最近三天有什么房建资质乙级能投的标”。
    处理：AI Agent使用深度学习模型首先解析用户查询，运用实体识别技术识别关键实体（如“最近三天”、“房建资质乙级”、“投标”）和意图（寻找符合条件的招标公告）。

    构造查询内容：

    操作：基于理解的用户意图和实体，AI构造一个适合语义搜索的查询字符串，如[“企业专业资质信息”，“招标公告发布时间”，“项目名称”]，以便检索相关的数据库记录。

    调用融合的 table_info() 工具：

    输入：使用AI构造的查询内容作为参数，调用 table_info(query_inputs) 函数，此函数基于关键词列表查询数据库表结构和样本数据，返回表结构和样本数据。
    处理：函数内部执行语义搜索，找到与查询内容匹配的表格和字段，然后构造展示表结构和获取样例数据的SQL语句。

    处理并返回结果：

    操作：AI Agent接收到包含表结构和样例数据的响应后，根据这些信息构造与问题相关的SQL语句，使用 sql_query 函数进行查询。此函数专用于执行SELECT查询语句，确保数据检索安全且不修改数据库内容。
    输出：根据查询结果，回答用户的问题。AI可以格式化输出，提供清晰的信息展示界面，使用户易于理解查询结果。

    错误处理与交互改进：

    如果查询结果不符合预期或AI检测到执行错误：
    1. AI自动判断错误类型（如查询无结果、结果异常等），并决定是否修正查询关键词或者补充新的查询信息。
    2. 如果需要更多的字段或表信息，AI将根据新的理解更新查询关键词，并重新调用table_info函数获取更多相关数据表信息。
    3. 通过友好的用户界面，向用户反馈当前查询状态和任何需要的进一步信息输入，以优化查询结果。用户可以通过界面直接调整查询参数或者重新定义查询条件。

    '''
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
    model_name = "qwen-plus" 
    response = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
    logger.info('AI模型已初始化：%s', model_name)
    total_usage = 0
    # 下面的循环核心是执行response.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
    call_model(response, messages)
    messages.append(response.message_to_append)
    total_usage += response.total_tokens
    logger.info('AI模型已调用：%s', response.content)

    max_loop_count = 5
    loop_count = 0
    while loop_count < max_loop_count and response.tool_calls:
        args = response.function_args
        logger.info('处理工具调用：%s', response.function_name)
        logger.info('工具调用参数：%s', args)

        # 这部分处理tool call，即不同的工具名调用不同的函数
        if response.function_name == "sql_query":
            try:
                function_result = sql_query(**json.loads(args))
            except Exception as e:
                function_result = {"error": str(e)}
        elif response.function_name == "table_info":
            try:
                function_result = table_info(**json.loads(args))
            except Exception as e:
                function_result = {"error": str(e)}

        # 添加tool call的结果到 messages序列里。
        messages.append({
            "role": "tool",
            "content": f"{function_result}",
            "tool_call_id":response.tool_calls['id']
        })
        
        logger.info('工具调用的结果是：%s', function_result)

        # 下面的循环核心是执行response = llm.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
        call_model(response, messages)
        total_usage += response.total_tokens
        messages.append(response.message_to_append)
        logger.info('AI模型已再次调用，响应是：%s', response.content)
    logger.info('AI模型已完成，总共使用的token数：%s。模型名：%s。', total_usage, model_name)
    return response.content


def get_ai_response(user_input):
    response = sqlAgent(user_input)
    return response
    
    
    
# # ###############
# 以下是待优化的代码，留给将来
# ###############
# # Configure logging
# import json
# import sys
# import time


# def handle_tool_call(response, tools):
#     """
#     根据工具配置和模型响应动态链接适当的函数来处理工具调用。

#     参数:
#     - response : object, QwenModel 的响应对象，包含工具调用的详细信息。
#     - tools : list of dict, 每个工具的配置，包括函数名称和其他元数据。
    
#     返回:
#     - 函数调用的结果，或者如果找不到合适的函数或调用失败，则返回错误消息。
#     """
#     if not response.tool_calls:
#         return "根据响应，无需进行工具调用。"

#     current_module = sys.modules[__name__]
#     function_name = response.function_name
#     tool_config = next((tool for tool in tools if tool["function"]["name"] == function_name), None)
    
#     if tool_config:
#         if hasattr(current_module, function_name):
#             func = getattr(current_module, function_name)
#             try:
#                 return func(**json.loads(response.function_args))
#             except Exception as e:
#                 return {"error": str(e)}
#         else:
#             return {"error": f"当前模块中找不到名为 {function_name} 的函数"}
#     else:
#         return {"error": f"未找到函数 {function_name} 的工具配置"}

# def abstractAgent(messages, tools, model, max_attempts=5, max_retries=3):
#     """
#     处理消息、工具交互和带重试的模型调用的抽象代理函数。

#     参数:
#     - messages : list of dict, 初始消息，包括角色和内容。
#     - tools : list of dict, 可用的工具及其配置。
#     - model : object, 模型类的实例，配备了必要的方法如 call()。
#     - max_attempts : int, 工具交互循环的最大尝试次数。
#     - max_retries : int, 调用模型时错误的最大重试次数。
#     """
#     total_usage = 0

#     def call_model_with_retries():
#         for i in range(max_retries):
#             try:
#                 response = model.call(messages)
#                 return response
#             except Exception as e:
#                 if i < max_retries - 1:
#                     logger.error('模型调用错误：%s。正在重试...', e)
#                     time.sleep(2 ** i)  # 指数退避
#                 else:
#                     logger.error('最后尝试失败。错误：%s', e)
#                     raise
    
#     try:
#         response = call_model_with_retries()
#         total_usage += response.total_tokens
#         logger.info('初始模型调用完成，内容：%s', response.content)
        
#         for attempt in range(max_attempts):
#             if not response.tool_calls:
#                 break
            
#             tool_response = handle_tool_call(response, tools)
#             messages.append({"role": "tool", "content": str(tool_response), "tool_call_id": response.tool_calls['id']})
#             logger.info('已处理工具调用，结果：%s', tool_response)
            
#             response = call_model_with_retries()
#             logger.info('模型重新调用，更新了消息。')

#     except Exception as e:
#         logger.error('处理过程中出现错误：%s', str(e))
#         return {"error": str(e)}
    
#     logger.info('抽象代理已完成。总共使用的令牌数：%d。', total_usage)
#     return response.content


# def sqlAgent(user_input):
#     tools = [
#         {
#         "type": "function",
#         "function": {
#             "name": "sql_query",
#             "description": "此函数负责执行传入的MySQL查询语句，并返回查询结果。它专门用于检索数据，不支持修改、删除或更新数据库的操作。这包括但不限于仅执行SELECT查询语句。",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "description": "一个有效的MySQL SELECT查询语句，用于从数据库中检索数据。",
#                         "type": "string"
#                     }
#                 },
#                 "required": ["query"]
#             },
#         },
#         },
#         {
#         "type": "function",
#         "function": {
#             "name": "table_info",
#             "description": "此函数接受一个关键词列表，基于这些关键词进行语义搜索，以识别和返回相关数据库表的结构和样例数据。主要用于获取和展示表的字段结构和前几条记录作为样本，辅助用户理解表的内容。",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "keywords": {
#                         "description": "一个包含关键词的列表，这些关键词用于通过语义搜索来确定相关的数据库表和字段。",
#                         "type": "list[string]"
#                     }
#                 },
#                 "required": ["keywords"]
#             },
#         },
#         }

#     ]

#     role_setting = '''
#     AI Agent 概述：

#     本AI Agent旨在提供一个智能的查询系统，专门为用户提供关于招标和投标信息的查询服务。通过先进的自然语言处理技术，本系统能够理解复杂的用户查询，返回准确的数据库查询结果。

#     理解用户问题：

#     输入：用户通过界面提出查询请求，例如：“最近三天有什么房建资质乙级能投的标”。
#     处理：AI Agent使用深度学习模型首先解析用户查询，运用实体识别技术识别关键实体（如“最近三天”、“房建资质乙级”、“投标”）和意图（寻找符合条件的招标公告）。

#     构造查询内容：

#     操作：基于理解的用户意图和实体，AI构造一个适合语义搜索的查询字符串，如[“企业专业资质信息”，“招标公告发布时间”，“项目名称”]，以便检索相关的数据库记录。

#     调用融合的 table_info() 工具：

#     输入：使用AI构造的查询内容作为参数，调用 table_info(query_inputs) 函数，此函数基于关键词列表查询数据库表结构和样本数据，返回表结构和样本数据。
#     处理：函数内部执行语义搜索，找到与查询内容匹配的表格和字段，然后构造展示表结构和获取样例数据的SQL语句。

#     处理并返回结果：

#     操作：AI Agent接收到包含表结构和样例数据的响应后，根据这些信息构造与问题相关的SQL语句，使用 sql_query 函数进行查询。此函数专用于执行SELECT查询语句，确保数据检索安全且不修改数据库内容。
#     输出：根据查询结果，回答用户的问题。AI可以格式化输出，提供清晰的信息展示界面，使用户易于理解查询结果。

#     错误处理与交互改进：

#     如果查询结果不符合预期或AI检测到执行错误：
#     1. AI自动判断错误类型（如查询无结果、结果异常等），并决定是否修正查询关键词或者补充新的查询信息。
#     2. 如果需要更多的字段或表信息，AI将根据新的理解更新查询关键词，并重新调用table_info函数获取更多相关数据表信息。
#     3. 通过友好的用户界面，向用户反馈当前查询状态和任何需要的进一步信息输入，以优化查询结果。用户可以通过界面直接调整查询参数或者重新定义查询条件。

#     '''
#     messages = [{"role": "system","content": role_setting}]
#     messages.append({"role": "user","content": '用户的问题是：' + user_input})
    
#     model_name = "qwen-plus" 
#     model = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
#     response_content = abstractAgent(messages, tools, model)
#     return response_content



# def get_ai_response(user_input):
#     response = sqlAgent(user_input)
#     return response
    