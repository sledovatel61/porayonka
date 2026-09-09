# core/zonal_models.py
# Модели данных для вкладки "Зональные"
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict
import uuid


class ReportItemType(Enum):
    """Тип пункта отчёта"""
    NUMERICAL = "numerical"      # Числовой показатель
    DELIVERABLE = "deliverable"  # Факт сдачи (да/нет)


@dataclass
class ReportTemplateItem:
    """Пункт шаблона отчёта"""
    id: str                          # Уникальный ID (uuid)
    name: str                        # Название (например, "Выезды на ОМП")
    item_type: ReportItemType        # Тип: числовой или да/нет
    unit: str = ""                   # Единица измерения (для числовых)
    order: int = 0                   # Порядок отображения

    @staticmethod
    def create(name: str, item_type: ReportItemType, unit: str = "", order: int = 0) -> "ReportTemplateItem":
        """Фабричный метод для создания нового пункта"""
        return ReportTemplateItem(
            id=str(uuid.uuid4()),
            name=name,
            item_type=item_type,
            unit=unit,
            order=order,
        )


@dataclass
class ReportTemplate:
    """Шаблон сбора данных"""
    name: str                                           # Название формы
    items: List[ReportTemplateItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    use_departments_mode: bool = False                  # Режим работы по отделам


@dataclass
class CriminalistZone:
    """Зона обслуживания криминалиста"""
    criminalist_id: int
    department_ids: List[int] = field(default_factory=list)  # IDs отделов из constants.py


@dataclass
class Criminalist:
    """Зональный криминалист"""
    id: int
    full_name: str               # ФИО
    note: str = ""               # Примечание (например, "Цифровая криминалистика")
    is_active: bool = True       # Участвует в текущем сборе
    zone: CriminalistZone = field(default_factory=lambda: CriminalistZone(criminalist_id=0))
    # Фаза 40: взаимозаменяемость — неориентированные попарные связи по
    # стабильным числовым ID (НЕ по ФИО). Симметрия и целостность
    # поддерживаются core/zonal_replacement.py; здесь хранится плоский
    # детерминированно упорядоченный список партнёров текущего человека.
    replacement_ids: List[int] = field(default_factory=list)


@dataclass
class ReportData:
    """Данные отчёта для одного криминалиста по одному пункту"""
    criminalist_id: int
    template_item_id: str

    # Режим 1 (общие значения)
    value: Optional[int] = None          # Числовое значение
    is_submitted: bool = False           # Для DELIVERABLE
    comment: str = ""
    updated_at: Optional[datetime] = None

    # Режим 2 (по отделам)
    department_values: Dict[int, int] = field(default_factory=dict)      # dept_id → value
    department_submitted: Dict[int, bool] = field(default_factory=dict)  # dept_id → сдал/нет


@dataclass
class ZonalCollection:
    """Конкретный сбор данных (экземпляр шаблона)"""
    template: ReportTemplate
    submissions: List[ReportData] = field(default_factory=list)
    last_saved: Optional[datetime] = None
    criminalists: List[Criminalist] = field(default_factory=list)