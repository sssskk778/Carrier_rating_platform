"""
Модуль API маршрутов Carrier Rating Platform.

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import logging
from flask import Blueprint, jsonify, request, make_response, session
from src.utils.validators import validate_body
from src.decorators import login_required, admin_required, current_user
from src.schemas.schemas import (
    LoginSchema, RegisterSchema,
    ScenarioCreateSchema, ScenarioUpdateSchema,
    SwaraWeightsSchema, DatasetUploadSchema,
)
from src.schemas.serializers import (
    serialize_dataset, serialize_carrier,
    serialize_scenario, serialize_run,
    serialize_run_result, serialize_criterion,
)
from src.services.data.dataset_service import DatasetService
from src.services.core.export_service import ExportService
from src.services.core.scenario_service import ScenarioService
from src.services.core.task_service import TaskService
from src.services.core.auth_service import AuthService
from src.services.algorithms.swara import SwaraService
from src.repositories import (
    RunRepository, RunResultRepository,
    ScenarioRepository, CriterionRepository,
    CarrierRepository, DatasetRepository,
    ScenarioCriterionRepository,
)

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')
datasets = DatasetService()
export_svc = ExportService()
scenarios = ScenarioService()
task_svc = TaskService()
auth_svc = AuthService()
run_repo = RunRepository()
run_result_repo = RunResultRepository()
scenario_repo = ScenarioRepository()
criterion_repo = CriterionRepository()
scenario_criteria_repo = ScenarioCriterionRepository()
carrier_repo = CarrierRepository()
dataset_repo = DatasetRepository()


def success(data=None, status=200):
    return jsonify({'ok': True, 'data': data}), status


def error(message, status=400):
    return jsonify({'ok': False, 'error': message}), status

@api_bp.post('/auth/login')
@validate_body(LoginSchema)
def login_post(data):
    """
    Авторизация пользователя
    ---
    responses:
      200:
        description: Успешная авторизация
      401:
        description: Неверный логин или пароль
    """
    try:
        user = auth_svc.login(data['username'], data['password'])
    except ValueError as e:
        return error(str(e), 401)
    session['user_id'] = user.id
    return success({'id': user.id, 'username': user.username, 'role': user.role})


@api_bp.post('/auth/register')
@validate_body(RegisterSchema)
def register_post(data):
    """
    Регистрация нового пользователя
    ---
    responses:
      201:
        description: Пользователь создан
      400:
        description: Логин уже занят
    """
    try:
        user = auth_svc.register(data['username'], data['password'], data['full_name'])
    except ValueError as e:
        return error(str(e), 400)
    session['user_id'] = user.id
    return success({'id': user.id, 'username': user.username, 'role': user.role}, 201)

@api_bp.get('/datasets')
@login_required
def dataset_list():
    """
    Список всех датасетов
    ---
    responses:
      200:
        description: Список датасетов
    """
    return success([serialize_dataset(d) for d in dataset_repo.get_all()])


@api_bp.post('/datasets/upload')
@login_required
@validate_body(DatasetUploadSchema)
def upload_dataset(data):
    """
    Загрузка Excel файла с данными
    ---
    responses:
      202:
        description: Задача импорта создана
      400:
        description: Ошибка валидации файла
    """
    file = request.files.get('file')
    try:
        datasets.validate_file(file)
    except ValueError as e:
        return error(str(e), 400)
    result = task_svc.start_import(
        file_storage=file,
        name=data.get('name') or file.filename,
        description=data.get('description', ''),
        skip_preprocess=data.get('skip_preprocess', False),
    )
    return success(result, 202)


@api_bp.delete('/datasets/<int:did>')
@login_required
def delete_dataset(did):
    """
    Удаление датасета
    ---
    responses:
      200:
        description: Датасет удалён
      404:
        description: Датасет не найден
    """
    try:
        datasets.delete_dataset(did)
    except ValueError as e:
        return error(str(e), 404)
    return success({'message': 'Датасет удален'})

@api_bp.get('/carriers')
@login_required
def carriers():
    """
    Список всех перевозчиков
    ---
    responses:
      200:
        description: Список перевозчиков
    """
    return success([serialize_carrier(c) for c in carrier_repo.get_all()])

@api_bp.get('/criteria')
@login_required
def criteria():
    """
    Список всех критериев оценки
    ---
    responses:
      200:
        description: Список критериев
    """
    return success([serialize_criterion(c) for c in criterion_repo.get_all()])

@api_bp.get('/scenarios/<int:sid>')
@login_required
def scenario_get(sid):
    """
    Получение сценария по ID
    ---
    responses:
      200:
        description: Данные сценария
      404:
        description: Сценарий не найден
    """
    s = scenario_repo.get_by_id(sid)
    if not s:
        return error(f'Сценарий {sid} не найден', 404)
    links = scenario_criteria_repo.get_by_scenario(s.id)
    criteria = criterion_repo.get_by_ids([l.criterion_id for l in links])
    return success({**serialize_scenario(s, criteria), 'swara_config': s.get_swara_config()})


@api_bp.post('/scenarios')
@admin_required
@validate_body(ScenarioCreateSchema)
def scenario_create(data):
    """
    Создание нового сценария
    ---
    responses:
      201:
        description: Сценарий создан
      400:
        description: Ошибка валидации
    """
    try:
        s = scenarios.create(data, current_user().id)
    except ValueError as e:
        return error(str(e), 400)
    return success({'id': s.id, 'name': s.name}, 201)


@api_bp.put('/scenarios/<int:sid>')
@admin_required
@validate_body(ScenarioUpdateSchema)
def scenario_update(sid, data):
    """
    Редактирование сценария
    ---
    responses:
      200:
        description: Сценарий обновлён
      400:
        description: Ошибка валидации
      404:
        description: Сценарий не найден
    """
    try:
        s = scenarios.update(sid, data)
    except ValueError as e:
        return error(str(e), 400)
    return success({'id': s.id, 'name': s.name})


@api_bp.delete('/scenarios/<int:sid>')
@admin_required
def scenario_delete(sid):
    """
    Удаление сценария
    ---
    responses:
      200:
        description: Сценарий удалён
      404:
        description: Сценарий не найден
    """
    try:
        scenarios.delete(sid)
    except ValueError as e:
        return error(str(e), 404)
    return success({'message': 'deleted'})

@api_bp.put('/scenarios/<int:sid>/weights/swara')
@admin_required
@validate_body(SwaraWeightsSchema)
def scenario_set_swara_weights(sid, data):
    """
    Сохранение весовых кэффициентов
    ---
    responses:
      200:
        description: Веса сохранены
      400:
        description: Ошибка валидации
      404:
        description: Сценарий не найден
    """
    try:
        result = scenarios.set_swara_weights(sid, data['ranking'], data['s_values'])
    except ValueError as e:
        return error(str(e), 400)
    return success(result)


@api_bp.get('/scenarios/<int:sid>/weights/swara')
@login_required
def scenario_get_swara_weights(sid):
    """
    Получение весов SWARA для сценария
    ---
    responses:
      200:
        description: Веса SWARA
      404:
        description: Сценарий не найден
    """
    s = scenario_repo.get_by_id(sid)
    if not s:
        return error(f'Сценарий {sid} не найден', 404)
    config = s.get_swara_config()
    if not config:
        return success({'ranking': [], 's_values': [], 'weights': {}})
    return success({
        'ranking': config['ranking'],
        's_values': config['s_values'],
        'weights': SwaraService.compute(config['ranking'], config['s_values']),
    })

@api_bp.post('/scenarios/<int:sid>/run')
@admin_required
def scenario_run(sid):
    """
    Запуск расчёта рейтинга
    ---
    responses:
      202:
        description: Задача расчёта создана
      400:
        description: Ошибка запуска
    """
    try:
        result = task_svc.start_run(sid, current_user().id)
    except ValueError as e:
        return error(str(e), 400)
    return success(result, 202)


@api_bp.get('/scenarios/<int:sid>/runs')
@login_required
def scenario_runs(sid):
    """
    Список всех запусков сценария
    ---
    responses:
      200:
        description: Список запусков
    """
    return success([serialize_run(r) for r in run_repo.get_all_by_scenario(sid)])


@api_bp.get('/runs/<int:rid>')
@login_required
def run_detail(rid):
    """
    Детали запуска
    ---
    responses:
      200:
        description: Данные запуска и результаты
      404:
        description: Запуск не найден
    """
    run = run_repo.get_by_id(rid)
    if not run:
        return error(f'Запуск {rid} не найден', 404)
    return success({
        'run': serialize_run(run),
        'results': [serialize_run_result(r) for r in run_result_repo.get_by_run(rid)],
    })


@api_bp.get('/scenarios/<int:sid>/latest-results')
@login_required
def latest_results(sid):
    """
    Последние результаты расчёта
    ---
    responses:
      200:
        description: Последний запуск и результаты
    """
    run = run_repo.get_latest_by_scenario(sid)
    if not run:
        return success({'run': None, 'results': []})
    return success({
        'run': serialize_run(run),
        'results': [serialize_run_result(r) for r in run_result_repo.get_by_run(run.id)],
    })

@api_bp.get('/scenarios/<int:sid>/export')
@login_required
def export_excel(sid):
    """
    Экспорт результатов в Excel
    ---
    responses:
      200:
        description: Excel файл
        schema:
          type: file
      404:
        description: Нет результатов
    """
    run = run_repo.get_latest_by_scenario(sid)
    if not run:
        return error('Нет результатов для экспорта', 404)
    results = run_result_repo.get_by_run(run.id)
    file_bytes = export_svc.build_excel_results(results)
    response = make_response(file_bytes)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=scenario_{sid}_results.xlsx'
    return response

@api_bp.get('/tasks/<task_id>')
@login_required
def task_status(task_id):
    """
    Статус фоновой задачи
    ---
    responses:
      200:
        description: Статус задачи
    """
    return success(task_svc.get_status(task_id))