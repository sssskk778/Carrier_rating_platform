"""
Сервис управления датасетами.
Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from pathlib import Path
from flask import current_app
from src import db
from src.repositories import DatasetRepository

MAX_FILE_SIZE = 10 * 1024 * 1024


class DatasetService:
    """
    Управление датасетами: валидация, импорт из Excel, удаление.
    Атрибуты:
        repo — репозиторий датасетов.
    Методы:
        validate_file         — проверка файла перед загрузкой (тип, размер).
        import_from_file      — полный цикл импорта: предобработка + запись в БД.
        delete_dataset        — удаление датасета и файла с диска.
        format_preprocess_report — форматирование отчёта предобработки.
    """

    def __init__(self):
        self.repo = DatasetRepository()

    def validate_file(self, file_storage) -> None:
        if not file_storage or not file_storage.filename:
            raise ValueError('Файл не передан')
        if not file_storage.filename.endswith(('.xlsx', '.xls')):
            raise ValueError('Поддерживаются только файлы .xlsx и .xls')
        file_storage.seek(0, 2)
        size = file_storage.tell()
        file_storage.seek(0)
        if size == 0:
            raise ValueError('Файл не может быть пустым')
        if size > MAX_FILE_SIZE:
            raise ValueError('Файл не должен превышать 10 МБ')

    def import_from_file(self, file_path: str, name: str, description: str = '', skip_preprocess: bool = False) -> dict:
        from src.services.data.excel_preprocessor import ExcelPreprocessor
        from src.services.data.excel_importer import ExcelImporter

        path = Path(file_path)
        importer = ExcelImporter()
        preprocess_report = None

        try:
            if skip_preprocess:
                import pandas as pd
                df_carriers  = pd.read_excel(file_path, sheet_name=0)
                df_shipments = pd.read_excel(file_path, sheet_name=1)
                dataset = importer.import_from_dataframes(
                    df_carriers=df_carriers,
                    df_shipments=df_shipments,
                    file_name=path.name,
                    name=name,
                    description=description,
                )
            else:
                preprocessor = ExcelPreprocessor()
                cleaned_data = preprocessor.process(file_path)
                preprocess_report = preprocessor.get_report()

                if cleaned_data['carriers'].empty and cleaned_data['shipments'].empty:
                    raise ValueError('Нет валидных данных для импорта после предобработки')

                dataset = importer.import_from_dataframes(
                    df_carriers=cleaned_data['carriers'],
                    df_shipments=cleaned_data['shipments'],
                    file_name=path.name,
                    name=name,
                    description=description,
                )

            if path.exists():
                path.unlink()

            result = {
                'dataset_id':       dataset.id,
                'skipped_shipments': importer.stats.get('skipped_shipments', 0),
            }
            if preprocess_report:
                result['preprocess'] = self.format_preprocess_report(preprocess_report)

            return result

        except Exception:
            db.session.rollback()
            if path.exists():
                path.unlink()
            raise

    def delete_dataset(self, dataset_id: int) -> None:
        ds = self.repo.get_by_id(dataset_id)
        if not ds:
            raise ValueError(f'Датасет {dataset_id} не найден')
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if upload_folder and ds.file_name:
            file_path = Path(upload_folder) / ds.file_name
            if file_path.exists():
                file_path.unlink()
        self.repo.delete(ds)
        db.session.commit()

    def format_preprocess_report(self, report: dict) -> dict:
        stats = report['stats']
        return {
            'total_carriers':      stats['total_carriers'],
            'valid_carriers':      stats['valid_carriers'],
            'empty_carriers':      stats.get('empty_carriers', 0),
            'total_shipments':     stats['total_shipments'],
            'valid_shipments':     stats['valid_shipments'],
            'empty_shipments':     stats.get('empty_shipments', 0),
            'total_errors':        report['total_errors'],
            'errors':              report['errors'][:20],
            'duplicate_carriers':  stats.get('duplicate_carrier_ids', 0),
            'duplicate_shipments': stats.get('duplicate_shipment_ids', 0),
        }