interface Props {
  search: string;
  includeArchived: boolean;
  disabled: boolean;
  onSearchChange: (value: string) => void;
  onApply: () => void;
  onReset: () => void;
  onArchiveToggle: (value: boolean) => void;
  onRefresh: () => void;
}

export default function Toolbar(props: Props) {
  return (
    <div className="toolbar">
      <label className="toolbar-field" htmlFor="search">
        <span className="toolbar-label">Поиск</span>
        <input
          id="search"
          className="input"
          type="search"
          value={props.search}
          placeholder="Номер, инициатор, содержание, ФИО"
          maxLength={200}
          disabled={props.disabled}
          onChange={(event) => props.onSearchChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') props.onApply();
          }}
        />
      </label>
      <div className="toolbar-actions">
        <button type="button" className="btn btn-primary" disabled={props.disabled} onClick={props.onApply}>
          Найти
        </button>
        <button type="button" className="btn" disabled={props.disabled} onClick={props.onReset}>
          Сбросить
        </button>
        <button type="button" className="btn" disabled={props.disabled} onClick={props.onRefresh}>
          Обновить
        </button>
        <label className="checkbox" htmlFor="archived">
          <input
            id="archived"
            type="checkbox"
            checked={props.includeArchived}
            disabled={props.disabled}
            onChange={(event) => props.onArchiveToggle(event.target.checked)}
          />
          <span>Показывать архивные</span>
        </label>
      </div>
      <div className="toolbar-mode" title="Стенд W01: редактирование отключено, офлайн-работа не предусмотрена">
        Режим: только чтение
      </div>
    </div>
  );
}
