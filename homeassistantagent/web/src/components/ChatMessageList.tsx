import type { UIMessage } from 'ai';
import type { ReactNode } from 'react';

type ChatMessageListProps = {
  messages: UIMessage[];
  renderMessageContent: (message: UIMessage) => ReactNode;
};

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
      {messages.map((message) => (
        <div key={message.id} className={`chat__message chat__message--${message.role}`}>
          <span className="chat__role">{message.role}</span>
          <div className="chat__content">{renderMessageContent(message)}</div>
        </div>
      ))}
    </>
  );
}
