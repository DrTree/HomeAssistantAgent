import { useChat } from '@ai-sdk/react';
import './App.css';

export default function App() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>HomeAssistantAgent</h1>
          <p>Ask questions about Home Assistant and get concise guidance.</p>
        </div>
        <span className={isLoading ? 'status status--active' : 'status'}>
          {isLoading ? 'Thinking…' : 'Ready'}
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
              <div className="chat__content">{message.content}</div>
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
        />
        <button type="submit" disabled={!input.trim() || isLoading}>
          Send
        </button>
      </form>
    </div>
  );
}
