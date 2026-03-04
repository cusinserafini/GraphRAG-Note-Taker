from agents import Chat
from python_sandbox.python_sandbox import PythonSandbox
from agents.AgenticSearch import AgenticSearch

import logging

logging.getLogger("qdrant_client").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("neo4j").setLevel(logging.ERROR)

chat = Chat(on_cpu=False, verbose=False, n_ctx=8192)

agent = AgenticSearch(chat=chat)
sandbox = PythonSandbox(connection_file="python_sandbox/connection.json")
query = "Explain how Alan Turing, ARPANET, CERN, NASA, and the Apollo program collectively shaped modern technological infrastructure."

print(f"> QUERY: {query}")
iterations = 0

while True:
    output, code = agent(text=query)
    query = None
    if not code:
        continue
    code_output, error = sandbox.execute_code(code[0])
    agent.append_code_output(code_output)
    print(f"CODE:\n{code[0]}")
    print(f"CODE OUTPUT\n{code_output}")
    
    if "end_interactive_shell()" in code[0]:
        break
    iterations += 1

    if iterations > 10:
        break

output, _ = agent("Now that you have finished your reasoning, give the answer in plain text without Python code and without the thinking part.")
print("FINAL ANSWER:")
print(output)
sandbox.clear_context()
sandbox.close()
