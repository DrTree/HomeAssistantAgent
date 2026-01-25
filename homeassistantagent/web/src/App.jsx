import { useState } from 'react';
import { useChat } from '@ai-sdk/react';
import './App.css';

export default function App() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status } = useChat({
    api: '/api/chat',
  });

  const isReady = status === 'ready';

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>HomeAssistantAgent</h1>
          <p>Ask questions about Home Assistant and get concise guidance.</p>
        </div>
        <span className={isReady ? 'status' : 'status status--active'}>
          {isReady ? 'Ready' : 'Thinking…'}
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

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          if (!input.trim() || !isReady) {
            return;
          }
          sendMessage({ text: input });
          setInput('');
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about automations, sensors, or setup tips…"
          aria-label="Message"
          disabled={!isReady}
        />
        <button type="submit" disabled={!input.trim() || !isReady}>
          Send
        </button>
      </form>
    </div>
  );
}
