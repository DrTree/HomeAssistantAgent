import type { FormEvent } from 'react';

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isBusy: boolean;
}

export function Composer({ value, onChange, onSubmit, isBusy }: ComposerProps) {
  const isDisabled = !value.trim() || isBusy;

  return (
    <div className="composer-dock">
      <form className="composer" onSubmit={onSubmit}>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask about automations, sensors, or setup tips…"
          aria-label="Message"
          disabled={isBusy}
        />
        <button type="submit" disabled={isDisabled} aria-label="Send message">
          Send
        </button>
      </form>
    </div>
  );
}
