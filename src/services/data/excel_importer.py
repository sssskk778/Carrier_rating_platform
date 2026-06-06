"""
Импорт данных из Excel в базу данных.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from src import db
from src.models import Dataset, Carrier, Shipment


class ExcelImporter:

    def __init__(self):
        self.stats = {
            'carriers':         0,
            'carriers_updated': 0,
            'shipments':        0,
            'skipped_shipments': 0,
        }
        self.valid_carrier_ids: set = set()

    def import_from_dataframes(
        self,
        df_carriers: pd.DataFrame,
        df_shipments: pd.DataFrame,
        file_name: str,
        name: str = 'Dataset',
        description: str = '',
    ) -> Dataset:
        dataset = Dataset(name=name, file_name=file_name, description=description, records_count=0)
        db.session.add(dataset)
        db.session.flush()

        try:
            if not df_carriers.empty:
                self._import_carriers(df_carriers)
                db.session.flush()

            self.valid_carrier_ids = {
                self._safe_int(row.get('ID перевозчика'))
                for _, row in df_carriers.iterrows()
                if self._safe_int(row.get('ID перевозчика'))
            }

            if not df_shipments.empty:
                self._import_shipments(df_shipments, dataset.id)

            dataset.records_count = (
                self.stats['carriers'] - self.stats['carriers_updated']
                + self.stats['shipments']
            )
            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        return dataset

    def _import_carriers(self, df: pd.DataFrame) -> None:
        for _, row in df.iterrows():
            carrier_id = self._safe_int(row.get('ID перевозчика'))
            if not carrier_id:
                continue
            name       = self._safe_str(row.get('Название')) or ''
            fleet_type = self._safe_str(row.get('Тип автопарка'))
            region     = self._safe_str(row.get('Регион'))

            existing = db.session.get(Carrier, carrier_id)
            if existing:
                existing.company_name = name
                existing.fleet_type   = fleet_type
                existing.region       = region
                self.stats['carriers_updated'] += 1
            else:
                db.session.add(Carrier(
                    carrier_id=carrier_id,
                    company_name=name,
                    fleet_type=fleet_type,
                    region=region,
                ))
            self.stats['carriers'] += 1

    def _import_shipments(self, df: pd.DataFrame, dataset_id: int) -> None:
        for _, row in df.iterrows():
            shipment_id = self._safe_int(row.get('ID рейса'))
            carrier_id  = self._safe_int(row.get('ID перевозчика'))

            if not shipment_id or not carrier_id or carrier_id not in self.valid_carrier_ids:
                self.stats['skipped_shipments'] += 1
                continue

            if db.session.get(Shipment, shipment_id):
                self.stats['skipped_shipments'] += 1
                continue

            db.session.add(Shipment(
                shipment_id=shipment_id,
                dataset_id=dataset_id,
                carrier_id=carrier_id,
                pickup_window_start=self._safe_datetime(row.get('Начало погрузки')),
                delivery_window_end=self._safe_datetime(row.get('Планируемое время доставки')),
                actual_delivery_time=self._safe_datetime(row.get('Фактическое время доставки')),
                client_rating=self._safe_int(row.get('Оценка клиента')),
                price=self._safe_float(row.get('Цена')),
                distance_km=self._safe_float(row.get('Расстояние км')),
                status=self._safe_str(row.get('Статус рейса')),
                has_gps=self._safe_bool(row.get('Был GPS')),
                has_pod=self._safe_bool(row.get('Наличие POD')),
                accident_severity=self._safe_str(row.get('Тяжесть ДТП')),
                carrier_fault=self._safe_bool(row.get('Вина перевозчика в ДТП')),
                claim_type=self._safe_str(row.get('Тип претензии')),
            ))
            self.stats['shipments'] += 1

    def _safe_int(self, val: Any) -> Optional[int]:
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _safe_float(self, val: Any) -> Optional[float]:
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _safe_datetime(self, val: Any) -> Optional[datetime]:
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
        try:
            return pd.to_datetime(val).to_pydatetime()
        except Exception:
            return None

    def _safe_bool(self, val: Any) -> Optional[bool]:
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
            return None
        val_str = str(val).strip()
        if val_str in ('Да', 'да'):
            return True
        if val_str in ('Нет', 'нет'):
            return False
        return None

    def _safe_str(self, val: Any) -> Optional[str]:
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
            return None
        return str(val).strip()