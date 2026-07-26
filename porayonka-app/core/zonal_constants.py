# core/zonal_constants.py
# Список 16 зональных криминалистов с зонами обслуживания по умолчанию
# Зоны соответствуют ID отделов из core/constants.py INITIAL_DEPARTMENTS

from .zonal_models import Criminalist, CriminalistZone

# ID отделов из INITIAL_DEPARTMENTS:
# 1=СО г.Азов, 2=Аксайский, 3=г.Батайск, 4=Белокалитвинский,
# 5=г.Волгодонск, 6=Зерноградский, 7=г.Донецк, 8=Зимовниковский,
# 9=г.КрасныйСулин, 10=Миллеровский, 11=Морозовский,
# 12=Неклиновский, 13=г.Новочеркасск, 14=г.Новошахтинск,
# 15=Сальский, 16=Семикаракорский, 17=Шолоховский,
# 18=г.Таганрог, 19=г.Шахты, 20=Ворошиловский,
# 21=Железнодорожный, 22=Кировский, 23=Ленинский,
# 24=Октябрьский, 25=Первомайский, 26=Пролетарский,
# 27=Советский, 28=ОВД-1, 29=ОВД-2

INITIAL_CRIMINALISTS_DATA = [
    {
        "id": 1,
        "full_name": "Агеев Олег Владимирович",
        "note": "",
        "is_active": True,
        # СО по г. Таганрог (8 дел), Неклиновский МСО (5 дел)
        "department_ids": [18, 12],
    },
    {
        "id": 2,
        "full_name": "Грубников Георгий Григорьевич",
        "note": "",
        "is_active": True,
        # СО по г. Новочеркасск (6 дел), СО по г. Шахты (8 дел)
        "department_ids": [13, 19],
    },
    {
        "id": 3,
        "full_name": "Белашов Николай Сергеевич",
        "note": "",
        "is_active": True,
        # СО по г. Азов (5 дел), СО по г. Батайск (4 дела)
        "department_ids": [1, 3],
    },
    {
        "id": 4,
        "full_name": "Эксузян Артур Мигранович",
        "note": "",
        "is_active": True,
        # СО по Первомайскому р-ну (6), СО по Железнодорожному р-ну (5),
        # СО по г. Новочеркасск (7)
        "department_ids": [25, 21, 13],
    },
    {
        "id": 5,
        "full_name": "Авакян Арсен Артурович",
        "note": "",
        "is_active": True,
        # СО по Ворошиловскому р-ну (6), СО по Пролетарскому р-ну (4),
        # Семикаракорский МСО (7)
        "department_ids": [20, 26, 16],
    },
    {
        "id": 6,
        "full_name": "Кудрявцев Василий Александрович",
        "note": "",
        "is_active": True,
        # СО по Октябрьскому р-ну (5), Советский МСО (6),
        # СО по Кировскому р-ну (4)
        "department_ids": [24, 27, 22],
    },
    {
        "id": 7,
        "full_name": "Терновой Иван Александрович",
        "note": "",
        "is_active": True,
        # Миллеровский МСО (5), Шолоховский МСО (3), Морозовский МСО (3)
        "department_ids": [10, 17, 11],
    },
    {
        "id": 8,
        "full_name": "Семишин Дмитрий Николаевич",
        "note": "",
        "is_active": True,
        # СО по Аксайскому р-ну (5), СО по Ленинскому р-ну (4)
        "department_ids": [2, 23],
    },
    {
        "id": 9,
        "full_name": "Сулейманов Эльдар Мирзаевич",
        "note": "",
        "is_active": True,
        # СО по г. Волгодонск (10), Зимовниковский МСО (6)
        "department_ids": [5, 8],
    },
    {
        "id": 10,
        "full_name": "Ливенский Вадим Олегович",
        "note": "",
        "is_active": True,
        # Сальский МСО (7), Зерноградский МСО (6)
        "department_ids": [15, 6],
    },
    {
        "id": 11,
        "full_name": "Свеженко Александр Сергеевич",
        "note": "",
        "is_active": True,
        # СО по г. Красный Сулин (7), СО по г. Донецк (7),
        # Белокалитвинский МСО (4)
        "department_ids": [9, 7, 4],
    },
    {
        "id": 12,
        "full_name": "Бережной Кирилл Николаевич",
        "note": "Цифровая криминалистика",
        "is_active": True,
        "department_ids": [],
    },
    {
        "id": 13,
        "full_name": "Чашин Эдуард Александрович",
        "note": "ОВД-1, ОВД-2",
        "is_active": True,
        # ОВД-1 (13 дел), ОВД-2 (16 дел)
        "department_ids": [28, 29],
    },
    {
        "id": 14,
        "full_name": "Гайнутдинов Станислав Игоревич",
        "note": "аналитика + зона №6",
        "is_active": True,
        "department_ids": [],
    },
    {
        "id": 15,
        "full_name": "Семисенко Иван Юрьевич",
        "note": "аналитика, ОВД-1, ОВД-2",
        "is_active": True,
        # ОВД-1 (13), ОВД-2 (16)
        "department_ids": [28, 29],
    },
    {
        "id": 16,
        "full_name": "Миронович Дмитрий Владимирович",
        "note": "Цифровая криминалистика",
        "is_active": True,
        "department_ids": [],
    },
]


def get_initial_criminalists() -> list:
    """Вернуть список из 16 криминалистов с зонами по умолчанию"""
    result = []
    for data in INITIAL_CRIMINALISTS_DATA:
        zone = CriminalistZone(
            criminalist_id=data["id"],
            department_ids=list(data["department_ids"]),
        )
        criminalist = Criminalist(
            id=data["id"],
            full_name=data["full_name"],
            note=data["note"],
            is_active=data.get("is_active", True),
            zone=zone,
        )
        result.append(criminalist)
    print(f"[ZONAL_CONST] Criminalists loaded: {len(result)}")
    return result