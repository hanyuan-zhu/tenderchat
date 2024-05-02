# utils.py
import mysql.connector
from config import api_key_qwen
import logging
import dashscope
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

dashscope.api_key=api_key_qwen


logger = logging.getLogger('websocket_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('app.log', encoding='utf-8', delay=False)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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


def clean_create_statement(create_statement):
    # Split the statement into lines
    lines = create_statement.split('\n')
    # Filter out unwanted lines and text within lines
    clean_lines = []
    for line in lines:
        if 'CREATE TABLE' in line:
            clean_lines.append(line)
        elif 'PRIMARY KEY' in line or 'FOREIGN KEY' in line:
            clean_lines.append(line.strip().rstrip(','))
        elif '`' in line:  # This ensures only column lines are included
            # Remove text after the data type
            parts = line.split()
            clean_line = ' '.join(parts[:2])
            if 'DEFAULT' in line:
                default_part = ' '.join(parts[parts.index('DEFAULT'):])
                clean_line += ' ' + default_part.split(',')[0]
            clean_lines.append(clean_line.strip().rstrip(','))
    # Reassemble the cleaned lines
    return '\n'.join(clean_lines) + '\n)'


def table_info(keywords):
    
    # 初始化 DashScope 嵌入模型
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v1", dashscope_api_key="sk-cbcc1fb859b1456885a270eecbec6369"
        )

    # Set up the Chroma database with the embedding function
    db3 = Chroma(persist_directory="vector_store", embedding_function=embeddings)
    
    connection = mysql.connector.connect(
    host="gz-cdb-5scrcjb5.sql.tencentcdb.com",
    user="db",
    password="dbdb905905",
    database="sele",
    port=63432
    )
    cursor = connection.cursor()
    # Initialize sets to store unique table names and field names
    table_names = set()
    field_names = {}
    full_output = ""  # Initialize the string to accumulate outputs

    # Iterate over each query in the input list
    for query in keywords:
        # Perform the similarity search
        results = db3.similarity_search(query, k=3)
        
        # Process results to extract table and field names
        for result in results:
            metadata = result.metadata
            if metadata["field_name"]:  # Skip if there's no field name (avoids table summaries)
                table_name = metadata["table_name"]
                field_name = metadata["field_name"]
                # print(f"{table_name}.{field_name}")  # Display table and field name
                table_names.add(table_name)
                if table_name not in field_names:
                    field_names[table_name] = []
                field_names[table_name].append(field_name)
    
    # Output the cleaned creation content of each table
    for table in table_names:
        cursor.execute(f"SHOW CREATE TABLE {table}")
        create_info = cursor.fetchone()
        clean_create_output = clean_create_statement(create_info[1])
        full_output += f"Creation info for {table}:\n{clean_create_output}\n"
    
    # Display sample contents from each table for the fields found
    for table, fields in field_names.items():
        field_list = ", ".join(fields)  # Combine field names into a comma-separated string
        cursor.execute(f"SELECT {field_list} FROM {table} LIMIT 3")
        sample_contents = cursor.fetchall()
        full_output += f"Sample contents from {table} ({field_list}): {sample_contents}\n"

    return full_output