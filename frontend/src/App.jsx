import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import {
  FileText, Plus, Upload, MessageSquare,
  PanelRightClose, PanelRightOpen, Save, Loader2, Trash2
} from 'lucide-react';
import './index.css';

// Using the same port mapped in docker-compose or local run
const API_URL = 'http://localhost:5001/api';

function App() {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [content, setContent] = useState('');

  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [researchType, setResearchType] = useState('RAG'); // Added research type state
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const saveTimeout = useRef(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${API_URL}/files`);
      setFiles(res.data.files || []);
      if (!activeFile && res.data.files?.length > 0) {
        loadFile(res.data.files[0]);
      }
    } catch (err) {
      console.error("Failed to fetch files", err);
    }
  };

  const loadFile = async (filename) => {
    try {
      const res = await axios.get(`${API_URL}/files/${filename}`);
      setActiveFile(filename);
      setContent(res.data.content || '');
    } catch (err) {
      console.error("Failed to load file", err);
    }
  };

  const createNewFile = async () => {
    const filename = prompt("Enter new file name (e.g., notebook.md):");
    if (!filename) return;

    try {
      await axios.post(`${API_URL}/files`, { filename, content: '# New Note\n\n' });
      await fetchFiles();
      loadFile(filename.endsWith('.md') ? filename : filename + '.md');
    } catch (err) {
      alert("Failed to create file: " + (err.response?.data?.error || err.message));
    }
  };

  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setContent(newContent);

    // Auto-save logic
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(() => {
      saveFile(activeFile, newContent);
    }, 1000);
  };

  const saveFile = async (filename, fileContent) => {
    if (!filename) return;
    setIsSaving(true);
    try {
      await axios.put(`${API_URL}/files/${filename}`, { content: fileContent });
    } catch (err) {
      console.error("Failed to save file", err);
    } finally {
      setIsSaving(false);
    }
  };

  const uploadToGraph = async () => {
    if (!activeFile) return;
    setIsUploading(true);
    try {
      await saveFile(activeFile, content); // save before upload
      const res = await axios.post(`${API_URL}/upload`, { filename: activeFile });
      alert(res.data.message || "Uploaded successfully!");
    } catch (err) {
      alert("Failed to upload: " + (err.response?.data?.error || err.message));
    } finally {
      setIsUploading(false);
    }
  };

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsAsking(true);

    // Initial empty bot message we will update character by character
    setChatMessages((prev) => [...prev, { role: 'bot', content: '' }]);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: userMsg.content, type: researchType }), // Passed research type
      });

      if (!response.body) {
        throw new Error('ReadableStream not yet supported in this browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let done = false;
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const messages = chunk.split('\n\n');
          for (let msg of messages) {
            msg = msg.trim();
            if (msg.startsWith('data: ')) {
              const data = msg.slice(6); // remove "data: "
              if (data === '[DONE]') {
                done = true;
              } else if (data.startsWith('[ERROR]')) {
                setChatMessages((prev) => {
                  const next = [...prev];
                  const lastIndex = next.length - 1;
                  next[lastIndex] = {
                    ...next[lastIndex],
                    content: next[lastIndex].content + "\n\nError: " + data.slice(7)
                  };
                  return next;
                });
                done = true;
              } else {
                setChatMessages((prev) => {
                  const next = [...prev];
                  const lastIndex = next.length - 1;
                  next[lastIndex] = {
                    ...next[lastIndex],
                    content: next[lastIndex].content + data
                  };
                  return next;
                });
              }
            }
          }
        }
      }

    } catch (err) {
      setChatMessages((prev) => {
        const next = [...prev];
        const lastIndex = next.length - 1;
        next[lastIndex] = {
          ...next[lastIndex],
          content: "Error: " + err.message
        };
        return next;
      });
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Area */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-title">Obsidian Graph</h2>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn" onClick={createNewFile}>
              <Plus size={16} /> New File
            </button>
          </div>
        </div>

        <div className="files-list">
          {files.map(file => (
            <div
              key={file}
              className={`file-item ${activeFile === file ? 'active' : ''}`}
              onClick={() => loadFile(file)}
            >
              <FileText size={16} />
              {file}
            </div>
          ))}
          {files.length === 0 && (
            <div style={{ padding: '16px', color: 'var(--text-secondary)', fontSize: 14 }}>
              No files found. Create one to get started.
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-area">
        <div className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontWeight: 500 }}>{activeFile || 'No file selected'}</span>
            {isSaving && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}><Loader2 size={12} className="lucide-spin" style={{ display: 'inline', animation: 'spin 2s linear infinite' }} /> Saving...</span>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button className="btn" onClick={uploadToGraph} disabled={!activeFile || isUploading}>
              {isUploading ? <Loader2 size={16} className="lucide-spin" /> : <Upload size={16} />}
              Upload to Graph DB
            </button>
            <button className="btn icon-btn" onClick={() => setIsChatOpen(!isChatOpen)}>
              {isChatOpen ? <PanelRightClose size={20} /> : <PanelRightOpen size={20} />}
            </button>
          </div>
        </div>

        {activeFile ? (
          <div className="editor-container">
            <div className="pane editor-pane">
              <textarea
                className="markdown-input"
                value={content}
                onChange={handleContentChange}
                placeholder="Start typing your markdown here..."
              />
            </div>
            <div className="pane preview-pane">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            <div style={{ textAlign: 'center' }}>
              <FileText size={48} style={{ opacity: 0.5, marginBottom: 16 }} />
              <h3>No File Open</h3>
              <p>Select a file from the sidebar or create a new one.</p>
            </div>
          </div>
        )}
      </div>

      {/* Chat / LLM Panel */}
      <div className={`chat-panel ${!isChatOpen ? 'closed' : ''}`}>
        <div className="chat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <MessageSquare size={16} style={{ display: 'inline', marginRight: '6px' }} /> Knowledge Assistant
          </div>
          <button
            className="btn icon-btn"
            title="Clear Chat"
            onClick={() => setChatMessages([])}
            disabled={isAsking || chatMessages.length === 0}
            style={{ padding: '4px' }}
          >
            <Trash2 size={16} />
          </button>
        </div>

        <div className="chat-history">
          {chatMessages.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: 40, fontSize: 13 }}>
              Ask a question about your uploaded knowledge graph!
            </div>
          )}
          {chatMessages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              {msg.role === 'bot' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          ))}
          {isAsking && (
            <div className="chat-message bot">
              <Loader2 size={16} style={{ animation: 'spin 2s linear infinite' }} />
            </div>
          )}
        </div>

        <form className="chat-input-area" onSubmit={askQuestion}>
          <div style={{ display: 'flex', width: '100%', marginBottom: '8px' }}>
            <select
              value={researchType}
              onChange={e => setResearchType(e.target.value)}
              className="chat-input"
              style={{ width: 'auto', flexGrow: 0, marginRight: '8px', padding: '6px 12px' }}
              disabled={isAsking}
            >
              <option value="RAG">RAG</option>
              <option value="Graph">Graph</option>
              <option value="Agentic">Agentic</option>
            </select>
            <input
              type="text"
              className="chat-input"
              style={{ flexGrow: 1 }}
              placeholder="Ask something..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              disabled={isAsking}
            />
          </div>
          <button type="submit" className="btn primary" disabled={isAsking || !chatInput.trim()} style={{ width: '100%' }}>
            Send
          </button>
        </form>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}} />
    </div>
  );
}

export default App;
