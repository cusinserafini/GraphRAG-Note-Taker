FROM python:3.11-slim
RUN pip install --no-cache-dir ipykernel
RUN pip install --no-cache-dir neo4j
RUN pip install --no-cache-dir qdrant-client
RUN pip install --no-cache-dir transformers accelerate sentence_transformers

WORKDIR /app

# Copy the connection file into the container
COPY python_sandbox/connection.json .
COPY neo4j_db.py .
COPY qdrant_db.py .
COPY embedder.py .
COPY .env .

EXPOSE 50001 50002 50003 50004 50005

# Start the kernel directly, pointing it to the connection file
CMD ["python", "-m", "ipykernel_launcher", "-f", "connection.json"]