import type { ReactNode } from 'react';

interface AppHeaderProps {
  title: string;
  subtitle: string | ReactNode;
  statusText: string;
  statusClassName?: string;
  actions?: ReactNode;
}

export function AppHeader({
  title,
  subtitle,
  statusText,
  statusClassName,
  actions,
}: AppHeaderProps) {
  return (
    <header className="app__header">
      <div className="app__header-main">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="app__header-actions">
        {actions}
        <span
          className={`status${statusClassName ? ` ${statusClassName}` : ''}`}
          aria-live="polite"
        >
          {statusText}
        </span>
      </div>
    </header>
  );
}
