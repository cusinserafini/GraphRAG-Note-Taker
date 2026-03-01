from typing import List
from llama_cpp import Llama
from .data_types import MessageFormat

class Chat:
    def __init__(self, on_cpu:bool = False, verbose:bool = False, n_ctx:int = 8192):
        # getting the model from HF
        self.llm = Llama.from_pretrained(
            repo_id = "google/gemma-3-4b-it-qat-q4_0-gguf",
            filename = "gemma-3-4b-it-q4_0.gguf",
            n_gpu_layers = 0 if on_cpu else -1, # -1 offloads ALL layers to the GPU (MPS)
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

    def ask(self, messages:List[MessageFormat], streaming:bool = False, max_new_tokens:bool = 1024):
        """
        If streaming is True, an iterator is returned
        """
        if streaming:
            return self.llm.create_chat_completion(
                messages = messages, 
                max_tokens = max_new_tokens,
                stream = streaming,
            )
        else:
            output = self.llm.create_chat_completion(
                messages = messages, 
                max_tokens = max_new_tokens,
                stream = streaming,
            )
            return output['choices'][0]['message']['content']


        