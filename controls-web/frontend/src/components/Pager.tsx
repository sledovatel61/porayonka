interface Props {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  loading: boolean;
  onGo: (page: number) => void;
}

export default function Pager({ page, pages, total, pageSize, loading, onGo }: Props) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const canPrev = page > 1 && !loading;
  const canNext = page < pages && !loading;

  return (
    <div className="pager">
      <button type="button" className="btn" disabled={!canPrev} onClick={() => onGo(1)}>
        В начало
      </button>
      <button type="button" className="btn" disabled={!canPrev} onClick={() => onGo(page - 1)}>
        ‹ Назад
      </button>
      <span className="pager-info">
        Строки {from}–{to} из {total} · страница {page} из {Math.max(pages, 1)} · по {pageSize}
      </span>
      <button type="button" className="btn" disabled={!canNext} onClick={() => onGo(page + 1)}>
        Вперёд ›
      </button>
      <button type="button" className="btn" disabled={!canNext} onClick={() => onGo(pages)}>
        В конец
      </button>
    </div>
  );
}
