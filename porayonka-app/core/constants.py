# [DARK THEME] Обновлено только визуально, логика сохранена.
# core/constants.py
# Константы: цвета, шрифты, список всех 29 отделов

# ────────────────────────────────────────────────
# ЦВЕТОВАЯ ПАЛИТРА (MODERN DARK MODE)
# ────────────────────────────────────────────────
COLORS = {
    # Фоны и поверхности
    "primary":        "#0f172a",
    "primary_dark":   "#020617",
    "primary_light":  "#1e293b",
    "bg":             "#0b1120",
    "card":           "#15202e",
    "card_hover":     "#1e293b",
    "border":         "#334155",
    "divider":        "#1e293b",

    # Текст
    "text":           "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted":     "#64748b",
    "text_light":     "#ffffff",

    # Статусы
    "received":       "#22c55e",
    "received_bg":    "#052e16",
    "received_hover": "#14532d",
    "received_text":  "#4ade80",

    "in_progress":       "#f59e0b",
    "in_progress_bg":    "#451a03",
    "in_progress_hover": "#78350f",
    "in_progress_text":  "#fbbf24",

    "empty":       "#64748b",
    "empty_bg":    "#1e293b",
    "empty_hover": "#334155",

    # Кнопки и акценты
    "btn_save":       "#3b82f6",
    "btn_save_hover": "#2563eb",
    "btn_export":     "#10b981",
    "btn_reset":      "#475569",

    # Статистика
    "stat_received_bg":     "#052e16",
    "stat_received_border": "#22c55e",
    "stat_progress_bg":     "#451a03",
    "stat_progress_border": "#f59e0b",
    "stat_empty_bg":        "#1e293b",
    "stat_empty_border":    "#64748b",
    "stat_blue_bg":         "#172554",
    "stat_blue_border":     "#3b82f6",
    "stat_blue_text":       "#60a5fa",

    # Прочее
    "row_alt":       "#0f172a",
    "row_hover":     "#1e293b",
    "toast_bg":      "#1e293b",
    "modal_overlay": "rgba(0,0,0,0.6)",
}

# ────────────────────────────────────────────────
# СПИСОК ВСЕХ 29 СЛЕДСТВЕННЫХ ОТДЕЛОВ
# ────────────────────────────────────────────────
INITIAL_DEPARTMENTS = [
    {"id": 1,  "name": "СО по г. Азов",                                          "is_ovd": False},
    {"id": 2,  "name": "СО по Аксайскому району",                                "is_ovd": False},
    {"id": 3,  "name": "СО по г. Батайск",                                       "is_ovd": False},
    {"id": 4,  "name": "Белокалитвинский МСО",                                   "is_ovd": False},
    {"id": 5,  "name": "СО по г. Волгодонск",                                    "is_ovd": False},
    {"id": 6,  "name": "Зерноградский МСО",                                      "is_ovd": False},
    {"id": 7,  "name": "СО по г. Донецк",                                        "is_ovd": False},
    {"id": 8,  "name": "Зимовниковский МСО",                                     "is_ovd": False},
    {"id": 9,  "name": "СО по г. Красный Сулин",                                 "is_ovd": False},
    {"id": 10, "name": "Миллеровский МСО",                                       "is_ovd": False},
    {"id": 11, "name": "Морозовский МСО",                                        "is_ovd": False},
    {"id": 12, "name": "Неклиновский МСО",                                       "is_ovd": False},
    {"id": 13, "name": "СО по г. Новочеркасск",                                  "is_ovd": False},
    {"id": 14, "name": "СО по г. Новошахтинск",                                  "is_ovd": False},
    {"id": 15, "name": "Сальский МСО",                                           "is_ovd": False},
    {"id": 16, "name": "Семикаракорский МСО",                                    "is_ovd": False},
    {"id": 17, "name": "Шолоховский МСО",                                        "is_ovd": False},
    {"id": 18, "name": "СО по г. Таганрог",                                      "is_ovd": False},
    {"id": 19, "name": "СО по г. Шахты",                                         "is_ovd": False},
    {"id": 20, "name": "СО по Ворошиловскому району г. Ростов-на-Дону",          "is_ovd": False},
    {"id": 21, "name": "СО по Железнодорожному району г. Ростов-на-Дону",        "is_ovd": False},
    {"id": 22, "name": "СО по Кировскому району г. Ростов-на-Дону",              "is_ovd": False},
    {"id": 23, "name": "СО по Ленинскому району г. Ростов-на-Дону",              "is_ovd": False},
    {"id": 24, "name": "СО по Октябрьскому району г. Ростов-на-Дону",            "is_ovd": False},
    {"id": 25, "name": "СО по Первомайскому району г. Ростов-на-Дону",           "is_ovd": False},
    {"id": 26, "name": "СО по Пролетарскому району г. Ростов-на-Дону",           "is_ovd": False},
    {"id": 27, "name": "Советский МСО",                                          "is_ovd": False},
    {"id": 28, "name": "ОВД-1",                                                  "is_ovd": True},
    {"id": 29, "name": "ОВД-2",                                                  "is_ovd": True},
]

TOTAL_DEPARTMENTS = len(INITIAL_DEPARTMENTS)  # 29

APP_TITLE    = "Порайонка"
APP_SUBTITLE = "Следственный комитет РФ · Ростовская область"
APP_VERSION  = "1.0"