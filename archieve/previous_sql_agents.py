
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

def QueryBuilder(user_input):
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
                  "description": "表名数组，用于查询表的详细架构。例如，如果需要查询'table_A'和'table_B'的详细信息，输入应为['table_A', 'table_B']。",
                  "type": "array",
                  "items": {"type": "string"}
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
    1. **理解问题**: 分析用户提问，通过识别关键词和短语（如“招标公告”、“监理行业”等）来关联到特定的数据库表或字段，明确用户的数据需求。
    2. **查询表信息**: 使用`tables` Tool 获取所有表的概览信息，以便初步筛选相关表。
    3. **获取表详情**: 对于初步筛选出的表，使用`table_details` Tool 获取详细架构和样本数据，进一步确认字段的有效性和数据格式。
    注意："table_details" Tool 输入参数为表名列表，比如感兴趣的表名是"table1"和"table2"，则输入参数为["table1", "table2"]。
    4. **构建SQL查询**: 基于验证过的字段信息，构建一个逻辑清晰、针对性强的SQL查询语句。
    5. **输出**: 向第二个AI代理(QueryExecutor & ResultInterpreter)传递构建好的SQL查询语句。
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

    max_loop_count = 10
    loop_count = 0
    while loop_count < max_loop_count and response.tool_calls:
        args = response.function_args
        logger.info('处理工具调用：%s', response.function_name)
        logger.info('工具调用参数：%s', args)

        # 这部分处理tool call，即不同的工具名调用不同的函数
        if response.function_name == "tables":
            try:
                function_result = tables()
            except Exception as e:
                function_result = {"error": str(e)}
        elif response.function_name == "table_details":
            try:
                function_result = table_details(**json.loads(args))
            except Exception as e:
                function_result = {"error": str(e)}

        print("方程结果类型:")
        print(type(function_result))
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


def QueryExecutor(user_input,prebuilt_sql_query):
    tools = [
        {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "执行MySQL SQL查询并返回结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "待执行的SQL查询语句。",
                        "type": "string"
                    }
                },
                "required": ["query"]
            },
        },
        }
    ]

    role_setting = '''
    **职责简述**：
      - 执行收到的SQL查询。
      - 筛选并解析查询结果。
      - 以清晰、简洁的方式回应用户查询。

    **操作步骤**:
      1. **接收查询**: 获取QueryBuilder准备好的SQL查询命令。
      2. **执行操作**: 利用`sql_query`工具执行数据库查询。
      3. **解析数据**: 检验查询结果，提取关键信息。
      4. **编制回复**: 根据查询目的，整理数据为易于理解的反馈，直接回应用户需求。

    **重点**:
      - 确保查询执行高效、准确，避免无关数据干扰。
      - 回复聚焦用户询问的核心，语言平实、专业。
      '''
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '用户的问题是：' + user_input})
    messages.append({"role": "user","content": '从QueryBuilder接收到的SQL查询建议是：' + prebuilt_sql_query})
    
    model_name = "qwen-plus" 
    response = QwenModel(api_key=api_key_qwen, model=model_name, temperature=0.2,tools=tools)
    logger.info('AI模型已初始化：%s', model_name)
    total_usage = 0
    # 下面的循环核心是执行response.call(messages)，如果出现错误，等待一段时间后再次尝试，最多尝试3次
    call_model(response, messages)
    messages.append(response.message_to_append)
    total_usage += response.total_tokens
    logger.info('AI模型已调用：%s', response.content)

    max_loop_count = 10
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

        print("方程结果类型:")
        print(type(function_result))
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

