FROM python:3.10-slim

WORKDIR /app

# Install build dependencies that might be needed for native extensions like llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

ENV FLASK_APP=app.py
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001", "--debug"]
