import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, getControl, getHealth, getSummary, listControls } from './api';
import type { ControlCardData, ControlListItem, ControlsPage, Health, ListQuery, Summary } from './types';
import SummaryBar from './components/SummaryBar';
import Toolbar from './components/Toolbar';
import ControlsTable from './components/ControlsTable';
import Pager from './components/Pager';
import ControlCard from './components/ControlCard';
import StatusBar from './components/StatusBar';
import type { StatusState } from './components/StatusBar';

const PAGE_SIZE = 50;
const UPLOAD_ENABLED = true; // временная функция стенда W01 (удаляется до передачи W02)

function nowLabel(): string {
  const now = new Date();
  const pad = (value: number) => (value < 10 ? `0${value}` : String(value));
  return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

function toStatus(error: unknown): StatusState {
  const apiError = error instanceof ApiError ? error : null;
  const offline = apiError !== null && apiError.status === 0;
  return {
    kind: offline ? 'offline' : 'error',
    text: apiError ? apiError.message : 'Неизвестная ошибка при обращении к стенду.',
    serverMs: null,
    at: nowLabel(),
  };
}

export default function App() {
  const [query, setQuery] = useState<ListQuery>({
    page: 1,
    pageSize: PAGE_SIZE,
    search: '',
    includeArchived: false,
  });
  const [draft, setDraft] = useState('');
  const [page, setPage] = useState<ControlsPage | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [card, setCard] = useState<ControlCardData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [cardLoading, setCardLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [status, setStatus] = useState<StatusState>({
    kind: 'loading',
    text: 'Подключение к стенду…',
    serverMs: null,
    at: null,
  });

  const listToken = useRef(0);
  const cardToken = useRef(0);

  const loadList = useCallback(async (target: ListQuery) => {
    const token = ++listToken.current;
    setListLoading(true);
    try {
      const result = await listControls(target);
      if (token !== listToken.current) return;
      setPage(result.data);
      setStatus({
        kind: 'ok',
        text: `Показано ${result.data.items.length} строк из ${result.data.total}`,
        serverMs: result.serverMs,
        at: nowLabel(),
      });
    } catch (error) {
      if (token !== listToken.current) return;
      setStatus(toStatus(error));
    } finally {
      if (token === listToken.current) setListLoading(false);
    }
  }, []);

  const loadCard = useCallback(async (id: string) => {
    const token = ++cardToken.current;
    setCardLoading(true);
    try {
      const result = await getControl(id);
      if (token !== cardToken.current) return;
      setCard(result.data);
    } catch (error) {
      if (token !== cardToken.current) return;
      setCard(null);
      setStatus(toStatus(error));
    } finally {
      if (token === cardToken.current) setCardLoading(false);
    }
  }, []);

  const loadMeta = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const [summaryResult, healthResult] = await Promise.all([getSummary(), getHealth()]);
      setSummary(summaryResult.data);
      setHealth(healthResult.data);
    } catch (error) {
      setStatus(toStatus(error));
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    void loadList(query);
  }, [query, loadList]);

  const applySearch = useCallback(() => {
    setQuery((prev) => ({ ...prev, page: 1, search: draft }));
  }, [draft]);

  const resetFilters = useCallback(() => {
    setDraft('');
    setQuery({ page: 1, pageSize: PAGE_SIZE, search: '', includeArchived: false });
  }, []);

  const refresh = useCallback(() => {
    void loadMeta();
    void loadList(query);
    if (selectedId) void loadCard(selectedId);
  }, [loadMeta, loadList, query, selectedId, loadCard]);

  const selectRow = useCallback(
    (item: ControlListItem) => {
      setSelectedId(item.id);
      void loadCard(item.id);
    },
    [loadCard],
  );

  const closeCard = useCallback(() => {
    cardToken.current += 1;
    setSelectedId(null);
    setCard(null);
  }, []);

  const afterUpload = useCallback(() => {
    if (selectedId) void loadCard(selectedId);
    void loadList(query);
    void loadMeta();
  }, [selectedId, loadCard, query, loadList, loadMeta]);

  const items = page ? page.items : [];

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title-block">
          <h1 className="app-title">Контроли</h1>
          <p className="app-subtitle">
            Технический стенд W01 · синтетические данные · только чтение · офлайн-редактирование не предусмотрено
          </p>
        </div>
        <SummaryBar summary={summary} loading={summaryLoading} />
      </header>

      <Toolbar
        search={draft}
        includeArchived={query.includeArchived}
        disabled={listLoading}
        onSearchChange={setDraft}
        onApply={applySearch}
        onReset={resetFilters}
        onArchiveToggle={(value) => setQuery((prev) => ({ ...prev, page: 1, includeArchived: value }))}
        onRefresh={refresh}
      />

      <main className="layout">
        <section className="list-col">
          <ControlsTable
            items={items}
            loading={listLoading}
            selectedId={selectedId}
            today={new Date()}
            onSelect={selectRow}
          />
          <Pager
            page={page ? page.page : 1}
            pages={page ? page.pages : 0}
            total={page ? page.total : 0}
            pageSize={page ? page.page_size : PAGE_SIZE}
            loading={listLoading}
            onGo={(target) => setQuery((prev) => ({ ...prev, page: target }))}
          />
        </section>
        <ControlCard
          card={card}
          loading={cardLoading}
          uploadEnabled={UPLOAD_ENABLED}
          onClose={closeCard}
          onUploaded={afterUpload}
        />
      </main>

      <StatusBar
        status={status}
        postgresVersion={health ? health.postgres_version : null}
        appVersion={health ? health.app_version : null}
        onRetry={refresh}
      />
    </div>
  );
}
