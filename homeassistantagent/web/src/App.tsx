import {
  DefaultChatTransport,
  type UIMessage,
  isTextUIPart,
  isToolUIPart,
  lastAssistantMessageIsCompleteWithToolCalls,
} from 'ai';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import './App.css';
import { ChatErrorBanner } from './components/ChatErrorBanner';
import { ChatMessageList } from './components/ChatMessageList';
import { Composer } from './components/Composer';
import { ToolMessage } from './components/ToolMessage';
import { ApprovalProvider } from './hooks/useApproval';
import { useChatWithModel } from './hooks/useChatWithModel';


export default function App() {
  const modelOptions = [
    { id: 'gpt-5.2', label: '5.2' },
    { id: 'gpt-5.1', label: '5.1' },
    { id: 'gpt-5', label: '5' },
    { id: 'gpt-5-mini', label: '5 mini' },
    { id: 'gpt-5-nano', label: '5 nano' },
    { id: 'gpt-5.2-chat-latest', label: '5.2 Turbo' },
    { id: 'gpt-5.1-chat-latest', label: '5.1 Chat' },
    { id: 'gpt-5-chat-latest', label: '5 Chat' },
    { id: 'gpt-5.2-codex', label: '5.2 Codex' },
  ];
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState(modelOptions[0]?.id ?? '');
  const [uiError, setUiError] = useState<string | null>(null);
  const [isErrorDismissed, setIsErrorDismissed] = useState(false);
  const [logMessages, setLogMessages] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [activeSubmenu, setActiveSubmenu] = useState<'models' | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const transport = useMemo(() => new DefaultChatTransport({ api: 'api/chat' }), []);
  const { messages, sendMessage, status, error } = useChatWithModel({
    transport,
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,
    model: selectedModel,
  });
  const isBusy = status === 'submitted' || status === 'streaming';
  const isReady = status === 'ready';
  const isError = status === 'error' || Boolean(error);

  const errorMessage = isErrorDismissed
    ? null
    : uiError ??
      (isError
        ? 'The chat service is unavailable right now. Check the server logs for details.'
        : null);

  useEffect(() => {
    if (error) {
      setIsErrorDismissed(false);
      setUiError(error instanceof Error ? error.message : 'Unexpected chat error.');
    }
  }, [error]);

  useEffect(() => {
    if (logMessages) {
      console.log('Chat messages', messages);
    }
  }, [logMessages, messages]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
        setActiveSubmenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const onCopyMessages = async () => {
    if (!navigator?.clipboard?.writeText) {
      setIsErrorDismissed(false);
      setUiError('Clipboard access is not available in this browser.');
      return;
    }

    try {
      await navigator.clipboard.writeText(JSON.stringify(messages, null, 2));
    } catch (copyError) {
      setIsErrorDismissed(false);
      setUiError(
        copyError instanceof Error ? copyError.message : 'Unable to copy chat messages.',
      );
    }
  };

  const renderMessageContent = (message: UIMessage) => {
    if (message.parts.length === 0) {
      return '';
    }

    return message.parts.map((part, index) => {
      if ('type' in part && part.type === 'reasoning') {
        return null;
      }
      if (isTextUIPart(part)) {
        return (
          <p key={`${message.id}-text-${index}`} className="chat__text">
            {part.text}
          </p>
        );
      }
        if (isToolUIPart(part)) {
          return (
            <ToolMessage
              key={`${message.id}-tool-${index}`}
              part={part}
            />
          );
        }
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

    try {
      await sendMessage(
        { text: trimmedInput },
        {
          body: {
            model: selectedModel,
          },
        },
      );
      setInput('');
    } catch (sendError) {
      setIsErrorDismissed(false);
      setUiError(
        sendError instanceof Error
          ? sendError.message
          : 'Unable to send your message. Please try again.',
      );
    }
  };

  const statusText = isError ? 'Offline' : isBusy ? 'Responding' : 'Stopped';
  const statusClassName = `${isBusy ? 'status--active' : ''}${isError ? ' status--error' : ''}`.trim();
  const selectedModelLabel =
    modelOptions.find((option) => option.id === selectedModel)?.label ?? selectedModel;

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-menu" ref={menuRef}>
          <button
            type="button"
            className="app-menu__trigger"
            onClick={() => setShowMenu((open) => !open)}
            aria-expanded={showMenu}
          >
            <span className="app-menu__dots" aria-hidden="true">
              <span />
              <span />
            </span>
            <span className="app-menu__title">
              HomeAgent <span className="app-menu__model">{selectedModelLabel}</span>
            </span>
            <span className={`app-menu__chevron ${showMenu ? 'is-open' : ''}`} aria-hidden="true">
              ▾
            </span>
          </button>

          {showMenu ? (
            <div className="app-menu__panel" role="menu">
              {!activeSubmenu ? (
                <>
                  <button
                    type="button"
                    className="app-menu__item"
                    onClick={() => setActiveSubmenu('models')}
                  >
                    <span>Switch Model</span>
                    <span className="app-menu__item-chevron">›</span>
                  </button>
                  <div className="app-menu__divider" />
                  <button
                    type="button"
                    className="app-menu__item"
                    onClick={() => setLogMessages((value) => !value)}
                  >
                    <span>Debug Logging</span>
                    <span
                      className={`app-menu__toggle ${logMessages ? 'is-on' : ''}`}
                      aria-hidden="true"
                    >
                      <span />
                    </span>
                  </button>
                  <button
                    type="button"
                    className="app-menu__item"
                    onClick={() => {
                      void onCopyMessages();
                      setShowMenu(false);
                      setActiveSubmenu(null);
                    }}
                    disabled={messages.length === 0}
                  >
                    Copy Conversation
                  </button>
                  <div className="app-menu__divider" />
                  <button type="button" className="app-menu__item" disabled>
                    Settings
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="app-menu__item app-menu__item--back"
                    onClick={() => setActiveSubmenu(null)}
                  >
                    <span className="app-menu__item-chevron">‹</span>
                    Models
                  </button>
                  {modelOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className="app-menu__item app-menu__item--model"
                      onClick={() => {
                        setSelectedModel(option.id);
                        setActiveSubmenu(null);
                        setShowMenu(false);
                      }}
                    >
                      <span>{option.label}</span>
                      {selectedModel === option.id ? (
                        <span className="app-menu__check" aria-hidden="true">
                          ✓
                        </span>
                      ) : null}
                    </button>
                  ))}
                </>
              )}
            </div>
          ) : null}
        </div>

        <div className="app-topbar__actions">
          <span className={`status ${statusClassName}`} aria-live="polite">
            {statusText}
          </span>
          <button type="button" className="icon-button" aria-label="More options">
            ⋯
          </button>
        </div>
      </header>

      {logMessages ? (
        <aside className="debug-panel">
          <p>[SYS] Model version: {selectedModelLabel}</p>
          <p>[NET] Socket connected: {isError ? 'offline' : '200 OK'}</p>
          <p>[LOG] Stream status: {isBusy ? 'streaming' : 'idle'}</p>
          <p>[LOG] Message count: {messages.length}</p>
          <p>[ACT] Listening for input…</p>
        </aside>
      ) : null}

      <section className="chat">
        {errorMessage ? (
          <ChatErrorBanner
            message={errorMessage}
            onDismiss={() => {
              setIsErrorDismissed(true);
              setUiError(null);
            }}
          />
        ) : null}
        <ApprovalProvider sendMessage={sendMessage}>
          <ChatMessageList messages={messages} renderMessageContent={renderMessageContent} />
        </ApprovalProvider>
        <div ref={messagesEndRef} />
      </section>

      <Composer value={input} onChange={setInput} onSubmit={onSubmit} isBusy={isBusy} />
    </div>
  );
}
