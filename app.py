import os
import glob
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Assuming KnowledgeManager imports work from project root
from embedder import Embedder
from agents import Chat
from knowledge_manager import KnowledgeManager

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for the frontend

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Initialize ML models
print("Initializing Models & KnowledgeManager...")
try:
    # embedder = Embedder()
    # chat = Chat(on_cpu=True, verbose=False)
    # kb_manager = KnowledgeManager(
    #     chat=chat,
    #     embedder=embedder,
    #     collection_name='test'
    # )
    embedder = None
    chat = None
    kb_manager = None
except Exception as e:
    print(f"Error initializing models: {e}")
    kb_manager = None


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
        kb_manager.upload(file_path)
        return jsonify({"message": "Successfully uploaded file to Graph and Vector DB"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ask", methods=["POST"])
def ask_question():
    data = request.json
    question = data.get("question")
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
        
    if not kb_manager:
        return jsonify({"error": "KnowledgeManager failed to initialize"}), 500
        
    try:
        # Call the existing ask_question method (user will implement its internals later)
        answer = kb_manager.ask_question(question)
        
        # If the method is not implemented yet, it throws NotImplementedError
        return jsonify({"answer": answer}), 200
    except NotImplementedError:
        # Return a mock response for now
        return jsonify({"answer": "Error: ask_question not implemented yet. The question was received but the implementation is pending."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
