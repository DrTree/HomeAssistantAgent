import { useChat } from '@ai-sdk/react';
import type { FormEvent } from 'react';
import './App.css';

export default function App() {
  const { messages, input, setInput, append, isLoading, error } = useChat({
    api: '/api/chat',
  });
  const isBusy = isLoading;
  const isReady = !isLoading && !error;
  const isError = Boolean(error);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isBusy) {
      return;
    }

    const trimmedInput = input.trim();
    if (!trimmedInput) {
      return;
    }

    await append({ role: 'user', content: trimmedInput });
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
              <div className="chat__content">{message.content}</div>
            </div>
          ))
        )}
      </section>

      <form className="composer" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
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
