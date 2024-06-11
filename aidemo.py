# mock_ai.py

import time
from utils import logger

# 预定义的对话内容
dialogue = [
    {
        "role": "AI",
        "content": "现在新员工按通知来公司了，现在要开始办理入职手续，接下来具体做什么？"
    },
    {
        "role": "AI",
        "content": "**欢迎并引导:**\n- 请先热情欢迎新员工，自我介绍，并引导他们到指定区域开始办理入职。\n\n**核实并收集资料:**\n- 请确认新员工携带了所有需要的文件，包括身份证、学历证明、体检报告和离职证明（如适用）。\n- 准备收集这些文件的复印件或电子版。\n\n**填写表格提醒:**\n- 待文件核对后，将指导新员工填写《员工履历表》与《岗位申请表》，确保信息无误。\n\n**接下来是合同签署:**\n- 准备好劳动合同，稍后将解释合同条款并安排签署。\n\n请开始第一步并告诉我完成后的情况。"
    },
    {
        "role": "AI",
        "content": "我已经完成了员工欢迎。现在要开始收集资料。"
    }
]

# 预定义的日志内容
log_messages = [
    "AI模型已初始化",
    "正在处理用户输入",
    "生成对话内容"
]

# 用于记录日志进度的索引
log_index = 0

# 用于记录对话进度的索引
dialogue_index = 0

def get_ai_response(user_input):
    global log_index, dialogue_index

    # 生成预定义的日志信息
    if log_index < len(log_messages):
        logger.info(log_messages[log_index])
        log_message = log_messages[log_index]
        log_index += 1  # 增加日志索引以记录下一个日志信息
    else:
        log_message = "Logger: 未定义的日志信息。"

    # 简单逻辑：返回对话列表中的下一个内容
    if dialogue_index < len(dialogue):
        response = dialogue[dialogue_index]
        dialogue_index += 1
        full_response = f"{response['role']}: {response['content']}"
    else:
        full_response = "已准备的demo结束。"

    # 模拟逐字符输出并将其组合成一个字符串返回
    simulated_typing = ""
    for char in full_response:
        simulated_typing += char
        time.sleep(0.005)  # 模拟逐字符输出的延迟

    return simulated_typing