from jupyter_client import BlockingKernelClient

# Connect directly to the ports exposed by Docker Compose
print("Connecting to the Compose sandbox...")
kc = BlockingKernelClient(connection_file='connection.json')
kc.load_connection_file()
kc.start_channels()
kc.wait_for_ready(timeout=10)
print("Connected! Ready to send LLM code.")

kc.execute("x = 'Hello from inside the Docker sandbox!'\nprint(x)")

print("Cleaning up...")
kc.stop_channels()