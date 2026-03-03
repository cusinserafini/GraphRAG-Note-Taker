from typing import List
from llama_cpp import Llama
from .data_types import MessageFormat

class Chat:
    def __init__(self, on_cpu:bool = False, verbose:bool = False, n_ctx:int = 4096):
        # getting the model from HF
        self.llm = Llama.from_pretrained(
            # repo_id = "google/gemma-3-4b-it-qat-q4_0-gguf",
            # filename = "gemma-3-4b-it-q4_0.gguf",
            repo_id="unsloth/Qwen3-14B-GGUF",
            filename="Qwen3-14B-Q4_K_M.gguf",
            n_gpu_layers = 0 if on_cpu else -1, # -1 offloads ALL layers to the GPU
            verbose = verbose,
            n_ctx=n_ctx,
        )

    def get_cache(self):
        return self.llm.save_state()

    def set_cache(self, cache):
        # TODO: check the cache type and add it into the params definition
        return self.llm.load_state(cache)

    def get_message_format(self, role:str, content:str):
        # used to unify the way in which the messages are created
        # (if you need to change the format, you just need to modify this function and not the entire code)
        return MessageFormat(role=role, content=content)
    
    def _strip_thinking(self, text: str) -> str:
        if "<think>" in text and "</think>" in text:
            return text.split("</think>", 1)[1].strip()
        return text.strip()

    def _stream_without_thinking(self, stream):
        buffer = ""
        thinking = False

        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            token = delta.get("content", "")

            if not token:
                continue

            buffer += token

            if "<think>" in buffer:
                thinking = True

            if "</think>" in buffer:
                thinking = False
                buffer = buffer.split("</think>", 1)[1]

                if buffer.strip():
                    yield {
                        "choices": [
                            {"delta": {"content": buffer}}
                        ]
                    }
                buffer = ""
                continue

            if not thinking:
                yield {
                    "choices": [
                        {"delta": {"content": token}}
                    ]
                }

    def ask(self, messages:List[MessageFormat], streaming:bool = False, max_new_tokens:bool = 1024):
        """
        If streaming is True, an iterator is returned
        """
        if not streaming:
            output = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_new_tokens,
                stream=streaming,
            )

            content = output['choices'][0]['message']['content']
            return self._strip_thinking(content)
        
        stream = self.llm.create_chat_completion(
            messages = messages, 
            max_tokens = max_new_tokens,
            stream = streaming,
        )
        return self._stream_without_thinking(stream)