from flask import Response
import os
import glob
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Assuming KnowledgeManager imports work from project root
from app_kb_initializer import kb_manager

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for the frontend

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@app.route("/")
def index():
    return jsonify({"status": "Backend is running!"}), 200

@app.route("/api/files", methods=["GET"])
def list_files():
    try:
        # Get all markdown files in the data directory
        files = [os.path.basename(f) for f in glob.glob(os.path.join(DATA_DIR, "*.md"))]
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/<filename>", methods=["GET"])
def get_file(filename):
    file_path = os.path.join(DATA_DIR, secure_filename(filename))
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return jsonify({"content": content}), 200

@app.route("/api/files", methods=["POST"])
def create_file():
    data = request.json
    filename = secure_filename(data.get("filename", "Untitled.md"))
    if not filename.endswith(".md"):
        filename += ".md"
        
    content = data.get("content", "")
    
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        return jsonify({"error": "File already exists"}), 400
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return jsonify({"message": "File created", "filename": filename}), 201

@app.route("/api/files/<filename>", methods=["PUT"])
def update_file(filename):
    data = request.json
    content = data.get("content", "")
    
    file_path = os.path.join(DATA_DIR, secure_filename(filename))
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return jsonify({"message": "File updated"}), 200

@app.route("/api/upload", methods=["POST"])
def upload_to_graph():
    data = request.json
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    file_path = os.path.join(DATA_DIR, secure_filename(filename))
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    if not kb_manager:
        return jsonify({"error": "KnowledgeManager failed to initialize"}), 500

    try:
        # The upload method takes the full file path to process and chunk it
        print(f"Uploading {file_path}")
        kb_manager.upload(file_path)
        return jsonify({"message": "Successfully uploaded file to Graph and Vector DB"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ask", methods=["POST"])
def ask_question():
    data = request.json
    question = data.get("question")
    research_type = data.get("type", "RAG") # Retrieve the research type, default to RAG

    if not question:
        return jsonify({"error": "Question is required"}), 400
        
    if not kb_manager:
        return jsonify({"error": "KnowledgeManager failed to initialize"}), 500
    
    try:
        # Route depending on the research type
        if research_type == "RAG":
            # Call the existing ask_question method which returns a generator of tokens
            generator = kb_manager.ask_question(question, research_type)
        elif research_type == "Graph":
            generator = kb_manager.ask_question(question, research_type)
        elif research_type == "Agentic":
            generator = kb_manager.ask_question(question, research_type)
        else:
             return jsonify({"error": "Unknown research type"}), 400
        
        def stream_response():
            try:
                for token in generator:
                    # Keep it simple for the frontend to parse
                    delta = token["choices"][0]["delta"]
                    if "content" in delta:
                        yield f"data: {delta['content']}\n\n"
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                
        return Response(stream_response(), mimetype='text/event-stream')
    except NotImplementedError:
        return jsonify({"error": "ask_question not implemented yet."}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
