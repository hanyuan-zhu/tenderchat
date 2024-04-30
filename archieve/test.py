from zhipuai import ZhipuAI
def helper(issue):
    client = ZhipuAI(api_key="fa1467996b5f2018bcf1f49f1643cf43.908Q1sveABVE1WJc") 
    role_setting = '''
    你的角色是一个协助其他ai agent解决问题的agent，你需要根据对方Agent的问题和对话log，给出合理的建议。
    告诉他问题潜在的解决方案，或者提供一些思路，帮助他解决问题。
    '''
    
    messages = [{"role": "system","content": role_setting}]
    messages.append({"role": "user","content": '对方Agent遇到的问题是：' + issue + '，请问您有什么想法？'})
    # messages.append({"role": "system","content": '以下是对方和用户的对话log'})
    # messages.append(context)
    
    response = client.chat.completions.create(
        model="glm-4",
        messages=messages,
    )
    
    return response.choices[0].message.content
    
user_input = input("请输入：")

print(helper(user_input))