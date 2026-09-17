export interface StatusState {
  kind: 'idle' | 'ok' | 'loading' | 'error' | 'offline';
  text: string;
  serverMs: number | null;
  at: string | null;
}

interface Props {
  status: StatusState;
  postgresVersion: string | null;
  appVersion: string | null;
  onRetry: () => void;
}

export default function StatusBar({ status, postgresVersion, appVersion, onRetry }: Props) {
  return (
    <footer className={`statusbar status-${status.kind}`}>
      <span className="status-dot" aria-hidden="true" />
      <span className="status-text">{status.text}</span>
      {status.serverMs !== null ? (
        <span className="status-meta">сервер: {status.serverMs.toFixed(1)} мс</span>
      ) : null}
      {status.at ? <span className="status-meta">обновлено: {status.at}</span> : null}
      {postgresVersion ? <span className="status-meta">PostgreSQL {postgresVersion}</span> : null}
      {appVersion ? <span className="status-meta">стенд {appVersion}</span> : null}
      {status.kind === 'error' || status.kind === 'offline' ? (
        <button type="button" className="btn btn-small" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </footer>
  );
}
