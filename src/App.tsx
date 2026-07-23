import { useState, useEffect, useRef, useCallback } from "react";

// ─────────────────────────────────────────────
// ТИПЫ И КОНСТАНТЫ
// ─────────────────────────────────────────────
type Status = "empty" | "received" | "in_progress";

interface Department {
  id: number;
  name: string;
  status: Status;
  updatedAt: string | null;
  isOvd: boolean;
}

const INITIAL_DEPARTMENTS: Department[] = [
  { id: 1,  name: "СО по г. Азов",                                       status: "empty", updatedAt: null, isOvd: false },
  { id: 2,  name: "СО по Аксайскому району",                             status: "empty", updatedAt: null, isOvd: false },
  { id: 3,  name: "СО по г. Батайск",                                    status: "empty", updatedAt: null, isOvd: false },
  { id: 4,  name: "Белокалитвинский МСО",                                status: "empty", updatedAt: null, isOvd: false },
  { id: 5,  name: "СО по г. Волгодонск",                                 status: "empty", updatedAt: null, isOvd: false },
  { id: 6,  name: "Зерноградский МСО",                                   status: "empty", updatedAt: null, isOvd: false },
  { id: 7,  name: "СО по г. Донецк",                                     status: "empty", updatedAt: null, isOvd: false },
  { id: 8,  name: "Зимовниковский МСО",                                  status: "empty", updatedAt: null, isOvd: false },
  { id: 9,  name: "СО по г. Красный Сулин",                              status: "empty", updatedAt: null, isOvd: false },
  { id: 10, name: "Миллеровский МСО",                                    status: "empty", updatedAt: null, isOvd: false },
  { id: 11, name: "Морозовский МСО",                                     status: "empty", updatedAt: null, isOvd: false },
  { id: 12, name: "Неклиновский МСО",                                    status: "empty", updatedAt: null, isOvd: false },
  { id: 13, name: "СО по г. Новочеркасск",                               status: "empty", updatedAt: null, isOvd: false },
  { id: 14, name: "СО по г. Новошахтинск",                               status: "empty", updatedAt: null, isOvd: false },
  { id: 15, name: "Сальский МСО",                                        status: "empty", updatedAt: null, isOvd: false },
  { id: 16, name: "Семикаракорский МСО",                                 status: "empty", updatedAt: null, isOvd: false },
  { id: 17, name: "Шолоховский МСО",                                     status: "empty", updatedAt: null, isOvd: false },
  { id: 18, name: "СО по г. Таганрог",                                   status: "empty", updatedAt: null, isOvd: false },
  { id: 19, name: "СО по г. Шахты",                                      status: "empty", updatedAt: null, isOvd: false },
  { id: 20, name: "СО по Ворошиловскому району г. Ростов-на-Дону",       status: "empty", updatedAt: null, isOvd: false },
  { id: 21, name: "СО по Железнодорожному району г. Ростов-на-Дону",     status: "empty", updatedAt: null, isOvd: false },
  { id: 22, name: "СО по Кировскому району г. Ростов-на-Дону",           status: "empty", updatedAt: null, isOvd: false },
  { id: 23, name: "СО по Ленинскому району г. Ростов-на-Дону",           status: "empty", updatedAt: null, isOvd: false },
  { id: 24, name: "СО по Октябрьскому району г. Ростов-на-Дону",         status: "empty", updatedAt: null, isOvd: false },
  { id: 25, name: "СО по Первомайскому району г. Ростов-на-Дону",        status: "empty", updatedAt: null, isOvd: false },
  { id: 26, name: "СО по Пролетарскому району г. Ростов-на-Дону",        status: "empty", updatedAt: null, isOvd: false },
  { id: 27, name: "Советский МСО",                                       status: "empty", updatedAt: null, isOvd: false },
  { id: 28, name: "ОВД-1",                                               status: "empty", updatedAt: null, isOvd: true  },
  { id: 29, name: "ОВД-2",                                               status: "empty", updatedAt: null, isOvd: true  },
];

const STORAGE_KEY = "porayonka_departments";

const STATUS_CYCLE: Status[] = ["empty", "received", "in_progress"];

function toggleStatus(current: Status): Status {
  const idx = STATUS_CYCLE.indexOf(current);
  return STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
}

function now(): string {
  return new Date().toISOString();
}

// ─────────────────────────────────────────────
// ХРАНИЛИЩЕ (localStorage вместо %APPDATA%)
// ─────────────────────────────────────────────
function loadDepartments(): Department[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return INITIAL_DEPARTMENTS.map(d => ({ ...d }));
    const saved: Department[] = JSON.parse(raw);
    // Слияние: новые отделы добавляются автоматически
    const byId = new Map(saved.map(d => [d.id, d]));
    return INITIAL_DEPARTMENTS.map(d => byId.get(d.id) ?? { ...d });
  } catch {
    return INITIAL_DEPARTMENTS.map(d => ({ ...d }));
  }
}

function saveDepartments(deps: Department[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(deps));
}

// ─────────────────────────────────────────────
// ЭКСПОРТ HTML
// ─────────────────────────────────────────────
function exportHTML(departments: Department[]): void {
  const dateStr = new Date().toLocaleString("ru-RU");

  const STATUS_STYLE: Record<Status, string> = {
    received:    "background:#27AE60;color:#fff;font-weight:600;",
    in_progress: "background:#F39C12;color:#fff;font-weight:600;",
    empty:       "background:#ECF0F1;color:#7F8C8D;",
  };
  const STATUS_LABEL: Record<Status, string> = {
    received:    "✅ Получено",
    in_progress: "🔄 В работе",
    empty:       "—",
  };

  const rows = departments.map(d => `
    <tr>
      <td style="text-align:center;padding:10px 12px;border:1px solid #dee2e6;">${d.isOvd ? "" : d.id}</td>
      <td style="padding:10px 14px;border:1px solid #dee2e6;${d.isOvd ? "font-style:italic;color:#64748b;" : ""}">${d.name}</td>
      <td style="text-align:center;padding:10px 12px;border:1px solid #dee2e6;${STATUS_STYLE[d.status]}">${STATUS_LABEL[d.status]}</td>
      <td style="text-align:center;padding:10px;border:1px solid #dee2e6;color:#64748b;font-size:13px;">${d.updatedAt ? new Date(d.updatedAt).toLocaleString("ru-RU") : ""}</td>
    </tr>`).join("");

  const received    = departments.filter(d => d.status === "received").length;
  const in_progress = departments.filter(d => d.status === "in_progress").length;
  const empty       = departments.filter(d => d.status === "empty").length;

  const html = `<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<title>Порайонка — ${dateStr}</title>
<style>
  body{font-family:'Segoe UI',Arial,sans-serif;margin:30px;background:#f8f9fa;color:#2c3e50;}
  h1{font-size:24px;margin-bottom:4px;}
  .subtitle{color:#6c757d;margin-bottom:20px;font-size:14px;}
  table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);}
  thead tr{background:linear-gradient(135deg,#1e293b,#334155);color:#fff;}
  th{padding:13px 14px;text-align:left;font-size:13px;font-weight:600;text-transform:uppercase;}
  th:first-child{text-align:center;width:60px;}
  tbody tr:nth-child(even){background:#f8faf0;}
  tbody tr:hover{background:#eff6ff;}
  .summary{margin-top:20px;padding:16px;background:#fff;border-radius:8px;display:flex;gap:24px;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,.06);}
  .btn{display:inline-block;padding:10px 20px;background:#3b82f6;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;margin-bottom:16px;}
  @media print{.no-print{display:none!important}body{margin:10mm}table{box-shadow:none}}
</style></head><body>
<div style="background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:24px;display:flex;align-items:center;gap:14px;">
  <span style="font-size:36px;">🏛️</span>
  <div><div style="font-size:22px;font-weight:700;">Порайонка</div>
  <div style="color:#94a3b8;font-size:13px;">Следственный комитет РФ · Ростовская область</div></div>
  <div style="margin-left:auto;text-align:right;color:#94a3b8;font-size:13px;">Сформировано<br><strong style="color:#fff;">${dateStr}</strong></div>
</div>
<div class="no-print"><button class="btn" onclick="window.print()">🖨️ Распечатать</button></div>
<table><thead><tr>
  <th style="text-align:center;">№</th>
  <th>Следственный отдел</th>
  <th style="width:160px;text-align:center;">Статус</th>
  <th style="width:150px;text-align:center;">Обновлено</th>
</tr></thead><tbody>${rows}</tbody></table>
<div class="summary">
  <strong>ИТОГО:</strong>
  <span style="color:#27AE60">✅ Получено: <strong>${received}</strong></span>
  <span style="color:#F39C12">🔄 В работе: <strong>${in_progress}</strong></span>
  <span style="color:#94a3b8">⬜ Не получено: <strong>${empty}</strong></span>
  <span style="margin-left:auto">📋 Всего: <strong>${departments.length}</strong></span>
</div>
</body></html>`;

  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `porayonka_${new Date().toISOString().slice(0,10)}.html`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────
// ЭКСПОРТ CSV
// ─────────────────────────────────────────────
function exportCSV(departments: Department[]): void {
  const STATUS_LABEL: Record<Status, string> = {
    received:    "Получено",
    in_progress: "В работе",
    empty:       "Не получено",
  };
  const BOM = "\uFEFF";
  const header = "№;Следственный отдел;Статус;Обновлено\n";
  const rows = departments.map(d =>
    `${d.isOvd ? "" : d.id};${d.name};${STATUS_LABEL[d.status]};${d.updatedAt ? new Date(d.updatedAt).toLocaleString("ru-RU") : ""}`
  ).join("\n");

  const blob = new Blob([BOM + header + rows], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `porayonka_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────
// КОМПОНЕНТ: СТАТУС-ЯЧЕЙКА
// ─────────────────────────────────────────────
function StatusCell({ dept, onClick }: { dept: Department; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);

  const config = {
    empty: {
      bg: hovered ? "#e2e8f0" : "#f1f5f9",
      content: <span className="text-slate-400 text-base font-medium">—</span>,
    },
    received: {
      bg: hovered ? "#bbf7d0" : "#dcfce7",
      content: (
        <div className="flex items-center gap-2 justify-center">
          <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-bold">✓</div>
          <span className="text-green-700 font-semibold text-sm">Получено</span>
        </div>
      ),
    },
    in_progress: {
      bg: hovered ? "#fde68a" : "#fef3c7",
      content: (
        <div className="flex items-center gap-2 justify-center">
          <div className="w-6 h-6 rounded-full bg-amber-400 flex items-center justify-center text-white text-xs font-bold spinning">↻</div>
          <span className="text-amber-700 font-semibold text-sm">В работе</span>
        </div>
      ),
    },
  };

  const cfg = config[dept.status];

  return (
    <div
      className="rounded-lg px-3 py-2.5 cursor-pointer transition-all duration-150 select-none min-h-[44px] flex items-center justify-center"
      style={{ backgroundColor: cfg.bg }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Кликните для смены статуса"
    >
      {cfg.content}
    </div>
  );
}

// ─────────────────────────────────────────────
// КОМПОНЕНТ: КАРТОЧКА СТАТИСТИКИ
// ─────────────────────────────────────────────
function StatCard({
  icon, value, label, bg, border, textColor, iconBg,
  extra,
}: {
  icon: string; value: string; label: string;
  bg: string; border: string; textColor: string; iconBg: string;
  extra?: React.ReactNode;
}) {
  return (
    <div
      className="flex-1 rounded-xl p-4 shadow-sm"
      style={{ backgroundColor: bg, border: `1.5px solid ${border}` }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-base flex-shrink-0"
          style={{ backgroundColor: iconBg }}
        >
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-2xl font-bold leading-none" style={{ color: textColor }}>{value}</div>
          <div className="text-xs text-slate-500 mt-0.5">{label}</div>
        </div>
      </div>
      {extra && <div className="mt-2">{extra}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────
// КОМПОНЕНТ: TOAST
// ─────────────────────────────────────────────
function Toast({ message, visible }: { message: string; visible: boolean }) {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
      }`}
      style={{ backgroundColor: "#1e293b" }}
    >
      <div className="w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold"
        style={{ backgroundColor: "#22c55e25", color: "#22c55e" }}>✓</div>
      <span className="text-white text-sm font-medium">{message}</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// КОМПОНЕНТ: МОДАЛЬНОЕ ОКНО ЭКСПОРТА
// ─────────────────────────────────────────────
function ExportModal({
  open, onClose, departments,
}: { open: boolean; onClose: () => void; departments: Department[] }) {
  const [csvDone, setCsvDone] = useState(false);
  const [htmlDone, setHtmlDone] = useState(false);

  useEffect(() => {
    if (open) { setCsvDone(false); setHtmlDone(false); }
  }, [open]);

  const received    = departments.filter(d => d.status === "received").length;
  const in_progress = departments.filter(d => d.status === "in_progress").length;
  const empty       = departments.filter(d => d.status === "empty").length;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Заголовок */}
        <div className="flex items-center gap-3 px-6 py-4" style={{ background: "linear-gradient(135deg,#1e293b,#334155)" }}>
          <span className="text-xl">📤</span>
          <span className="text-white font-bold text-lg flex-1">Экспорт данных</span>
          <button className="text-white/70 hover:text-white text-xl leading-none" onClick={onClose}>✕</button>
        </div>

        <div className="p-5 space-y-3">
          {/* CSV */}
          <ExportCard
            icon="📊" title="CSV / Excel"
            desc="Открывается в Microsoft Excel, LibreOffice Calc и Google Таблицах"
            done={csvDone}
            onClick={() => { exportCSV(departments); setCsvDone(true); }}
          />
          {/* HTML */}
          <ExportCard
            icon="🖨️" title="HTML (печать)"
            desc="Красиво оформленная таблица. Откройте в браузере и нажмите Ctrl+P"
            done={htmlDone}
            onClick={() => { exportHTML(departments); setHtmlDone(true); }}
          />

          {/* Сводка */}
          <div className="rounded-xl p-4 space-y-2" style={{ backgroundColor: "#f8fafc", border: "1px solid #e2e8f0" }}>
            <div className="text-sm font-semibold text-slate-700 mb-3">Сводка по экспорту</div>
            <div className="flex justify-around">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{received}</div>
                <div className="text-xs text-slate-500">Получено</div>
              </div>
              <div className="w-px bg-slate-200" />
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-500">{in_progress}</div>
                <div className="text-xs text-slate-500">В работе</div>
              </div>
              <div className="w-px bg-slate-200" />
              <div className="text-center">
                <div className="text-2xl font-bold text-slate-400">{empty}</div>
                <div className="text-xs text-slate-500">Не получено</div>
              </div>
            </div>
          </div>

          <button
            className="w-full py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
            style={{ backgroundColor: "#f1f5f9" }}
            onClick={onClose}
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

function ExportCard({ icon, title, desc, done, onClick }: {
  icon: string; title: string; desc: string; done: boolean; onClick: () => void;
}) {
  const [hov, setHov] = useState(false);
  return (
    <div
      className="rounded-xl p-4 cursor-pointer transition-all duration-150 border"
      style={{ backgroundColor: hov ? "#f0f9ff" : "white", borderColor: "#e2e8f0" }}
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      <div className="flex items-center gap-3">
        <span className="text-3xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-slate-700 text-sm">{title}</div>
          <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</div>
        </div>
        {done && (
          <span className="text-xs font-semibold text-white px-2.5 py-1 rounded-full flex-shrink-0"
            style={{ backgroundColor: "#22c55e" }}>Скачан ✓</span>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// КОМПОНЕНТ: МОДАЛЬНОЕ ОКНО СБРОСА
// ─────────────────────────────────────────────
function ResetModal({ open, onClose, onConfirm }: {
  open: boolean; onClose: () => void; onConfirm: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-6 py-4" style={{ background: "linear-gradient(135deg,#dc2626,#b91c1c)" }}>
          <span className="text-xl">⚠️</span>
          <span className="text-white font-bold text-lg">Сброс данных</span>
        </div>
        <div className="p-6 text-center space-y-3">
          <div className="text-4xl">🔄</div>
          <p className="text-slate-700 font-medium text-sm leading-relaxed">
            Все статусы будут сброшены до начального состояния.
          </p>
          <p className="text-red-600 font-bold text-sm">Это действие нельзя отменить.</p>
          <p className="text-slate-500 text-sm italic">Вы уверены, что хотите продолжить?</p>
          <div className="flex gap-3 pt-2">
            <button
              className="flex-1 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
              style={{ backgroundColor: "#f1f5f9" }}
              onClick={onClose}
            >Отмена</button>
            <button
              className="flex-1 py-2.5 rounded-xl text-sm font-bold text-white transition-colors hover:opacity-90"
              style={{ backgroundColor: "#dc2626" }}
              onClick={onConfirm}
            >Сбросить</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ГЛАВНЫЙ КОМПОНЕНТ
// ─────────────────────────────────────────────
export default function App() {
  const [departments, setDepartments] = useState<Department[]>(() => loadDepartments());
  const [search, setSearch] = useState("");
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [showReset, setShowReset] = useState(false);
  const [toast, setToast] = useState({ visible: false, message: "" });
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Автосохранение при монтировании (восстановить дату)
  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY + "_meta");
    if (raw) {
      try { setLastSaved(JSON.parse(raw).lastSaved); } catch {}
    }
  }, []);

  const showToast = useCallback((msg: string) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ visible: true, message: msg });
    toastTimer.current = setTimeout(() => setToast(t => ({ ...t, visible: false })), 2500);
  }, []);

  // Сохранение
  const save = useCallback((deps: Department[], silent = false) => {
    saveDepartments(deps);
    const ts = now();
    setLastSaved(ts);
    localStorage.setItem(STORAGE_KEY + "_meta", JSON.stringify({ lastSaved: ts }));
    if (!silent) showToast("Данные сохранены");
  }, [showToast]);

  // Клик по статусу
  const handleStatusClick = useCallback((id: number) => {
    setDepartments(prev => {
      const next = prev.map(d =>
        d.id === id
          ? { ...d, status: toggleStatus(d.status), updatedAt: now() }
          : d
      );
      save(next, true); // автосохранение
      return next;
    });
  }, [save]);

  // Сброс
  const handleReset = useCallback(() => {
    const reset = INITIAL_DEPARTMENTS.map(d => ({ ...d }));
    setDepartments(reset);
    save(reset, true);
    setShowReset(false);
    showToast("Все статусы сброшены");
  }, [save, showToast]);

  // Статистика
  const received    = departments.filter(d => d.status === "received").length;
  const in_progress = departments.filter(d => d.status === "in_progress").length;
  const empty       = departments.filter(d => d.status === "empty").length;
  const total       = departments.length;
  const percent     = Math.round((received / total) * 100);

  // Фильтрация
  const filtered = departments.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  const formatSaved = (iso: string | null) => {
    if (!iso) return "Ещё не сохранено";
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#f8fafc" }}>

      {/* ── ШАПКА ── */}
      <header style={{ background: "linear-gradient(135deg,#1e293b,#0f172a)" }}
        className="px-6 py-4 shadow-lg flex-shrink-0">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center text-3xl"
              style={{ backgroundColor: "rgba(255,255,255,0.1)" }}>🏛️</div>
            <div>
              <h1 className="text-white font-bold text-2xl leading-tight">Порайонка</h1>
              <p className="text-slate-400 text-xs mt-0.5">Следственный комитет РФ · Ростовская область</p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-slate-500 text-xs">Последнее сохранение</div>
            <div className="text-slate-300 text-sm font-medium mt-0.5">{formatSaved(lastSaved)}</div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-5">

        {/* ── СТАТИСТИКА ── */}
        <div className="flex gap-3 mb-4">
          <StatCard
            icon="✓" value={String(received)} label="Получено"
            bg="#dcfce7" border="#22c55e" textColor="#15803d" iconBg="#22c55e"
          />
          <StatCard
            icon="↻" value={String(in_progress)} label="В работе"
            bg="#fef3c7" border="#f59e0b" textColor="#d97706" iconBg="#f59e0b"
          />
          <StatCard
            icon="○" value={String(empty)} label="Не получено"
            bg="#f1f5f9" border="#94a3b8" textColor="#64748b" iconBg="#94a3b8"
          />
          <StatCard
            icon="📊" value={`${percent}%`} label="Прогресс"
            bg="#dbeafe" border="#3b82f6" textColor="#1d4ed8" iconBg="#3b82f6"
            extra={
              <div className="space-y-1">
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#bfdbfe" }}>
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${percent}%`, backgroundColor: "#3b82f6" }} />
                </div>
                <div className="text-xs text-slate-500">{received} из {total}</div>
              </div>
            }
          />
        </div>

        {/* ── ТУЛБАР ── */}
        <div className="flex items-center gap-3 mb-3">
          {/* Поиск */}
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">🔍</span>
            <input
              type="text"
              placeholder="Поиск по отделам..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-9 py-2.5 rounded-xl border text-sm outline-none transition-colors"
              style={{
                borderColor: "#e2e8f0",
                backgroundColor: "white",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
              }}
            />
            {search && (
              <button
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-base"
                onClick={() => setSearch("")}
              >✕</button>
            )}
          </div>

          {/* Кнопки */}
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-white text-sm font-semibold shadow-sm hover:opacity-90 transition-opacity"
            style={{ backgroundColor: "#3b82f6" }}
            onClick={() => save(departments)}
          >
            💾 Сохранить
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-white text-sm font-semibold shadow-sm hover:opacity-90 transition-opacity"
            style={{ backgroundColor: "#10b981" }}
            onClick={() => setShowExport(true)}
          >
            📤 Экспорт
          </button>
          <button
            className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-500 hover:text-slate-700 transition-colors"
            style={{ backgroundColor: "#e2e8f0" }}
            title="Сбросить все статусы"
            onClick={() => setShowReset(true)}
          >
            🔄
          </button>
        </div>

        {/* ── ЛЕГЕНДА ── */}
        <div className="flex items-center gap-5 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#22c55e" }} />
            <span className="text-sm font-semibold text-slate-700">Получено</span>
            <span className="text-sm text-slate-500">— документы поступили</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#f59e0b" }} />
            <span className="text-sm font-semibold text-slate-700">В работе</span>
            <span className="text-sm text-slate-500">— на рассмотрении</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#94a3b8" }} />
            <span className="text-sm font-semibold text-slate-700">Не получено</span>
          </div>
          <span className="ml-auto text-xs italic text-slate-400">Клик по статусу — переключить</span>
        </div>

        {/* ── ТАБЛИЦА ── */}
        <div className="rounded-xl overflow-hidden border shadow-sm" style={{ borderColor: "#e2e8f0" }}>
          {/* Заголовок */}
          <div
            className="grid text-white text-xs font-bold uppercase tracking-wide px-5 py-3.5"
            style={{
              gridTemplateColumns: "56px 1fr 180px",
              background: "linear-gradient(135deg,#1e293b,#334155)",
            }}
          >
            <div className="text-center">№</div>
            <div className="pl-2">Следственный отдел</div>
            <div className="text-center">Статус</div>
          </div>

          {/* Строки */}
          <div className="bg-white divide-y divide-slate-200" style={{ maxHeight: "480px", overflowY: "auto" }}>
            {filtered.map((dept, idx) => {
              const isFirstOvd = dept.isOvd && idx > 0 && !filtered[idx - 1]?.isOvd;
              return (
                <div key={dept.id}>
                  {isFirstOvd && <div className="h-0.5" style={{ backgroundColor: "#e2e8f0" }} />}
                  <DeptRow dept={dept} idx={idx} onStatusClick={() => handleStatusClick(dept.id)} />
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="text-center py-12 text-slate-400 text-sm">
                Ничего не найдено по запросу «{search}»
              </div>
            )}
          </div>

          {/* Подвал */}
          <div className="text-center py-3 text-xs" style={{ color: "#94a3b8", backgroundColor: "white", borderTop: "1px solid #e2e8f0" }}>
            Данные сохраняются автоматически · 29 отделов
          </div>
        </div>
      </main>

      {/* ── МОДАЛЬНЫЕ ОКНА ── */}
      <ExportModal open={showExport} onClose={() => setShowExport(false)} departments={departments} />
      <ResetModal open={showReset} onClose={() => setShowReset(false)} onConfirm={handleReset} />

      {/* ── TOAST ── */}
      <Toast message={toast.message} visible={toast.visible} />

      {/* ── СТИЛИ ── */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spinning { animation: spin 2s linear infinite; display: inline-block; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
      `}</style>
    </div>
  );
}

// ─────────────────────────────────────────────
// СТРОКА ТАБЛИЦЫ
// ─────────────────────────────────────────────
function DeptRow({ dept, idx, onStatusClick }: {
  dept: Department; idx: number; onStatusClick: () => void;
}) {
  const [hov, setHov] = useState(false);
  const evenBg = idx % 2 === 0 ? "white" : "#f8faf0";
  const bg = hov ? "#eff6ff" : evenBg;

  return (
    <div
      className="grid items-center px-5 py-1 transition-colors duration-100"
      style={{ gridTemplateColumns: "56px 1fr 180px", backgroundColor: bg, minHeight: "52px" }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {/* Номер */}
      <div className="flex justify-center">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
          style={{
            backgroundColor: dept.isOvd ? "#cbd5e1" : "#1e293b",
            color: dept.isOvd ? "#64748b" : "white",
          }}
        >
          {dept.isOvd ? "—" : dept.id}
        </div>
      </div>

      {/* Название */}
      <div
        className="pl-2 pr-3 text-sm font-medium truncate"
        style={{
          color: dept.isOvd ? "#64748b" : "#334155",
          fontStyle: dept.isOvd ? "italic" : "normal",
          fontWeight: dept.isOvd ? 400 : 500,
        }}
        title={dept.name}
      >
        {dept.name}
      </div>

      {/* Статус */}
      <div className="py-1">
        <StatusCell dept={dept} onClick={onStatusClick} />
      </div>
    </div>
  );
}
