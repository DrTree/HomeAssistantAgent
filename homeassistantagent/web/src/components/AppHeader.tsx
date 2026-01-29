import type { ReactNode } from 'react';

interface AppHeaderProps {
  title: string;
  statusText: string;
  statusClassName?: string;
  actions?: ReactNode;
}

export function AppHeader({
  title,
  statusText,
  statusClassName,
  actions,
}: AppHeaderProps) {
  return (
    <header className="app__header">
      <div className="app__header-bar">
        <div className="app__title-group">
          <h1>{title}</h1>
          {actions ? (
            <details className="app__menu">
              <summary className="app__menu-trigger" aria-label="Open settings menu">
                <span className="app__kebab" aria-hidden="true">
                  ⋮
                </span>
              </summary>
              <div className="app__menu-panel">{actions}</div>
            </details>
          ) : null}
        </div>
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
