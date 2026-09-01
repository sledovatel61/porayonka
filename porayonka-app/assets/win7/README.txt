api-ms-win-core-path-l1-1-0.dll — стаб для запуска Python 3.9+ на Windows 7
===========================================================================

Раунд 37 (задача 2). Ошибка на Windows 7:

    «Запуск программы невозможен, отсутствует
     api-ms-win-core-path-l1-1-0.dll»
    «Failed to load Python DLL ...\python311.dll:
     LoadLibrary: Не найден указанный модуль»

Причина: python311.dll импортирует функцию PathCchCanonicalizeEx из
api-ms-win-core-path-l1-1-0.dll, которой в Windows 7 нет (появилась в
Windows 8). Поэтому Python 3.9+ (в т.ч. 3.11) на «чистой» Windows 7 не
запускается.

Файл в этой папке — стаб проекта nalexandru/api-ms-win-core-path-HACK
(реализация API на базе Wine, MIT):
архив api-ms-win-core-path-blender-0.3.1.zip, ВНУТРИ архива — вложенная
папка api-ms-win-core-path-blender\x64\ (именно она, не просто x64\).

Источник (build-скрипты скачивают автоматически и кэшируют сюда):
https://github.com/nalexandru/api-ms-win-core-path-HACK/releases/download/0.3.1/api-ms-win-core-path-blender-0.3.1.zip

Контроль подлинности (build-скрипты проверяют перед копированием; без
валидного файла сборка web-дистрибутивов ОСТАНАВЛИВАЕТСЯ):
SHA256 архива:  2CFF5E3DC3B0A5E9241C1091230959CDED50E3D2FF543308B68C6FBA653A3BB6
SHA256 DLL x64: A1F02F8F2B90F89D0BFAE554D2EBD61D07C7454EABBC53236738143180E030CE

Куда уходит при сборке web-дистрибутивов Win7 (Пользователь/Админ):
1. ВНУТРЬ бандла — spec-файлы кладут DLL в корень _MEIPASS, рядом с
   python311.dll (datas: "assets/win7/api-ms-win-core-path-l1-1-0.dll" -> ".");
2. рядом с exe в dist (папка exe — первый каталог поиска зависимостей);
3. установщик Inno Setup копирует её в {app} (флаг skipifsourcedoesntexist).

Если файла здесь нет — сборка не падает, но exe под Windows 7 запуститься
не сможет; скачайте zip по ссылке выше и положите сюда файл из папки x64.
