from config import api_key_qwen
import mysql.connector
from mysql.connector import Error
import json
from utils import logger, clean_create_statement
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
import dashscope
from collections import defaultdict # merge documents by tender_id 的函数用


# 设置DashScope服务的API密钥
dashscope.api_key = api_key_qwen

###################################
# Database connection configuration
###################################
DB_CONFIG = {
    "host": "gz-cdb-5scrcjb5.sql.tencentcdb.com",
    "user": "db",
    "password": "dbdb905905",
    "database": "sele",
    "port": 63432
}

def connect_db():
    """Connect to the MySQL database."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Error while connecting to MySQL: {e}")
        return None


###################################
# SQL Search Agents
###################################

# 【Prompt】sqlAgent Component : "retrieval and Hints" 
def table_schema():
    """Generate the schema of a specific table (hardcoded for 'tender_key_detail_copy')."""
    connection = connect_db()
    if not connection:
        return "Connection error."
    cursor = connection.cursor()
    cursor.execute("SHOW CREATE TABLE tender_key_detail_copy")
    create_info = cursor.fetchone()
    return clean_create_statement(create_info[1])
def column_comments():
    """Return column comments as a JSON string."""
    columns = {
        'tender_id': '招标项目ID',
        'bid_price': '招标价格（元）',
        'construction_duration': '工期（天）',
        'construction_area': '建筑面积（平方米）',
        'construction_cost': '建安费（元）',
        'qualification_type': '监理企业资质类型,必须是来自于以下：房屋建筑工程、冶炼工程、矿山工程、化工石油工程、水利水电工程、电力工程、农林工程、铁路工程、公路工程、港口与航道工程、航天航空工程、通信工程、市政公用工程、机电安装工程，综合资质',
        'qualification_level': '监理企业资质等级',
        'qualification_profession': '总监注册资格证书专业',
        'title_level': '总监职称等级',
        'education': '总监学历',
        'performance_requirements': '总监相关业绩要求,例如，“至少担任过2项类似工程的监理负责人”',
        'simultaneous_projects_limit': '总监兼任项目限制,例如，“在任职期间能参与的其他在施项目不得超过2个”',
        'qualification_profession_addition': '附加信息',
        'title': '项目名称',
        'publish_date': '招标公告发布日期', 
        'province': '所在省份，例如“广东省”，不包含省级之外的地级市信息',
        'detail_link': '详情链接'
    }    
    return json.dumps(columns, indent=2, ensure_ascii=False)
def sample_entries(question):
    """Retrieve sample entries based on a question."""
    embeddings = DashScopeEmbeddings(model="text-embedding-v1", dashscope_api_key=api_key_qwen)
    persist_dir = "updated_tender_vector_store"
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    results = vectorstore.similarity_search(question, k=3)

    full_output = ""
    connection = connect_db()
    if connection:
        cursor = connection.cursor()
        try:
            # 获取并输出列名
            cursor.execute("SELECT * FROM tender_key_detail_copy WHERE FALSE")
            columns = [desc[0] for desc in cursor.description]
            header = ', '.join(columns)
            full_output += f"{header}\n"

            for result in results:
                # 确保之前的结果已经被完全处理
                while cursor.nextset():
                    pass

                query = f"SELECT * FROM tender_key_detail_copy WHERE tender_id = '{result.metadata['tender_id']}'"
                cursor.execute(query)
                sample_contents = cursor.fetchall()

                for row in sample_contents:
                    formatted_row = ', '.join(map(str, row))
                    full_output += f"{formatted_row}\n"

        finally:
            cursor.fetchall()
            cursor.close()
    connection.close()
    return full_output

# 【Tool】sqlAgent Component : "sql_query" 
def sql_query(query: str):
    """Execute an SQL query and return the results."""
    connection = connect_db()
    if not connection:
        return "Database connection failed."
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return result

# sqlAgent 输入: 用户问题(user_input), 额外信息(extra_info；输出: query, query_result, raw_response.output
def sqlAgent(user_input,extra_info=None):
    # 【考虑一下】当sql_query没有返回信息的时候，进行一次自查，看看是不是sql写错了。
    # 考虑把上一次的query 作为 extra info 输入，或者直接append message
    # 提供另一个 function call，就是报错 function call，以便于exit loop。
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
        }
    ]

    system_prompt = """
    基于用户的问题及元数据表的结构信息，构建正确的查询语句，使用sql_query工具去查询可回答问题的数据。
    逐步去思考，拆解问题关键词，仔细审阅相关注释，最终构建合适的查询语句。

    注意：不用输出任何信息，而是调用“sql_query”函数，传入查询语句。
    """

    messages = [
        {"role": "system", "content": system_prompt},
        *({"role": "user", "content": f"注意：额外的要求： {extra_info}"} if extra_info else []),
        {"role": "user", "content": f"用户的问题是: {user_input}"},
        {"role": "user", "content": f"元数据表的结构： {table_schema()}"},
        {"role": "user", "content": f"元数据注释： {column_comments()}"},
        {"role": "user", "content": f"元数据表数据示例： {sample_entries(user_input)}"}
    ]
    
    messages.append({"role": "user", "content": f"最后务必再提醒一次：“province”字段的值不包含省级之外的地级市信息，例如“广东省”，但包含“广州市、佛山市等”。"})    

    model_name = "qwen-max"
    temperature = 0.2
    
    # 工作区
    logger.info('SQL Agent（模型:%s）开始解析问题...', model_name)

    raw_response = dashscope.Generation.call(
        messages=messages,
        model=model_name,
        tools=tools,
        temperature=temperature,
        result_format='message'
    )
    # 检查HTTP响应状态码，除了200，就是4xx，或者5xx。
    if raw_response.status_code != 200:
        logger.error(f"Request failed with status code: {raw_response.status_code}")
        logger.error(f"Error Code: {raw_response.code}")
        logger.error(f"Error Message: {raw_response.message}")
        return None, "Service error, please try again later."
    
    if 'tool_calls' not in raw_response.output.choices[0].message:
        logger.error("No sql query generated by sqlAgent.")
        return None, "No query generated."

    arguments = raw_response.output.choices[0].message.tool_calls[0]['function']['arguments']   
    query = json.loads(arguments)["query"]
    query_result = sql_query(query)
    
    ## 工作区：
    logger.info(f'{raw_response.output.choices[0].message.content}\n')
    logger.info(f"开始执行查询【 {query}】...\n") # 这个可以不要，并不利于阅读
    logger.info(f"查询结果：{query_result}\n" if query_result else "查询结果为空。\n")
    
    return query, query_result, raw_response

# sqlRetrievalGrader: 判断上述query 和 query result 和user_input是否相关；输出 True or False (Boolean)
def sqlRetrievalGrader(user_input, query, query_result):
    # 【要改改】这里prompt和判断都要改成 True or False，类似 answer evaluation那个Agent。
    evaluation_prompt = (
    f"用户询问：'{user_input}'\n"
    f"为此问题设计的SQL查询是：\n{query}\n"
    f"执行的SQL查询产生了以下结果概要：\n"
    f"{('查询结果为空。' if not query_result else query_result)}\n"
    "\n请严格判断，此查询结果是否完美对应并能精确解答用户的问题。"
    "若结果完全符合，回答'是'；若有任何偏差、遗漏或信息不足之处，包括结果为空，请回答'否'。"
    "\n请仅回答'是'或'否'，无需额外解释。"
    )
    
    # 工作区logger:
    logger.info(f"Grader Agent 开始评估查询结果是否满足用户的问题。")
    
    # 调用DashScope模型进行评估
    model_name = "qwen-plus"
    temperature = 0.2
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )

    # 解析模型的回复
    ai_response = raw_response.output.choices[0].message.content.strip().lower()

    # 判断并返回结果
    if ai_response in ['是', 'yes']:
        #工作区logger:
        logger.info(f"PASS！")
        return True, ai_response
    else:
        logger.info(f"FAIL！准备语义查询。")
        return False, ai_response # 这里判断比较严格，除了yes，其他就算模棱两可，都算no。
# sqlRetrievalRefinement 提炼query_result信息，只保留和问题相关的信息
def sqlRetrievalRefinement(user_input, query, query_result):
    # 【要改改么？】其实不知道这个函数是不是有必要，sql的结果其实多余信息不多，也不知道这个能压缩多少信息。
    evaluation_prompt = (
        f"用户提问核心为：'{user_input}'\n"
        f"为此定制的SQL查询语句为：\n{query}\n"
        f"该查询返回的数据概览如下：\n{query_result}\n"
        "\n任务要求：从上述数据中，依据用户提问的实质，精心筛选并重新组织信息，"
        "务必确保所有紧要数据均被充分阐释，无遗漏。"
        "注意：筛掉和问题无关的信息，仅保留和问题有关的数据。"
    )
    
    # 工作区logger:
    logger.info(f"Refinement Agent 开始提炼和查询结果...")

    model_name = "qwen-plus"
    temperature = 0.2
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )
    refined_sql_retrievals = raw_response.output.choices[0].message.content
    
    # 工作区logger:
    logger.info(f"重整完毕！")
    logger.info(f"\n{refined_sql_retrievals}\n")
    
    return refined_sql_retrievals

# sqlSearch 函数：整合上述sql查询相关组件，实现用户问题到SQL查询到结果的流程
def sqlSearch(user_input,extra_info=None):
    query,sql_query_result,_= sqlAgent(user_input,extra_info)
    if query:
        sql_retrieval_grader_result = sqlRetrievalGrader(user_input, query, sql_query_result)
        if sql_retrieval_grader_result[0]:
            sql_retrieval_refined_result = sqlRetrievalRefinement(user_input, query, sql_query_result)
            return sql_retrieval_refined_result
        else:
            return None
    else:
        return None

####################################
# Semantic Search Agents
####################################

# retrievalPlanner ：输入用户问题，输出 1. 元数据筛选条件和核心查询内容（纯文本）2. api full response
def retrievalPlanner(user_input):
    system_prompt = """
        
    **任务说明：**
    你的任务是分析用户提出的问题，并根据给定的元数据结构信息，精确识别出用于数据筛选的条件以及提炼出剩余的查询主体。确保筛选条件紧密贴合元数据字段，输出结果简洁明了。

    **输入信息：**
    - **用户问题**：“佛山市市政工程在4月的标有哪些？他们开标时间都是什么时候？”

    **操作步骤：**
    1. **细致分析问题**：
    - 深入理解问题的多维度意图，识别与元数据直接相关及间接相关的关键词或短语。

    2. **精准匹配元数据条件**：
    - 严格对照元数据结构信息，确认哪些关键词可以直接对应到现有元数据字段。例，“4月”与“发布时间”关联，“市政工程”于“企业资质要求”相关。

    3. **明确筛选条件**：
    - 将直接与元数据字段匹配的部分提取为筛选条件，以自然语言形式表述。本例中，筛选条件为“4月市政工程”。

    4. **提炼查询主体**：

    剔除已用于筛选条件的部分后，剩余的内容即为核心查询问题。

    **输出格式：**
    - **元数据筛选条件**：明确指出用于数据筛选的条件，此处为“4月市政工程”。
    - **核心查询内容**：去除筛选条件后，保留并优化的查询主体，即“佛山市有哪些标，开标时间都是什么时候”。

    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"注意：**用户的问题**是: {user_input}"},
        {"role": "user", "content": f"**元数据注释**： {column_comments()}"},
        {"role": "user", "content": f"**元数据表数据示例**： {sample_entries(user_input)}"}
    ]
    
    model_name = "qwen-max"
    temperature = 0.2
    
    logger.info('语义搜索Agent(%s)开始解析问题...', model_name)
    
    raw_response = dashscope.Generation.call(
        messages=messages,
        model=model_name,
        temperature=temperature,
        result_format='message'
    )
    
    ai_response = raw_response.output.choices[0].message.content
    
    return ai_response,raw_response

# sqlAgent_for_tender_id ： 输入retrievalExecAgent的输出，调用sql_query函数，获取tender_id列表 
# 这里本质上是之前 sqlAgent改的，作为semantic search 的元数据retrieval工具

def sqlAgent_for_tender_id(query,extra_info=None):
    # 【要改】注意：这里没有处理没有命中函数的情况，即 tool_calls 为空的情况。这个实际上需要做 repetitive 处理。
    tools = [
        {
        "type": "function",
        "function": {
            "name": "sql_query_tender_id",
            "description": "此函数负责执行传入的MySQL查询语句，并返回查询结果。它专门用于检索数据，不支持修改、删除或更新数据库的操作。这包括但不限于仅执行SELECT查询语句。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "description": "一个有效的MySQL SELECT查询语句，用于从数据库中检索数据。务必只查询tender_id字段：SELECT tender_id FROM ... WHERE ...",
                        "type": "string"
                    }
                },
                "required": ["query"]
            },
        },
        }
    ]
    
    system_prompt = """
    基于输入的信息及元数据表的结构信息，使用sql_query_tender_id 工具去查询和输入要求相关的数据的tender_id。
    注意：不用直接输出，而是调用“sql_query_tender_id”函数，传入查询语句。
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        *({"role": "user", "content": f"注意：额外的要求： {extra_info}"} if extra_info else []),
        {"role": "user", "content": f"输入的要求是: {query}"},
        {"role": "user", "content": f"元数据表的结构： {table_schema()}"},
        {"role": "user", "content": f"元数据注释： {column_comments()}"},
        {"role": "user", "content": f"元数据表数据示例： {sample_entries(query)}"}
    ]
    
    model_name = "qwen-plus"
    temperature = 0.2
        
    raw_response = dashscope.Generation.call(
        messages=messages,
        model=model_name,
        tools=tools,
        temperature=temperature,
        result_format='message'
    )
    
    
    # 检查HTTP响应状态码
    if raw_response.status_code != 200:
        print(f"Request failed with status code: {raw_response.status_code}. Error: {raw_response.message}")
        return None, [], None

    tool_calls = raw_response.output.choices[0].message.get('tool_calls', [])
    if not tool_calls:
        print("No tool calls found in the successful response.")
        return None, [], raw_response.output.choices[0].message.content

    query_call = tool_calls[0]  # 假设只有一个tool call
    query = query_call['function']['arguments']

    # 直接在handle_tool_calls中处理SQL查询逻辑，简化主函数
    tender_ids = handle_and_extract_tender_ids(raw_response)

    return query, tender_ids, raw_response.output.choices[0].message.content

# retrievalExecAgent : 输入retrievalPlanner的输出，iteratively调用函数执行完Planner要求的查询工作，输出retrieval result
def retrievalExecAgent(user_input):
    tools = [
        {
        "type": "function",
        "function": {
            "name": "retrieval",
            "description": "这个是一个通过retrieve信息的Agent，所有参数都是输入“自然语言描述”。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sqlquery": {
                        "description": "这里输入“元数据筛选条件，必须自然语言描述。”",
                        "type": "string"
                    },
                    "semanticquery": {
                        "description": "这里输入核心查询内容，必须自然语言描述。",
                        "type": "string"
                    }

                },
                "required": ["sqlquery","semanticquery"]
            },
        },
        },
    ]
    
    system_prompt = """
    基于意图识别Agent的输出，你详细分析，retrieval函数来获取结果。
    "元数据筛选条件"的内容输入到sqlquery参数里，"核心语义查询内容"的内容输入到semanticquery参数，获取相关的招标公告信息。
    你的任务主要就识别这两个部分内容，然后调用相应的函数。
    分析的内容务必省略，直接调用函数。
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"注意：**意图识别Agent的输出**是: {user_input}"},
    ]
    
    import dashscope
    dashscope.api_key = api_key_qwen
    model_name = "qwen-plus"
    temperature = 0.2
    
    logger.info('AI model initialized: %s', model_name)
    
    
    result = []
    
    print(messages)
    
    raw_response = dashscope.Generation.call(
        messages=messages,
        model=model_name,
        tools=tools,
        temperature=temperature,
        result_format='message'
    )
    
    print(raw_response)
    
    if raw_response.output is None:
        logger.error("Error: dashscope.Generation.call did not return a result.")
        return None, raw_response

    tool_call = raw_response.output.choices[0].message.tool_calls[0]
    function_name = tool_call['function']['name']
    arguments = json.loads(tool_call['function']['arguments']) 

    if function_name == 'retrieval':
        sqlquery = arguments['sqlquery']
        semanticquery = arguments['semanticquery']
        
        #工作区logger:
        logger.info(f"要筛选的元数据条件是: {sqlquery}；\n 要从招标公告中查询的信息是: {semanticquery}")
        
        tender_ids = [] # 这里包括下面if语句，目的就是万一tender_ids回复的空集，就等于让semantic_search没有filter限制。
        if sqlquery:
            _, tender_ids, _ = sqlAgent_for_tender_id(sqlquery)
        result = semantic_search(semanticquery, tender_ids)
        
        #工作区logger:
        logger.info(f"相关片段搜索完毕，总共查询到{len(result)}条相关片段信息。")

    return result ,raw_response


# 【sqlAgent_for_tender_id 的辅助函数】处理tool_calls，提取tender_ids；
def handle_and_extract_tender_ids(raw_response):
    # 【一定会改】其实这个函数有点reduntant，因为只有一个tool call，直接提取就行了。历史原因才造成有它。
    tool_call = raw_response.output.choices[0].message.tool_calls[0]  # 假定只有一个tool call
    query_args = json.loads(tool_call['function']['arguments'])

    try:
        tender_id_query = preprocess_query (query_args['query'])        
        function_result = sql_query(tender_id_query)
        tender_ids = [item[0] for item in function_result]
    except (ValueError, KeyError):
        print("Error parsing SQL query result or unexpected format.")
        tender_ids = []

    return tender_ids

# 【sql_query_tender_id的辅助函数】以确保只返回tender_id字段
def preprocess_query(query):
    expected_start = "SELECT tender_id"
    if not query.strip().startswith(expected_start):
        raise ValueError(f"Query must start with '{expected_start}'")
    return query

# 【retrievalExecAgent的工具函数】semantic_search函数：纯粹通过embedding，semantic查询招标公告信息 
def semantic_search(query,tender_ids,top_k=80,persist_dir = "tender_chunks_vectors_v4"):

    embeddings = DashScopeEmbeddings(model="text-embedding-v1", dashscope_api_key=api_key_qwen)
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)


    if tender_ids:
        retrieval = vectorstore.similarity_search(
            query=query,
            k=top_k,
            filter={"tender_id": {"$in": tender_ids}}
        )
    else:
        retrieval = vectorstore.similarity_search(
            query=query,
            k=top_k
        )
    return retrieval

# merge_documents_by_tender_id 函数：将招标公告信息按照tender_id合并
# 输入：documents，一个包含招标公告信息的列表
# 输出：一个字典，键为tender_id，值为包含相同tender_id的招标公告信息的列表

def merge_documents_by_tender_id(documents):
    # 创建一个默认为列表的字典
    tender_id_to_contents = defaultdict(list)
    tender_id_to_metadata = {}

    # 遍历 documents，将每个 page_content 添加到其对应的 tender_id 列表中
    for document in documents:
        tender_id = document.metadata['tender_id']
        tender_id_to_contents[tender_id].append(document.page_content)
        tender_id_to_metadata[tender_id] = document.metadata

    # 将每个 tender_id 列表中的 page_content 合并为一个字符串
    for tender_id, contents in tender_id_to_contents.items():
        tender_id_to_contents[tender_id] = ' --- Next Chunk --- '.join(contents)
    
    # 创建一个新的文档列表，每个文档是一个字典，包含 text 和 metadata
    merged_documents = [
        {"text": content, "metadata": tender_id_to_metadata[tender_id]}
        for tender_id, content in tender_id_to_contents.items()
    ]

    return merged_documents

#  retrieval_grader : 输入用户问题和每一个merged retrieved document，判断retrieval结果是否与用户问题相关
def semantic_retrieval_grader(user_input, retrieval):
    evaluation_prompt = (
    f"用户询问：'{user_input}'\n"
    f"为此搜索到的招标公告内容片段是：\n{retrieval['text']}\n"
    # f"该内容对应的公告元数据是：\n{retrieval['metadata']}\n" # 这里comment掉是考虑grader是否需要对元数据进行判断。再三考虑后不太需要，因为sql搜索的时候，就已经对元数据进行的判断。
    "\n请严格判断，此查询结果是否完美对应并能精确解答用户的问题。"
    "若结果完全符合，回答'是'；若有任何偏差、遗漏或信息不足之处，包括结果为空，请回答'否'。"
    "\n请仅回答'是'或'否'，无需额外解释。"
    )

    # 调用DashScope模型进行评估
    model_name = "qwen-plus"
    temperature = 0.2
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )

    # 解析模型的回复
    ai_response = raw_response.output.choices[0].message.content.strip().lower()

    # 判断并返回结果
    if ai_response in ['是', 'yes']:
        return True, ai_response
    elif ai_response in ['否', 'no']:
        return False, ai_response
    else:
        return None, ai_response


# retrieval_refine: 输入用户问题和retrieval结果，输出精炼后的retrieval结果
def retrieval_refine(user_input, retrieval):
    evaluation_prompt = (
        f"用户提问内容为：'{user_input}'\n"
        f"为此搜索到的招标公告内容片段是：\n{retrieval['text']}\n"
        f"该内容对应的公告元数据是：\n{retrieval['metadata']}\n"
        "\n任务要求：从上述数据中，依据用户提问的实质，精心筛选并重新组织信息，以便于后续问答系统的回答。\n"
        "注意：仅仅提取和用户提问相关的信息！！！"
    )
    model_name = "qwen-plus"
    temperature = 0.2
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )
    refined_context = raw_response.output.choices[0].message.content
    return refined_context

# retrievalGraderAndRefinement: 输入merged retrieval结果，调用retrieval_grader和retrieval_refine，输出refined后的retrieval list
def retrievalGraderAndRefinement(question,merged_documents):
    # 这个grade的结果最好能够保存下来，这样之后可以来review。
    refined_results = []
    
    # 工作区logger:
    logger.info(f"开始相关片段进行整理...")
    
    for i in range(len(merged_documents)):
        grade,_ = semantic_retrieval_grader(question, merged_documents[i])
        if grade:
            refined_result = retrieval_refine(question, merged_documents[i])
            refined_results.append(refined_result)
            
            logger.info(f"第{i+1}个条片段：{refined_result}")
            
    return refined_results

# semanticSearch 的pipeline : 输入用户问题，输出最终的refined retrieval结果
def semanticSearch(user_input):    
    # 调用retrievalPlanner函数，获取元数据筛选条件和核心查询内容
    planner_output, _ = retrievalPlanner(user_input)
    
    # 调用retrievalExecAgent函数，执行retrievalPlanner的输出，获取retrieval结果
    retrieval_result, _ = retrievalExecAgent(planner_output)
    
    # 调用 merge_documents_by_tender_id 函数，将招标公告信息按照tender_id合并
    merged_documents = merge_documents_by_tender_id(retrieval_result)
    
    # 调用retrievalGraderAndRefinement函数，对retrieval结果进行评分和精炼
    refined_retrievals = retrievalGraderAndRefinement(user_input,merged_documents)
    
    logger.info(f"语义搜索结果整理完毕！")
    
    return refined_retrievals
###################################
# Answer Agents
###################################
# answerAgent 函数：生成结构化回答
def answerAgent(user_input,relevant_context):
    # 这里要修改，第一次sql如果无法回答到问题，用了semantic search后，sql的relevent_context也要保留，就是append semantic search出来的内容。
    answer_prompt = (
        "你是一个专注回答工程投标相关问题的AI助手。"
        f"用户提问核心为：'{user_input}'\n"
        f"查询返回的数据概览如下：\n{relevant_context}\n"
        "\n任务要求：从上述数据中，依据用户提问的实质，精心筛选并重新组织信息，"
        "务必确保所有紧要数据均被充分阐释，无遗漏。"
        "\n\n如果数据是列表形式，尝试将其转化为Markdown表格，例如：\n"
        "| Column 1 | Column 2 | Column 3 |\n"
        "| -------- | -------- | -------- |\n"
        "| Data 1   | Data 2   | Data 3   |\n"
        "\n如果数据是文本形式，尝试将其转化为有结构的段落，例如：\n"
        "1. 主题1：\n"
        "    - 细节1\n"
        "    - 细节2\n"
        "2. 主题2：\n"
        "    - 细节1\n"
        "    - 细节2\n"
        "\n最终的输出应该是一个结构化的回答，包含所有重要的信息，没有遗漏。"
        "\n基于查询的信息，尽可能内容丰富，详细地回答用户的问题。"
    )

    model_name = "qwen-max-longcontext" # 注意：这里使用max-longcontext模型，以容纳更多上下文(relevant_context)
    temperature = 0.2
    
    logger.info('Answer Agent(%s)正在审阅提供的资料，开始工作中...', model_name)
    
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": answer_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )

    ai_answer = raw_response.output.choices[0].message.content
    
    return ai_answer

# answerEvaluationAgent 函数：评估回答是否“全面且准确”
def answerEvaluationAgent(user_input, answer):
    """
    根据用户提问和回答的结果，利用专门的评估逻辑判断回答是否全面且准确，
    返回true/false。若判断为false，则触发Semantic Retrieval Agent。
    """
    evaluation_prompt = (
        f"用户提问为：'{user_input}'\n"
        f"回答为：\n{answer}\n"
        "\n任务要求：从上述问题和回答中，判断回答是否全面且准确，"
        "\n最终的仅输出true/false。"
        "\n注意：问题中的所有如果没有被未完整回答，必须判断为false。"
    )
    model_name = "qwen-max" # 因为回复仅仅为True or False，使用max不影响速度
    temperature = 0.2
    raw_response = dashscope.Generation.call(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model=model_name,
        temperature=temperature,
        result_format='message'
    )

    evaluate_result = raw_response.output.choices[0].message.content

    if "true" in evaluate_result.lower():
        return True
    elif "false" in evaluate_result.lower():
        return False
    else:
        return False # 出于信息严谨的考虑，若无法判断，则默认为False
    
def main(user_input):
    answer = ""
    evaluate_result = False

    retrieval_results = sqlSearch(user_input)
    if retrieval_results:
        answer = answerAgent(user_input,retrieval_results)
        evaluate_result = answerEvaluationAgent(user_input, answer)

    if not evaluate_result:
        retrieval_results = semanticSearch(user_input)
        if retrieval_results:
            answer = answerAgent(user_input,retrieval_results)
            evaluate_result = answerEvaluationAgent(user_input, answer)
            
    return answer

def get_ai_response(user_input):
    response = main(user_input)
    return response

# if __name__ == "__main__":
#     user_input = "三月招标价格最高的项目，其招标价格以及资质要求是什么？"
#     main(user_input)