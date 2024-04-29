class AIModel:
    def __init__(self, api_key, model, temperature=0.9,tools=None):
        self.api_key = api_key
        self.model = model
        self.tools = tools
        self.temperature = temperature
        self.message = None

    def call(self, messages):
        result = self.get_result(messages)
        self.process_result(result)
        return self

    def get_result(self, messages):
        raise NotImplementedError("Subclasses must implement this method")

    def process_result(self, result):
        self.message = self.get_message(result)
        self.usage = self.get_usage(result)

    def get_message(self, result):
        raise NotImplementedError("Subclasses must implement this method")

    def get_usage(self, result):
        raise NotImplementedError("Subclasses must implement this method")


class ZhipuModel(AIModel):
    def __init__(self, api_key, model, temperature=0.9,tools=None):
        super().__init__(api_key, model, temperature,tools)
        from zhipuai import ZhipuAI
        self.client = ZhipuAI(api_key=self.api_key)

    def get_result(self, messages):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools = self.tools,
            tool_choice="auto",
            temperature=self.temperature,
        )

    def get_message(self, result):
        message = {
            'role': result.choices[0].message.role,
            'content': result.choices[0].message.content,
        }
        if result.choices[0].message.tool_calls is not None:
            message['tool_calls'] = result.choices[0].message.tool_calls
        return message
    
    def get_usage(self, result):
        return {
            "input_tokens": result.usage.prompt_tokens,
            "output_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens
        }


class QwenModel(AIModel):
    def __init__(self, api_key, model, temperature=0.9,tools=None):
        super().__init__(api_key, model, temperature, tools)
        import dashscope
        dashscope.api_key = self.api_key

    def get_result(self, messages):
        import dashscope
        import random
        return dashscope.Generation.call(
            model=self.model,
            messages=messages,
            tools=self.tools,
            seed=random.randint(1, 10000),
            temperature=self.temperature,
            result_format='message'  
        )

    def get_message(self, result):
        return result.output.choices[0].message

    def get_usage(self, result):
        return {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens
        }
        
        
