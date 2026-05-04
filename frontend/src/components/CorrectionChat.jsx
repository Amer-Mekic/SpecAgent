import { useState, useEffect, useRef } from 'react';
import { chat as chatApi } from '../api/client';

export default function CorrectionChat({ guestMode, sessionId, pinnedRequirement, onApplySuggestion }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Requirements extracted. Review the list and let me know what to change.' }
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setSending(true);
    try {
      if (guestMode) {
        await new Promise((r) => setTimeout(r, 400));
        const pin = pinnedRequirement?.req_id || pinnedRequirement?.statement?.slice(0, 40);
        const reply = pin
          ? `(Preview) Noted your note about “${pin}”. In a signed-in session the agent would revise requirements here.`
          : '(Preview) Message received. Sign in to run the real correction agent against your session.';
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
        return;
      }
      const res = await chatApi.send(sessionId, text, pinnedRequirement?.id || null);
      setMessages(prev => [...prev, { role: 'assistant', content: res.message || res.content || res }]);
      if (res.suggested_statement && onApplySuggestion) {
        setMessages(prev => [...prev, {
          role: 'system-action',
          content: res.suggested_statement,
          requirementId: pinnedRequirement?.id,
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>Correction chat</span>
        {pinnedRequirement && (
          <span className="chat-pinned-label">📌 {pinnedRequirement.req_id || 'Requirement pinned'}</span>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg msg-${msg.role}`}>
            {msg.role === 'system-action' ? (
              <div className="suggestion-bubble">
                <p className="suggestion-text">{msg.content}</p>
                <button
                  className="btn-apply"
                  onClick={() => onApplySuggestion(msg.requirementId, msg.content)}
                >
                  Apply suggestion
                </button>
              </div>
            ) : (
              <div className="msg-bubble">{msg.content}</div>
            )}
          </div>
        ))}
        {sending && (
          <div className="chat-msg msg-assistant">
            <div className="msg-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          placeholder="Type a correction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={sending}
        />
        <button className="btn-send" onClick={send} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}