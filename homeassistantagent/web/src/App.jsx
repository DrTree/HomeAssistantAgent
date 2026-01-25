import { useChat } from '@ai-sdk/react';
import { useState } from 'react';
import './App.css';

export default function App() {
  const { messages, status, error, sendMessage } = useChat();
  const [input, setInput] = useState('');

  const isBusy = status === 'submitted' || status === 'streaming';
  const isReady = status === 'ready' && !error;
  const isError = Boolean(error);

  const handleInputChange = (event) => {
    setInput(event.target.value);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isBusy) {
      return;
    }
    sendMessage(trimmed);
    setInput('');
  };

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>HomeAssistantAgent</h1>
          <p>Ask questions about Home Assistant and get concise guidance.</p>
        </div>
        <span
          className={`status${isReady ? '' : ' status--active'}${isError ? ' status--error' : ''}`}
        >
          {isReady ? 'Ready' : isError ? 'Offline' : 'Thinking…'}
        </span>
      </header>

      <section className="chat">
        {messages.length === 0 ? (
          <div className="chat__empty">
            <p>Start a conversation by asking your first question.</p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`chat__message chat__message--${message.role}`}>
              <span className="chat__role">{message.role}</span>
              <div className="chat__content">
                {message.parts.map((part, index) =>
                  part.type === 'text' ? <span key={index}>{part.text}</span> : null,
                )}
              </div>
            </div>
          ))
        )}
      </section>

      <form className="composer" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask about automations, sensors, or setup tips…"
          aria-label="Message"
          disabled={isBusy}
        />
        <button type="submit" disabled={!input.trim() || isBusy}>
          Send
        </button>
      </form>
    </div>
  );
}
