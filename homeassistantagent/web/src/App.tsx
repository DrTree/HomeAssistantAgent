import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport, type UIMessage, isTextUIPart } from 'ai';
import { useMemo, useState, type FormEvent } from 'react';
import './App.css';

export default function App() {
  const [input, setInput] = useState('');
  const [clientError, setClientError] = useState<string | null>(null);
  const transport = useMemo(() => new DefaultChatTransport({ api: '/api/chat' }), []);
  const { messages, sendMessage, status, error } = useChat({ transport });
  const isBusy = status === 'submitted' || status === 'streaming';
  const isReady = status === 'ready';
  const formatError = (value: unknown) => {
    if (!value) {
      return null;
    }
    if (typeof value === 'string') {
      return value;
    }
    if (value instanceof Error) {
      return value.message;
    }
    try {
      return JSON.stringify(value);
    } catch {
      return 'Unexpected error.';
    }
  };
  const errorMessage = clientError ?? formatError(error);
  const isError = status === 'error' || Boolean(errorMessage);

  const renderMessageContent = (message: UIMessage) => {
    const textParts = message.parts.filter(isTextUIPart).map((part) => part.text);
    if (textParts.length > 0) {
      return textParts.join('');
    }
    return message.parts.length > 0 ? '[Unsupported message content]' : '';
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isBusy) {
      return;
    }

    const trimmedInput = input.trim();
    if (!trimmedInput) {
      return;
    }

    setClientError(null);
    try {
      await sendMessage({ text: trimmedInput });
      setInput('');
    } catch (err) {
      setClientError(formatError(err) ?? 'Failed to send message.');
    }
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

      {errorMessage ? (
        <div className="alert" role="alert">
          <strong>Connection error.</strong> {errorMessage}
        </div>
      ) : null}

      <section className="chat">
        {messages.length === 0 ? (
          <div className="chat__empty">
            <p>Start a conversation by asking your first question.</p>
          </div>
        ) : (
          messages.map((message) => (
              <div key={message.id} className={`chat__message chat__message--${message.role}`}>
                <span className="chat__role">{message.role}</span>
                <div className="chat__content">{renderMessageContent(message)}</div>
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
