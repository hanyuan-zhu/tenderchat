# app.py
# Standard library imports
import gevent
from gevent import Greenlet
from geventwebsocket import WebSocketApplication
import mysql.connector
# Third party imports
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
# Local application imports
# from ai import get_ai_response
from aidemo import get_ai_response
from config import app_secret_key,database_config
from utils import logger

app = Flask(__name__)
app.debug = True
app.secret_key = app_secret_key

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
        connection = mysql.connector.connect(**database_config)

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