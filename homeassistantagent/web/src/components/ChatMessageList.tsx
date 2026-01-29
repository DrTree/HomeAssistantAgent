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

        return (
          <div key={message.id} className={`chat__message chat__message--${message.role}`}>
            <div className="chat__content">{renderMessageContent(message)}</div>
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
