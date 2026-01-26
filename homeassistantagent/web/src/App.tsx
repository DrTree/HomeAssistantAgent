import { useChat } from '@ai-sdk/react';
import {
  DefaultChatTransport,
  type UIMessage,
  isTextUIPart,
  isToolUIPart,
  lastAssistantMessageIsCompleteWithToolCalls,
} from 'ai';
import { useMemo, useState, type FormEvent } from 'react';
import './App.css';

export default function App() {
  const [input, setInput] = useState('');
  const transport = useMemo(() => new DefaultChatTransport({ api: '/api/chat' }), []);
  const { messages, sendMessage, status, error, addToolOutput } = useChat({
    transport,
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,
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

    const parsedInput = (() => {
      if (typeof part.input === 'string') {
        try {
          return JSON.parse(part.input) as { number_a?: number; number_b?: number; operator?: string };
        } catch (error) {
          console.warn('Unable to parse tool input.', error);
          return {};
        }
      }
      return (part.input ?? {}) as { number_a?: number; number_b?: number; operator?: string };
    })();

    if (part.state === 'approval-requested' || part.state === 'input-available') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator approval requested</p>
          <p className="chat__tool-details">
            {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
          </p>
          <div className="chat__tool-actions">
            <button
              type="button"
              className="chat__tool-button"
              onClick={() => {
                if (
                  typeof parsedInput.number_a !== 'number' ||
                  typeof parsedInput.number_b !== 'number' ||
                  !parsedInput.operator
                ) {
                  addToolOutput({
                    tool: 'calculator',
                    toolCallId: part.toolCallId,
                    state: 'output-error',
                    errorText: 'Missing calculator inputs.',
                  });
                  return;
                }

                if (parsedInput.operator === '/' && parsedInput.number_b === 0) {
                  addToolOutput({
                    tool: 'calculator',
                    toolCallId: part.toolCallId,
                    state: 'output-error',
                    errorText: 'Cannot divide by zero.',
                  });
                  return;
                }

                const result =
                  parsedInput.operator === '+'
                    ? parsedInput.number_a + parsedInput.number_b
                    : parsedInput.operator === '-'
                      ? parsedInput.number_a - parsedInput.number_b
                      : parsedInput.operator === '*'
                        ? parsedInput.number_a * parsedInput.number_b
                        : parsedInput.number_a / parsedInput.number_b;

                addToolOutput({
                  tool: 'calculator',
                  toolCallId: part.toolCallId,
                  output: result,
                });
              }}
            >
              Approve
            </button>
            <button
              type="button"
              className="chat__tool-button chat__tool-button--deny"
              onClick={() =>
                addToolOutput({
                  tool: 'calculator',
                  toolCallId: part.toolCallId,
                  state: 'output-error',
                  errorText: 'Calculator request denied by user.',
                })
              }
            >
              Deny
            </button>
          </div>
        </div>
      );
    }

    if (
      (part.state === 'approval-responded' && part.approval.approved === false) ||
      part.state === 'output-denied'
    ) {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator request denied</p>
          <p className="chat__tool-details">
            {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
          </p>
        </div>
      );
    }

    if (part.state === 'output-available') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator result</p>
          <p className="chat__tool-details">
            {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b} = {part.output as number}
          </p>
        </div>
      );
    }

    if (part.state === 'output-error') {
      const errorText = part.errorText ?? 'Unable to process calculator request.';
      const isDenied = errorText.toLowerCase().includes('denied');
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">
            {isDenied ? 'Calculator request denied' : 'Calculator error'}
          </p>
          <p className="chat__tool-details">
            {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
          </p>
          <p className="chat__tool-details">{errorText}</p>
        </div>
      );
    }

    if (part.state === 'input-streaming') {
      return (
        <div key={part.toolCallId} className="chat__tool">
          <p className="chat__tool-title">Calculator request incoming…</p>
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
      return null;
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
