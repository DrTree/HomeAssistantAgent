interface ChatErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export function ChatErrorBanner({ message, onDismiss }: ChatErrorBannerProps) {
  return (
    <div className="chat__error">
      <div>
        <p className="chat__error-title">We hit a problem</p>
        <p className="chat__error-details">{message}</p>
      </div>
      <button type="button" className="chat__error-dismiss" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  );
}
