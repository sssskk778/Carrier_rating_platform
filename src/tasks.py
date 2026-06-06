"""
Фоновые задачи Celery.
"""
import logging
from src.extensions import celery
from src.services.core.run_service import RunService
from src.services.data.dataset_service import DatasetService

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='tasks.run_scenario')
def run_scenario_task(self, scenario_id: int, user_id: int):
    logger.info('Запуск расчёта сценария %s пользователем %s', scenario_id, user_id)
    try:
        run = RunService().execute(scenario_id, user_id)
        logger.info('Расчёт сценария %s завершён, run_id=%s', scenario_id, run.id)
        return {'run_id': run.id, 'status': run.status}
    except Exception:
        logger.exception('Ошибка расчёта сценария %s', scenario_id)
        raise


@celery.task(bind=True, name='tasks.import_dataset')
def import_dataset_task(self, file_path: str, name: str, description: str = '', skip_preprocess: bool = False):
    logger.info('Импорт файла %s', file_path)
    try:
        return DatasetService().import_from_file(file_path, name, description, skip_preprocess)
    except Exception:
        logger.exception('Ошибка импорта файла %s', file_path)
        raise