from agents import Chat
from embedder import Embedder
from python_sandbox.python_sandbox import PythonSandbox
from agents.AgenticSearch import AgenticSearch

embedder = Embedder()
chat = Chat(on_cpu=False, verbose=False, n_ctx=8192)

agent = AgenticSearch(chat=chat)
sandbox = PythonSandbox(connection_file="./python_sandbox/connection.json")
sandbox.clear_context()

query = "Who is the husband of the Elisabetta qween?"

print(f"> QUERY: {query}")
output, code = agent(text=query)

iterations = 0

while True:
    code_output = sandbox.execute_code(code)
    agent.append_code_output(code_output)
    print(f"CODE:\n{code[0]}")
    print(f"CODE OUTPUT\n{code_output}")
    
    if "end_interactive_shell()" in code:
        break
    iterations += 1

    if iterations > 20:
        break

sandbox.clear_context()
sandbox.close()