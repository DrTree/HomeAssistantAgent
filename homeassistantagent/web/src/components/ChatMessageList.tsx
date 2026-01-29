import type { UIMessage } from 'ai';
import type { ReactNode } from 'react';

type ChatMessageListProps = {
  messages: UIMessage[];
  renderMessageContent: (message: UIMessage) => ReactNode;
};

const getReasoningParts = (message: UIMessage) =>
  message.parts
    .filter(
      (part): part is { type: 'reasoning'; text: string } =>
        'type' in part && part.type === 'reasoning' && typeof part.text === 'string',
    )
    .map((part) => part.text.trim())
    .filter(Boolean);

const getMessageText = (message: UIMessage) =>
  message.parts
    .filter((part): part is { type: 'text'; text: string } => 'type' in part && part.type === 'text')
    .map((part) => part.text)
    .join('\n')
    .trim();

export function ChatMessageList({
  messages,
  renderMessageContent,
}: ChatMessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="chat__empty">
        <p>Start a conversation by asking your first question.</p>
      </div>
    );
  }

  return (
    <>
      {messages.map((message) => {
        const reasoningParts = message.role === 'assistant' ? getReasoningParts(message) : [];
        const messageText = message.role === 'user' ? getMessageText(message) : '';

        return (
          <div key={message.id} className={`chat__message chat__message--${message.role}`}>
            <div className="chat__content">{renderMessageContent(message)}</div>
            {message.role === 'user' ? (
              <div className="chat__message-actions">
                <button
                  type="button"
                  className="chat__message-action"
                  onClick={async () => {
                    if (!messageText || !navigator?.clipboard?.writeText) {
                      return;
                    }
                    try {
                      await navigator.clipboard.writeText(messageText);
                    } catch (error) {
                      console.warn('Unable to copy message', error);
                    }
                  }}
                  disabled={!messageText}
                >
                  Copy
                </button>
                <button type="button" className="chat__message-action" disabled>
                  Edit
                </button>
              </div>
            ) : null}
            {reasoningParts.length > 0 ? (
              <details className="chat__reasoning">
                <summary>Reasoning</summary>
                <div className="chat__reasoning-body">
                  {reasoningParts.map((reasoning, index) => (
                    <p key={`${message.id}-reasoning-${index}`} className="chat__reasoning-text">
                      {reasoning}
                    </p>
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        );
      })}
    </>
  );
}
