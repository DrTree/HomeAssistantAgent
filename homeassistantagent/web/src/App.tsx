import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport, type UIMessage, isTextUIPart, isToolUIPart } from 'ai';
import { useMemo, useState, type FormEvent } from 'react';
import './App.css';

export default function App() {
  const [input, setInput] = useState('');
  const transport = useMemo(() => new DefaultChatTransport({ api: '/api/chat' }), []);
  const { messages, sendMessage, status, error, addToolApprovalResponse } = useChat({
    transport,
  });
  const isBusy = status === 'submitted' || status === 'streaming';
  const isReady = status === 'ready';
  const isError = status === 'error' || Boolean(error);

  const renderToolPart = (part: UIMessage['parts'][number]) => {
    if (!isToolUIPart(part)) {
      return null;
    }

    if (part.type !== 'tool-calculator') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Tool request</p>
          <p>Unsupported tool request.</p>
        </div>
      );
    }

    const input = part.input as { number_a?: number; number_b?: number; operator?: string };

    if (part.state === 'approval-requested') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator approval requested</p>
          <p className="chat__tool-details">
            {input.number_a} {input.operator} {input.number_b}
          </p>
          <div className="chat__tool-actions">
            <button
              type="button"
              className="chat__tool-button"
              onClick={() =>
                addToolApprovalResponse({
                  id: part.approval.id,
                  approved: true,
                })
              }
            >
              Approve
            </button>
            <button
              type="button"
              className="chat__tool-button chat__tool-button--deny"
              onClick={() =>
                addToolApprovalResponse({
                  id: part.approval.id,
                  approved: false,
                })
              }
            >
              Deny
            </button>
          </div>
        </div>
      );
    }

    if (part.state === 'approval-responded' && part.approval.approved === false) {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator request denied</p>
          <p className="chat__tool-details">
            {input.number_a} {input.operator} {input.number_b}
          </p>
        </div>
      );
    }

    if (part.state === 'output-available') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator result</p>
          <p className="chat__tool-details">
            {input.number_a} {input.operator} {input.number_b} = {part.output as number}
          </p>
        </div>
      );
    }

    return (
      <div key={part.toolCallId} className="chat__tool">
        <p className="chat__tool-title">Calculator pending</p>
      </div>
    );
  };

  const renderMessageContent = (message: UIMessage) => {
    if (message.parts.length === 0) {
      return '';
    }

    return message.parts.map((part, index) => {
      if (isTextUIPart(part)) {
        return (
          <p key={`${message.id}-text-${index}`} className="chat__text">
            {part.text}
          </p>
        );
      }
      if (isToolUIPart(part)) {
        return renderToolPart(part);
      }
      return (
        <p key={`${message.id}-unsupported-${index}`} className="chat__unsupported">
          [Unsupported message content]
        </p>
      );
    });
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

    await sendMessage({ text: trimmedInput });
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
