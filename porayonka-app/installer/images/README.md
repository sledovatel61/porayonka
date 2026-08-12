# Графика установщиков «Порайонка»

Единый комплект в тёмной палитре приложения. Основной знак сохраняет мотив
исходной иконки `assets/icon.png` — линзу с диагональной ручкой — и различает
редакции цветным бейджем. Боковая панель и малый логотип мастера продолжают
тот же картографический стиль.

| Редакция | PNG 1024×1024 | ICO (8 размеров) | Бейдж |
|---|---|---|---|
| Общая / fallback | `icon.png` | `icon.ico` | без бейджа |
| Администратор | `icon_admin.png` | `icon_admin.ico` | фиолетовый щит |
| Пользователь | `icon_user.png` | `icon_user.ico` | зелёный профиль |
| User Web (Windows 7) | `icon_user_web.png` | `icon_user_web.ico` | голубой глобус |

Дополнительные материалы мастера:

| Файл | Размер | Назначение |
|---|---:|---|
| `wizard_image.png` | 164×314 | Боковая панель классического мастера Inno Setup |
| `wizard_small_image.png` | 55×55 | Логотип справа в заголовке мастера |
| `icons_preview.png` | 1800×780 | Обзор иконок и проверка малых размеров |
| `installer_artwork_preview.png` | 1800×1400 | Общий лист и mockup мастера |

## Подключение в Inno Setup

В соответствующем `.iss` используйте отдельную иконку редакции:

```ini
; Общие параметры всех трёх установщиков
WizardImageFile=images\wizard_image.png
WizardSmallImageFile=images\wizard_small_image.png

; Admin.iss
SetupIconFile=images\icon_admin.ico

; User.iss
SetupIconFile=images\icon_user.ico

; UserWeb.iss
SetupIconFile=images\icon_user_web.ico
```

`icon.ico` оставлен как универсальный вариант для общих ярлыков и обратной
совместимости с планируемой структурой из `PROMPT_установщик_inno_setup.md`.

Каждый ICO содержит настоящие RGBA-кадры 16, 24, 32, 48, 64, 96, 128 и
256 px. Это даёт чёткий вид в заголовке мастера, Проводнике, меню «Пуск» и
списке установленных приложений Windows 7/10/11.

## Повторная генерация

Требуется Pillow (он уже устанавливается существующими build-скриптами):

```bat
python installer\images\generate_icons.py
```

Скрипт не меняет код приложения и перезаписывает только PNG/ICO-файлы в этой
папке.
