import React, { useEffect, useRef, useState } from 'react';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Loader2, Sparkles, Send, Trash2, User, Bot } from 'lucide-react';

const SUGGESTIONS = [
  'Which jobs match my resume best?',
  'What are my skill gaps?',
  'How do I fix my missing skills?',
  'Create a learning plan',
  'Write a cover letter',
  'Prepare interview questions',
];

export function AssistantPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await apiService.assistant.history();
        setMessages(response.data.results || response.data || []);
      } catch (e) {
        console.error('Failed to load chat history:', e);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || sending) return;
    setInput('');
    setError('');
    setSending(true);
    // Optimistic echo so the question appears immediately.
    const tempId = `tmp-${Date.now()}`;
    setMessages(prev => [...prev, { id: tempId, role: 'user', content: message, created_at: new Date().toISOString() }]);
    try {
      const response = await apiService.assistant.send(message);
      setMessages(prev => [...prev.filter(m => m.id !== tempId), response.data.user_message, response.data.reply]);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not reach the assistant.');
      setMessages(prev => prev.filter(m => m.id !== tempId));
    } finally {
      setSending(false);
    }
  };

  const clearHistory = async () => {
    try {
      await apiService.assistant.clear();
      setMessages([]);
    } catch (e) {
      setError('Could not clear the conversation.');
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  if (loading) {
    return <div className="page-loading"><Loader2 size={32} className="spin" /></div>;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>AI Career Assistant</h1>
          <p>Ask about your resume, job fit, skill gaps, cover letters and interview prep.</p>
        </div>
        {messages.length > 0 && (
          <button className="btn btn-secondary" onClick={clearHistory}>
            <Trash2 size={18} /> Clear chat
          </button>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="chat-card">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <Sparkles size={40} />
              <h3>Hi {(user?.name || 'there').split(' ')[0]}, what would you like to work on?</h3>
              <p>Every answer is grounded in your uploaded resume, so nothing gets invented.</p>
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chat-suggestion" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.role}`}>
              <div className="chat-avatar">{m.role === 'user' ? <User size={16} /> : <Bot size={16} />}</div>
              <div className="chat-bubble-body">
                <span className="chat-role">{m.role === 'user' ? 'You' : 'Assistant'}</span>
                <div className="chat-text">{m.content}</div>
              </div>
            </div>
          ))}
          {sending && (
            <div className="chat-bubble assistant">
              <div className="chat-avatar"><Bot size={16} /></div>
              <div className="chat-bubble-body">
                <span className="chat-role">Assistant</span>
                <div className="chat-text text-muted"><Loader2 size={16} className="spin" /> Thinking...</div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-row">
          <textarea
            className="chat-input"
            rows={1}
            placeholder="Ask about your resume, a job, or interview prep..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="btn btn-primary" onClick={() => send()} disabled={sending || !input.trim()}>
            {sending ? <Loader2 size={18} className="spin" /> : <Send size={18} />} Send
          </button>
        </div>
      </div>
    </div>
  );
}