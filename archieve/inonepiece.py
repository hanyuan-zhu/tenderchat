# Standard library imports
import json
import logging
import re

# Third party imports
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from gevent import Greenlet, monkey
import gevent
from geventwebsocket import Resource, WebSocketApplication, WebSocketServer

# Local application imports
from zhipuai import ZhipuAI

# Patching should be done as early as possible
monkey.patch_all()

client = ZhipuAI(api_key="fa1467996b5f2018bcf1f49f1643cf43.908Q1sveABVE1WJc") # 请填写您自己的APIKey

# 创建了一个Flask应用实例，这个应用将处理HTTP请求。
app = Flask(__name__)
app.debug = True
app.secret_key = 'your-secret-key'

# 使用同一个logger记录所有的日志信息
logger = logging.getLogger('websocket_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('app.log', encoding='utf-8', delay=False)
file_handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

from datetime import datetime
# 获取当前的本地时间
now = datetime.now()
# 将日期格式化为 'YYYY-MM-DD' 格式
local_date_string = now.strftime('%Y-%m-%d %H:%M:%S')

import mysql.connector
def execute_sql_query(sql_query:str):
    connection = mysql.connector.connect(
        host="gz-cdb-5scrcjb5.sql.tencentcdb.com",  # 数据库主机地址
        user="buildsensePublic",  # 数据库用户名
        password="buildsense905",  # 数据库密码
        database="sele",  # 数据库名
        port=63432  # Corrected syntax for specifying the port argument
    )
    logger.info('已连接到标讯数据库')
    cursor = connection.cursor()

    try:
        # 执行SQL查询
        cursor.execute(sql_query)
        result = cursor.fetchall()  # 获取所有查询结果
        logger.info('数据查询中')
    
    # 如果结果是空的，返回一个默认的消息
        if not result:
           logger.info('没有查询到相关数据')
           result = {"message": f"对不起，没有查询到对应数据。查询的语句是 {sql_query}，可能的原因是查询条件不准确或者数据库中没有匹配的数据，请检查是否正确。"}
           return result
    except mysql.connector.Error as err:
        # 如果出现异常，将异常的信息添加到返回的结果中
        logger.info('数据查询异常'+str(err))
        result = {
            "message": f"查询过程中出现了错误：{str(err)}。请检查你的查询语句是否正确，或者是否存在其他问题。error_code: {err.errno}，sqlstate:{err.sqlstate} ,sql_query: {sql_query}"
        }
        return result
        
    finally:
        cursor.close()
        connection.close()
    # 格式化结果为字符串，以便返回
    formatted_result = ", ".join([str(row) for row in result])
    # print("formatted_result: " + formatted_result)
    logger.info('返回查询数据：'+formatted_result)
    return formatted_result

sql_tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description":"""
            我们需要生成一个SQL查询语句，它将用于从数据库中检索特定信息。在创建sql_query时，请遵循以下指南：
            1. 查询语句应该简洁并符合数据库结构，同时满足用户查询的意图。
            2. 对于时间相关的查询，优先在'tender_index'表中进行。
            3. 对于价格、资质的查询，先在'tender_key_detail'表中尝试，资质优先考虑'qualification_type'和'qualification_level'字段,价格优先考虑'tender_key_detail'表中的'bid_price'字段
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "description": "将要在 MySQL 数据库上执行的命令语句 SQL query。此语句必须符合 SQL 语法规范，确保可以正确执行以获取预期的数据库信息。在数据库中，日期的格式是 'YYYY-MM-DD'，例如 '2024-04-24',搜索时检查不要加其他多余的符号",
                        "type": "string"
                        }
                    },
                "required": ["sql_query"]
            }
        }
    }
]

system_message = {
    "role": "system",
    "content": {
         "整体介绍": "作为一个招投标AI助手，你会帮助用户回答招标公告相关的信息",
         "规则":"用户可能会使用不完整的名称或近似的文字，例如，'标'可能代表'招标公告'的项目；'资质'可能代表公司资质。项目名称可能只会给部分,而不是全称;今天的本地日期和时间是 {local_date_string}。",
         "工具使用":"你的主要工作是识别用户的问题应该使用什么工具:当用户询问关于招标公告或监理招标的信息时，你会优先用sql_tools，根据问题的具体内容选择恰当的数据表进行SQL查询，用查询后返回的自有监理招标数据库内容回答。若不需要使用任何工具，则以专业的助手口吻回复。如果用户给的信息不足，则列出需要补充的信息。",
    },
}

def clean_sql_query(query):
    """
    Cleans and corrects SQL queries to prevent common syntax errors and potential SQL injections.
    """

    # Replace the problematic characters
    query = query.replace("“", "'").replace("”", "'")
    # Ensure the encoding is correct
    query = query.encode('utf-8').decode('utf-8')

    # Function to replace double quotes with single quotes and escape inner single quotes
    def replace_quotes(match):
        inner_text = match.group(1).replace("'", "''")  # Escape single quotes by doubling them
        return f"'{inner_text}'"  # Wrap the corrected text in single quotes

    # Replace double quotes in the query using the 'replace_quotes' function
    query = re.sub(r'"([^"]*)"', replace_quotes, query)

    # Remove SQL comments to prevent injection via comments
    query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.MULTILINE | re.DOTALL)

    # Enforce the use of LIKE for title searches
    # 将 title = 'value' 转换为 title LIKE '%value%'
    query = re.sub(r"title = '([^']+)'", r"title LIKE '%\1%'", query)

    # Check for risky SQL patterns that might indicate SQL injection attempts
    if re.search(r"xp_|exec|execute|drop|update|delete|insert", query, re.IGNORECASE):
        logger.warning("Query contains risky keywords which are not allowed.")
        return None  # Return None or raise an exception if risky patterns are found

    logger.info('Cleaned SQL Query: ' + query)
    return query

def ai_response(messages):
    # log出最新的一条message
    # logger.info('第一次的消息结果:' + json.dumps(messages[-1], ensure_ascii=False))
    
    response = client.chat.completions.create(
        model="glm-4", # 填写需要调用的模型名称
        messages=messages,
        tools=sql_tools,
        tool_choice="auto",
    )
    logger.info(f"这次对话使用的token总数: {response.usage.total_tokens}")
    answer ={}
    if response.choices[0].message.tool_calls:
        # 获取第一个tool调用
        tool_call = response.choices[0].message.tool_calls[0]
        # 获取tool调用时的参数arg
        args = tool_call.function.arguments
        print(args)
        sql_query = args['sql_query']
        logger.info('使用机器人工具中，uncleaned sql query:'+sql_query)
        function_result = {}
        cleaned_query = clean_sql_query(sql_query)
        # 根据tools调用的函数选择，执行对应的函数
        if tool_call.function.name == "execute_sql_query":
            logger.info('再次启用数据库机器人')
            function_result = execute_sql_query(cleaned_query)
            answer = json.dumps(function_result, ensure_ascii=False)
            logger.info('返回答案：'+answer)
    else:
        answer=response.choices[0].message.content
        logger.info('返回答案：'+answer)
        return answer

def first_response(messages):
    logger.info('接收到消息')
    response_one = client.chat.completions.create(
        model="glm-4", # 填写需要调用的模型名称
        messages=messages,
        tools=sql_tools,
        tool_choice="auto",
    )
    logger.info(f"这次对话使用的token总数: {response_one.usage.total_tokens}")

    
    # 处理第一次ai结果
    # 如果模型返回的消息中tool call了
    if response_one.choices[0].message.tool_calls:
        role = "tool"
        # 获取第一个tool调用
        tool_call = response_one.choices[0].message.tool_calls[0]
        # 获取tool调用时的参数arg
        args = json.loads(tool_call.function.arguments)
        sql_query = args['sql_query']
        logger.info('uncleaned sql query:'+sql_query)
        # 初始化函数结果字典
        function_result = {}
        cleaned_query = clean_sql_query(sql_query)
        # 根据tools调用的函数选择，执行对应的函数
        if tool_call.function.name == "execute_sql_query":
            logger.info('启用数据库机器人')
            function_result = execute_sql_query(cleaned_query)
            answer = json.dumps(function_result, ensure_ascii=False)
    #没有tool call
    else:
        role = "assistant"
        logger.info('默认助手分析中..')
        answer =  response_one.choices[0].message.content
    return answer, role

database_intro={
  "relations": "tender_index主表通过id关联tender_detail和tender_key_detail的tender_id。",
   "tables": {
    "tender_index": {
      "purpose": "索引表，快速检索招标项目基本信息。",
      "key_data": "id为唯一标识，title为项目名称，publish_time为发布时间，province为项目省份，source_platform为信息平台，info_type描述信息类别，business_type描述商业性质，industry为行业分类，detail_link为详细链接，detail_info_fetched标记详细信息是否已提取。"
    },
    "tender_detail": {
      "purpose": "详细信息表，扩展tender_index内容。",
      "key_data": "id为自增主键，tender_id关联tender_index，tender_document_start_time和end_time为招标文件有效期，question_deadline为答疑截止，answer_announcement_time为答疑公告，bid_submission_deadline为投标截止，bid_opening_time为开标时间，tenderer为招标人，tender_contact为招标联系人，contact_phone为联系电话，tender_agency为招标代理，tender_agency_contact为代理联系人，tender_agency_contact_phone为代理电话，supervision_qualification_requirement为公司资质要求，business_license_requirement为营业许可，chief_supervisor_qualification_requirement为总监资质，consortium_bidding_requirement为联合投标要求，project_name为项目名称，investment_project_code为投资代码，tender_project_name为招标项目，implementation_site为项目地点，funding_source为资金来源，tender_scope_and_scale为范围规模，duration为工期，maximum_bid_price为最高投标价，qualification_review_method为评审方法。"
    },
    "tender_key_detail": {
      "purpose": "关键信息表，评估招标项目价格和资质。",
      "key_data": "tender_id为关联主表的外键，bid_price为投标价格，construction_duration为工期天数，construction_area为建设面积，construction_cost为建安费，qualification_type为资质类型，qualification_level为资质级别，qualification_profession为总监专业资质要求，title_level为总监职称级别，education为总监教育背景要求，performance_requirements为总监业绩要求，simultaneous_projects_limit为总监同时项目限制，qualification_profession_addition为总监附加要求。"
    }
  },
}
    
def get_ai_response(user_input):
    
    messages = [
        system_message,
        {
            "role": "user",
            "content": user_input
        },
        {
            "role": "system",
            "content": json.dumps(database_intro)
        }
    ]

    first_answer, role = first_response(messages)
    # logger.info('第1次的消息结果:' + str(first_answer))
    # 第二次的system prompt
    if role == "tool":
        messages.append({
            "role": role,
            "content": "从数据库搜索后的结果是：" + str(first_answer) + "请判断是否成功查询，若未成功,请提供反馈告诉用户该如何正确提问，若成功查询，请以对话形式返回，确保用户能够直观地理解查询内容和结果,注意不要把sql语句发送给用户"
        })
        result = ai_response(messages)
    else:  # role is "assistant"
        result = first_answer
        # result = ai_response(messages)
        # 以下是如果第一次返回的是assistant的也需要再过一次ai_response
        # content = first_answer
        # messages.append({
        #     "role": role,
        #     "content": content
        # })
    # result = ai_response(messages)
    return result

def follow(thefile):
    thefile.seek(0,2)  # Go to the end of the file
    while True:
        line = thefile.readline()
        if not line:
            gevent.sleep(1)  # Sleep briefly
            continue
        yield line
   
class LogSocketApp(WebSocketApplication):
    def on_open(self):
        logger.debug('WebSocket connection opened')
        # 打开日志文件并开始跟踪最新内容
        self.logfile = open('app.log', 'r', encoding='utf-8')
        self.loglines = follow(self.logfile)
        # 使用 Greenlet 而不是直接 spawn，这样你可以控制它
        self.log_sender = Greenlet.spawn(self.send_logs)
        
    def on_message(self, message):
        # 你可以在这里处理从客户端发来的消息
        logger.debug('Message received from client: %s', message)

    def send_logs(self):
        logger.debug('start send_logs')
        try:
            # 持续发送日志文件的新内容
            for line in self.loglines:
                self.ws.send(line.strip())
                logger.debug('Sent log data: %s', line.strip())
                gevent.sleep(0.1)  # Sleep to avoid busy waiting
        except Exception as e:
            logger.exception('Failed to send log data: %s', e)
            self.ws.close()

    def on_close(self, reason):
        # 关闭时，停止发送日志数据的Greenlet
        if self.log_sender is not None and not self.log_sender.dead:
            self.log_sender.kill()
        logger.debug('WebSocket connection closed: %s', reason)
        # 关闭日志文件
        if self.logfile is not None:
            self.logfile.close()

@app.route('/query', methods=['POST'])
# 发送信息
def conversation():
    try:
        user_input = request.json['input']
        result = get_ai_response(user_input)
        return jsonify(result=result)  # 返回一个 JSON 响应
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()  # 打印异常的堆栈跟踪
        return jsonify(error=str(e)), 500

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        logger.debug('Index endpoint was reached')
        return render_template('index.html')
    except Exception as e:
        logger.error(f'Failed to render template due to error: {e}')
        return "An error occurred", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']

        # Connect to the database
        connection = mysql.connector.connect(
            host="gz-cdb-5scrcjb5.sql.tencentcdb.com",
            user="buildsensePublic",
            password="buildsense905",
            database="sele",
            port=63432
        )

        # Create a cursor
        cursor = connection.cursor()

        # Query the database
        cursor.execute(f"SELECT * FROM users WHERE nickname = '{username}'")

        # Fetch one record
        user = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Check if the user exists
        if user:
            session['username'] = username
            return render_template('index.html')
        else:
            return 'Invalid username'
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    logger.info('启动 WebSocket 服务...')
    try:
        http_server = WebSocketServer(
            ('0.0.0.0', 5000),
            Resource([
                ('^/logs', LogSocketApp),
                ('^/.*', app)  # 处理常规的http请求
            ]),
            log=logger,  # 使用自定义的 logger
        )
        logger.info('WebSocket 服务正在运行在 0.0.0.0:5000')
        http_server.serve_forever()
    except Exception as e:
        logger.exception('无法启动 WebSocket 服务: {}'.format(e))