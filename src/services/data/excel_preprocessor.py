"""
Предобработка Excel-файлов перед импортом.
Валидация и очистка данных о перевозчиках и рейсах.
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional


class ExcelPreprocessor:

    ALLOWED_VALUES = {
        'Тип автопарка':         ['самосвалы', 'бортовые', 'все типы', 'рефрижераторы'],
        'Регион':                ['Центральный', 'Северо-Западный', 'Южный', 'Приволжский',
                                  'Уральский', 'Сибирский', 'Дальневосточный'],
        'Статус рейса':          ['Доставлено', 'Отменено'],
        'Тяжесть ДТП':           ['Нет', 'Легкое', 'Среднее', 'Тяжелое'],
        'Вина перевозчика в ДТП': ['Да', 'Нет'],
        'Тип претензии':         ['Нет', 'Повреждение', 'Потеря'],
        'Был GPS':               ['Да', 'Нет'],
        'Наличие POD':           ['Да', 'Нет'],
        'Оценка клиента':        ['Нет', '1', '2', '3', '4', '5'],
    }

    CARRIERS_COLUMNS = ['ID перевозчика', 'Название', 'Тип автопарка', 'Регион']

    SHIPMENTS_COLUMNS = [
        'ID рейса', 'ID перевозчика', 'Начало погрузки', 'Планируемое время доставки',
        'Фактическое время доставки', 'Оценка клиента', 'Цена', 'Расстояние км',
        'Статус рейса', 'Был GPS', 'Тяжесть ДТП', 'Вина перевозчика в ДТП',
        'Тип претензии', 'Наличие POD',
    ]

    def __init__(self):
        self.errors: List[Tuple[str, int, str, str]] = []
        self.stats = {
            'total_carriers': 0, 'valid_carriers': 0, 'empty_carriers': 0,
            'total_shipments': 0, 'valid_shipments': 0, 'empty_shipments': 0,
            'duplicate_carrier_ids': 0, 'duplicate_shipment_ids': 0,
        }

    def process(self, file_path: str) -> Dict[str, pd.DataFrame]:
        df_carriers  = pd.read_excel(file_path, sheet_name=0)
        df_shipments = pd.read_excel(file_path, sheet_name=1)

        df_carriers_clean = self._validate_carriers(df_carriers)

        valid_carrier_ids = {
            self._parse_int(row.get('ID перевозчика'))
            for _, row in df_carriers_clean.iterrows()
            if self._parse_int(row.get('ID перевозчика'))
        } if not df_carriers_clean.empty else set()

        df_shipments_clean = self._validate_shipments(df_shipments, valid_carrier_ids)
        return {'carriers': df_carriers_clean, 'shipments': df_shipments_clean}

    def get_report(self) -> Dict[str, Any]:
        return {'stats': self.stats, 'errors': self.errors[:100], 'total_errors': len(self.errors)}

    def _is_empty(self, val: Any) -> bool:
        if val is None or pd.isna(val):
            return True
        return str(val).strip() in ('', 'nan')

    def _parse_datetime(self, val: Any) -> Optional[datetime]:
        if self._is_empty(val):
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        val_str = str(val).strip()
        for fmt in ('%d.%m.%Y %H:%M', '%d.%m.%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue
        return None

    def _parse_int(self, val: Any) -> Optional[int]:
        if self._is_empty(val):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _parse_float(self, val: Any) -> Optional[float]:
        if self._is_empty(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _validate_carriers(self, df: pd.DataFrame) -> pd.DataFrame:
        self.stats['total_carriers'] = len(df)
        valid_rows, seen_ids = [], set()

        for idx, row in df.iterrows():
            row_num, sheet, is_valid = idx + 2, 'carriers', True

            empty_fields = [c for c in self.CARRIERS_COLUMNS if c in row.index and self._is_empty(row[c])]
            if empty_fields:
                self.errors.append((sheet, row_num, ', '.join(empty_fields), 'Пустые поля - строка удалена'))
                self.stats['empty_carriers'] += 1
                continue

            carrier_id = self._parse_int(row.get('ID перевозчика'))
            if not carrier_id or carrier_id <= 0:
                self.errors.append((sheet, row_num, 'ID перевозчика', 'Должен быть > 0'))
                is_valid = False
            elif carrier_id in seen_ids:
                self.errors.append((sheet, row_num, 'ID перевозчика', f'Дубликат ID {carrier_id}'))
                self.stats['duplicate_carrier_ids'] += 1
                is_valid = False
            else:
                seen_ids.add(carrier_id)

            name = str(row.get('Название', '')).strip()
            if len(name) < 2:
                self.errors.append((sheet, row_num, 'Название', 'Минимум 2 символа'))
                is_valid = False

            fleet = str(row.get('Тип автопарка', '')).strip()
            if fleet not in self.ALLOWED_VALUES['Тип автопарка']:
                self.errors.append((sheet, row_num, 'Тип автопарка',
                                    f'Должен быть: {", ".join(self.ALLOWED_VALUES["Тип автопарка"])}'))
                is_valid = False

            region = str(row.get('Регион', '')).strip()
            if region not in self.ALLOWED_VALUES['Регион']:
                self.errors.append((sheet, row_num, 'Регион',
                                    f'Должен быть: {", ".join(self.ALLOWED_VALUES["Регион"])}'))
                is_valid = False

            if is_valid:
                valid_rows.append(row)
                self.stats['valid_carriers'] += 1

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=self.CARRIERS_COLUMNS)

    def _validate_shipments(self, df: pd.DataFrame, valid_carrier_ids: set) -> pd.DataFrame:
        self.stats['total_shipments'] = len(df)
        valid_rows, seen_ids = [], set()

        for idx, row in df.iterrows():
            row_num, sheet, is_valid = idx + 2, 'shipments', True

            status = str(row.get('Статус рейса', '')).strip()
            if status not in self.ALLOWED_VALUES['Статус рейса']:
                self.errors.append((sheet, row_num, 'Статус рейса', 'Неверный статус'))
                continue

            is_delivered = status == 'Доставлено'

            empty_fields = [
                col for col in self.SHIPMENTS_COLUMNS
                if not (col == 'Фактическое время доставки' and not is_delivered)
                and col in row.index and self._is_empty(row[col])
            ]
            if empty_fields:
                self.errors.append((sheet, row_num, ', '.join(empty_fields[:3]),
                                    f'Пустые поля ({len(empty_fields)})'))
                self.stats['empty_shipments'] += 1
                continue

            shipment_id = self._parse_int(row.get('ID рейса'))
            if not shipment_id or shipment_id <= 0:
                self.errors.append((sheet, row_num, 'ID рейса', 'Должен быть > 0'))
                is_valid = False
            elif shipment_id in seen_ids:
                self.errors.append((sheet, row_num, 'ID рейса', f'Дубликат {shipment_id}'))
                self.stats['duplicate_shipment_ids'] += 1
                is_valid = False
            else:
                seen_ids.add(shipment_id)

            carrier_id = self._parse_int(row.get('ID перевозчика'))
            if not carrier_id:
                self.errors.append((sheet, row_num, 'ID перевозчика', 'Должен быть целым числом'))
                is_valid = False
            elif carrier_id not in valid_carrier_ids:
                self.errors.append((sheet, row_num, 'ID перевозчика', f'Перевозчик {carrier_id} не найден'))
                is_valid = False

            pickup  = self._parse_datetime(row.get('Начало погрузки'))
            planned = self._parse_datetime(row.get('Планируемое время доставки'))

            if not pickup:
                self.errors.append((sheet, row_num, 'Начало погрузки', 'Неверный формат даты'))
                is_valid = False
            elif pickup > datetime.now():
                self.errors.append((sheet, row_num, 'Начало погрузки', 'Не может быть в будущем'))
                is_valid = False

            if not planned:
                self.errors.append((sheet, row_num, 'Планируемое время доставки', 'Неверный формат даты'))
                is_valid = False
            elif pickup and planned < pickup:
                self.errors.append((sheet, row_num, 'Планируемое время доставки', 'Раньше начала погрузки'))
                is_valid = False

            delivery_raw = row.get('Фактическое время доставки')
            delivery_str = str(delivery_raw).strip() if delivery_raw is not None else ''
            delivery     = self._parse_datetime(delivery_raw)

            if is_delivered:
                if self._is_empty(delivery_raw):
                    self.errors.append((sheet, row_num, 'Фактическое время доставки', 'Должно быть заполнено'))
                    is_valid = False
                elif not delivery:
                    self.errors.append((sheet, row_num, 'Фактическое время доставки', 'Неверный формат даты'))
                    is_valid = False
                elif pickup and delivery < pickup:
                    self.errors.append((sheet, row_num, 'Фактическое время доставки', 'Раньше начала погрузки'))
                    is_valid = False
            elif delivery_str != 'Нет':
                self.errors.append((sheet, row_num, 'Фактическое время доставки',
                                    f'Должно быть "Нет" для "{status}"'))
                is_valid = False

            rating_raw = row.get('Оценка клиента')
            rating_str = str(rating_raw).strip() if rating_raw is not None else ''
            rating     = self._parse_int(rating_raw)

            if is_delivered:
                if not rating or rating < 1 or rating > 5:
                    self.errors.append((sheet, row_num, 'Оценка клиента', 'Должна быть 1-5'))
                    is_valid = False
            elif rating_str != 'Нет':
                self.errors.append((sheet, row_num, 'Оценка клиента',
                                    f'Должна быть "Нет" для "{status}"'))
                is_valid = False

            price = self._parse_float(row.get('Цена'))
            if not price or price <= 0:
                self.errors.append((sheet, row_num, 'Цена', 'Должна быть > 0'))
                is_valid = False

            dist = self._parse_float(row.get('Расстояние км'))
            if not dist or dist <= 0:
                self.errors.append((sheet, row_num, 'Расстояние км', 'Должно быть > 0'))
                is_valid = False

            gps = str(row.get('Был GPS', '')).strip()
            if gps not in ('Да', 'Нет'):
                self.errors.append((sheet, row_num, 'Был GPS', 'Должен быть "Да" или "Нет"'))
                is_valid = False
            elif not is_delivered and gps == 'Да':
                self.errors.append((sheet, row_num, 'Был GPS', f'Должен быть "Нет" для "{status}"'))
                is_valid = False

            sev = str(row.get('Тяжесть ДТП', '')).strip()
            if is_delivered:
                if sev not in self.ALLOWED_VALUES['Тяжесть ДТП']:
                    self.errors.append((sheet, row_num, 'Тяжесть ДТП',
                                        f'Должен быть: {", ".join(self.ALLOWED_VALUES["Тяжесть ДТП"])}'))
                    is_valid = False
            elif sev != 'Нет':
                self.errors.append((sheet, row_num, 'Тяжесть ДТП', f'Должна быть "Нет" для "{status}"'))
                is_valid = False

            fault = str(row.get('Вина перевозчика в ДТП', '')).strip()
            if is_delivered:
                if fault not in ('Да', 'Нет'):
                    self.errors.append((sheet, row_num, 'Вина перевозчика в ДТП', 'Должна быть "Да" или "Нет"'))
                    is_valid = False
            elif fault != 'Нет':
                self.errors.append((sheet, row_num, 'Вина перевозчика в ДТП',
                                    f'Должна быть "Нет" для "{status}"'))
                is_valid = False

            claim = str(row.get('Тип претензии', '')).strip()
            if is_delivered:
                if claim not in self.ALLOWED_VALUES['Тип претензии']:
                    self.errors.append((sheet, row_num, 'Тип претензии',
                                        f'Должен быть: {", ".join(self.ALLOWED_VALUES["Тип претензии"])}'))
                    is_valid = False
            elif claim != 'Нет':
                self.errors.append((sheet, row_num, 'Тип претензии', f'Должен быть "Нет" для "{status}"'))
                is_valid = False

            pod = str(row.get('Наличие POD', '')).strip()
            if is_delivered:
                if pod not in ('Да', 'Нет'):
                    self.errors.append((sheet, row_num, 'Наличие POD', 'Должен быть "Да" или "Нет"'))
                    is_valid = False
            elif pod != 'Нет':
                self.errors.append((sheet, row_num, 'Наличие POD', f'Должен быть "Нет" для "{status}"'))
                is_valid = False

            if is_valid:
                valid_rows.append(row)
                self.stats['valid_shipments'] += 1

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=self.SHIPMENTS_COLUMNS)