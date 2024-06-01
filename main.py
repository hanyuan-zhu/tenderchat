# main.py
from gevent import monkey
monkey.patch_all()

from geventwebsocket import WebSocketServer, Resource
from app import app, LogSocketApp
from utils import logger


if __name__ == "__main__":
    logger.info('启动 WebSocket 服务...')
    try:
        http_server = WebSocketServer(
            ('0.0.0.0', 5001),
            Resource([
                ('^/logs', LogSocketApp),
                ('^/.*', app)  # 处理常规的http请求
            ]),
            log=logger,  # 使用自定义的 logger
        )
        print('WebSocket 服务正在运行在 0.0.0.0:5001')
        logger.info('WebSocket 服务正在运行在 0.0.0.0:5001')
        http_server.serve_forever()
    except Exception as e:
        logger.exception('无法启动 WebSocket 服务: {}'.format(e))