from .chat import Chat

class Agent:
    def __init__(self, chat:Chat, system_prompt:str):
        self.chat = chat
        self.system_prompt = system_prompt
        self.system_prompt_cache = self._get_sys_prompt_cache()

    def __call__(self):
        """
        To implement for each agent
        """
        raise NotImplementedError(f"Method call of {self} is not implemented")
    
    def _get_sys_prompt_cache(self):
        messages = [
            self.chat.get_message_format(role="system", content=self.system_prompt),
            self.chat.get_message_format(role="user", content="")
        ]

        self.chat.ask(messages=messages, max_new_tokens=1)
        cache = self.chat.get_cache()
        return cache

    def set_agent_from_scratch(self):
        """
        Restores the state of the llm to the initial cache with the system prompt
        """
        self.chat.set_cache(self.system_prompt_cache)

    def execute_basic_call(self, content:str, streaming:bool = False):
        """
        Calls the agent using the message list composed by system prompt and user request
        """
        self.set_agent_from_scratch()
        messages = [
            self.chat.get_message_format(role="system", content=self.system_prompt),
            # For GEMMA: conversation roles must alternate
            # self.chat.get_message_format(role="user", content=f"{content}. Return ONLY the output. Do not explain. Do not reason. Do not add commentary."),
            # For QWEN
            self.chat.get_message_format(role="user", content=content),
            self.chat.get_message_format(role="user", content="Return ONLY the output. Do not explain. Do not reason. Do not add commentary.")
        ]
        return self.chat.ask(messages, streaming=streaming)
