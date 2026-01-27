import type { ReactNode } from 'react';

interface AppHeaderProps {
  title: string;
  subtitle: string | ReactNode;
  statusText: string;
  statusClassName?: string;
}

export function AppHeader({ title, subtitle, statusText, statusClassName }: AppHeaderProps) {
  return (
    <header className="app__header">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <span className={`status${statusClassName ? ` ${statusClassName}` : ''}`}>{statusText}</span>
    </header>
  );
}
