import random
from dashscope import Generation
import dashscope
class QwenModel:
    def __init__(self, api_key, model, tools=None, temperature=0.2, result_format='message'):
        """
        初始化 QwenModel 类，预设部分参数。
        :param api_key: Dashscope API 密钥。
        :param model_name: 使用的模型名称。
        :param tools: 工具配置。
        :param temperature: 采样温度，默认为0.2。
        :param result_format: 结果的格式，默认为'message'。
        """
        dashscope.api_key = api_key
        self.model_name = model
        self.tools = tools
        self.temperature = temperature
        self.result_format = result_format

    def call(self, messages):
        """
        生成消息，只需要传入messages参数。
        
        :param messages: 用于生成的对话消息列表。
        :return: API 调用的响应，并解析出常用属性。
        """
        seed = random.randint(1, 10000)
        raw_response = Generation.call(
            model=self.model_name,
            messages=messages,
            tools=self.tools,
            seed=seed,
            temperature=self.temperature,
            result_format=self.result_format
        )
        # 解析响应为更易访问的属性
        return self._parse_response(raw_response)
        # return raw_response

    def _parse_response(self, response):
        """
        解析API响应，设置为实例的属性。
        """
        self.status = response.status_code
        if response.output and response.output.choices:
            choice = response.output.choices[0].message
            self.tool_calls = choice.tool_calls[0] if 'tool_calls' in choice and choice.tool_calls else None
            self.function_name = self.tool_calls["function"]["name"] if self.tool_calls else None
            self.function_args = self.tool_calls["function"]["arguments"] if self.tool_calls else None
            self.message_to_append = choice
            self.role = choice.role
            self.content = choice.content
        self.total_tokens = response.usage.total_tokens if response.usage else None
        return self


