import {
  DefaultChatTransport,
  type UIMessage,
  isTextUIPart,
  isToolUIPart,
  lastAssistantMessageIsCompleteWithToolCalls,
  StepStartUIPart,
  UIMessagePart,
  UIDataTypes,
  UITools
} from 'ai';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import './App.css';
import { AppHeader } from './components/AppHeader';
import { ChatErrorBanner } from './components/ChatErrorBanner';
import { ChatMessageList } from './components/ChatMessageList';
import { Composer } from './components/Composer';
import { ModelSelector } from './components/ModelSelector';
import { ToolMessage } from './components/ToolMessage';
import { ApprovalProvider } from './hooks/useApproval';
import { useChatWithModel } from './hooks/useChatWithModel';


export default function App() {
  const modelOptions = [
    'gpt-5.2',
    'gpt-5.1',
    'gpt-5',
    'gpt-5-mini',
    'gpt-5-nano',
    'gpt-5.2-chat-latest',
    'gpt-5.1-chat-latest',
    'gpt-5-chat-latest',
    'gpt-5.2-codex',
  ];
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState(modelOptions[0]);
  const [uiError, setUiError] = useState<string | null>(null);
  const [isErrorDismissed, setIsErrorDismissed] = useState(false);
  const [logMessages, setLogMessages] = useState(false);
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

  const statusText = isReady ? 'Ready' : isError ? 'Offline' : 'Thinking…';
  const statusClassName = `${isReady ? '' : 'status--active'}${isError ? ' status--error' : ''}`.trim();

  return (
    <div className="app">
      <AppHeader
        title="HomeAssistantAgent"
        subtitle="Ask questions about Home Assistant and get concise guidance."
        statusText={statusText}
        statusClassName={statusClassName}
      />

      <ModelSelector
        modelOptions={modelOptions}
        selectedModel={selectedModel}
        onChange={setSelectedModel}
        debugMessages={logMessages}
        onDebugChange={setLogMessages}
        onCopyMessages={onCopyMessages}
        copyDisabled={messages.length === 0}
      />

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
      </section>

      <Composer value={input} onChange={setInput} onSubmit={onSubmit} isBusy={isBusy} />
    </div>
  );
}
