import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';

const SAMPLE_QUESTIONS = [
  'Who spends the most?',
  'How much was spent on travel this month?',
  'Show me unusual transactions.',
  'What is the biggest expense category?',
  'Predict next month\'s expenses.',
  'Who owes the most money?',
  'Which day of the week has highest spending?',
];

const MessageBubble = ({ role, content, confidence, intent }) => {
  const isUser = role === 'user';
  return (
    <div className={`chat-bubble-wrapper ${isUser ? 'user' : 'assistant'}`}>
      <div className="chat-avatar">{isUser ? '👤' : '🤖'}</div>
      <div className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
        <div className="bubble-content">{content}</div>
        {!isUser && (confidence != null || intent) && (
          <div className="bubble-meta">
            {intent && <span className="bubble-intent">Intent: {intent}</span>}
            {confidence != null && (
              <span className="bubble-confidence">
                Confidence: {Math.round(confidence * 100)}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const ConversationalAI = () => {
  const { jobId } = useParams();
  const [messages,    setMessages]    = useState([]);
  const [input,       setInput]       = useState('');
  const [loading,     setLoading]     = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [wsStatus,    setWsStatus]    = useState('idle'); // idle | connected | error
  const bottomRef = useRef(null);
  const wsRef     = useRef(null);

  /* ── Load conversation history ── */
  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get(`/analyze/${jobId}/conversation`);
        if (data.length) {
          setMessages(data.map(m => ({ role: m.role, content: m.content })));
        } else {
          setMessages([{
            role: 'assistant',
            content: `Hi! I'm your AI expense analyst for this dataset. Ask me anything about your spending patterns, anomalies, or forecasts. You can also say "summarize this dataset" for an instant overview.`,
          }]);
        }
      } catch {
        setMessages([{
          role: 'assistant',
          content: 'Hello! Ask me anything about your expense data.',
        }]);
      }
      setHistoryLoaded(true);
    };
    load();
  }, [jobId]);

  /* ── Scroll to bottom ── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ── Send via REST (WebSocket optional) ── */
  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    const question = text.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const history = messages.slice(-10).map(m => ({ role: m.role, content: m.content }));
      const { data } = await api.post(`/analyze/${jobId}/ask`, {
        question,
        conversation_history: history,
      });

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || 'I was unable to answer that question.',
        confidence: data.confidence,
        intent: data.intent,
      }]);
    } catch (e) {
      const errMsg = e.response?.data?.detail || 'Something went wrong. Please try again.';
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ ${errMsg}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="chat-page">
      {/* Header */}
      <div className="chat-header">
        <Link to={`/intelligence/${jobId}`} className="btn-back">← Intelligence</Link>
        <div className="chat-header-center">
          <span className="chat-ai-icon">🤖</span>
          <div>
            <h1 className="chat-title">AI Expense Assistant</h1>
            <p className="chat-subtitle">Conversational analytics for job <code>{jobId?.slice(0, 8)}…</code></p>
          </div>
        </div>
        <div className="chat-header-right">
          <span className="chat-status-dot" />
          <span className="chat-status-text">Online</span>
        </div>
      </div>

      {/* Sample questions */}
      {historyLoaded && messages.length <= 1 && (
        <div className="sample-questions">
          <p className="sample-label">Try asking:</p>
          <div className="sample-chips">
            {SAMPLE_QUESTIONS.map((q, i) => (
              <button key={i} className="sample-chip" onClick={() => sendMessage(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <MessageBubble key={i} {...msg} />
        ))}
        {loading && (
          <div className="chat-bubble-wrapper assistant">
            <div className="chat-avatar">🤖</div>
            <div className="chat-bubble bubble-ai typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your expense data…"
          rows={1}
          disabled={loading}
        />
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  );
};

export default ConversationalAI;
