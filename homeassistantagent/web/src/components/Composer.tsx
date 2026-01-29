import { useRef, type FormEvent } from 'react';

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isBusy: boolean;
}

export function Composer({ value, onChange, onSubmit, isBusy }: ComposerProps) {
  const isDisabled = !value.trim() || isBusy;
  const formRef = useRef<HTMLFormElement | null>(null);
  return (
    <div className="composer-dock">
      <form ref={formRef} className="composer" onSubmit={onSubmit}>
        <button type="button" className="composer__icon-button" aria-label="Add attachment">
          +
        </button>
        <textarea
          value={value}
          rows={1}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Make this home smart…"
          aria-label="Message"
          disabled={isBusy}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              if (!isDisabled) {
                formRef.current?.requestSubmit();
              }
            }
          }}
          onInput={(event) => {
            const target = event.currentTarget;
            target.style.height = 'auto';
            target.style.height = `${target.scrollHeight}px`;
          }}
        />
        <div className="composer__actions">
          <button
            type="submit"
            disabled={isDisabled}
            className="composer__send"
            aria-label="Send message"
          >
            ↑
          </button>
        </div>
      </form>
    </div>
  );
}
