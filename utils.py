# utils.py
import mysql.connector
from config import database_config
import logging
import re

logger = logging.getLogger('websocket_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('app.log', encoding='utf-8', delay=False)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def table_details(tables:list):
    """
    输入表名列表:["table1","table2"]
    返回每张表的结构（列名、数据类型、完整性约束等）及前几行数据作为示例
    """
    connection = mysql.connector.connect(**database_config)
    logger.info('已连接到标讯数据库')
    cursor = connection.cursor()
    
    # 定义查询表结构和前几行数据的SQL模板
    schema_query_template = "SHOW CREATE TABLE {};"
    sample_data_query_template = "SELECT * FROM {} LIMIT 3;"
    
    table_details_list = []
    
    for table in tables:
        try:
            # 查询表结构（使用SHOW CREATE TABLE）
            cursor.execute(schema_query_template.format(table))
            schema_result = cursor.fetchone()  # SHOW CREATE TABLE 只返回一行数据
            
            # 从查询结果中提取表结构SQL语句
            create_table_sql = schema_result[1]  # 第一列是表名，第二列是创建表的SQL语句
            
            # 查询表的前几行数据
            cursor.execute(sample_data_query_template.format(table))
            sample_data_result = cursor.fetchall()
            
            # 处理结果
            # 注意：此处直接使用SHOW CREATE TABLE的结果，不再分解为列名和数据类型列表，
            # 因为完整的创建语句已经包含了这些信息，且可能更复杂（如外键定义等）
            table_info = {
                "table_name": table,
                "create_table_statement": create_table_sql,
                "sample_data": sample_data_result
            }
            table_details_list.append(table_info)
            
        except mysql.connector.Error as err:
            logger.error(f"查询表'{table}'时发生错误: {err}")
            continue
        
    # 关闭游标和连接
    cursor.close()
    connection.close()
    
    logger.info('成功获取表详情并关闭数据库连接')
    return table_details_list
def execute_sql_query(sql_query:str):
    """
    执行SQL查询并返回结果
    """
    connection = mysql.connector.connect(**database_config)
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

def clean_sql_query(query):
    """
    清除和修正SQL查询中的符号和字符问题
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