"""
Веб-маршруты — возвращают HTML-страницы.
"""
import logging

from flask import Blueprint, render_template, abort
from werkzeug.exceptions import HTTPException

from src.decorators import login_required, admin_required
from src.repositories import RunRepository, ScenarioRepository

logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__)

run_repo = RunRepository()
scenario_repo = ScenarioRepository()


@web_bp.get('/')
@login_required
def index():
    try:
        return render_template(
            'index.html',
            scenarios=scenario_repo.get_all()
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception('Ошибка на главной странице')
        abort(500)


@web_bp.get('/datasets')
@login_required
def dataset_page():
    return render_template('datasets.html')


@web_bp.get('/scenarios/<int:sid>')
@admin_required
def scenario_page(sid):
    try:
        if sid == 0:
            scenario = type('obj', (object,), {
                'id': 0,
                'name': '',
                'description': '',
                'method': 'topsis'
            })()
        else:
            scenario = scenario_repo.get_by_id(sid)

            if not scenario:
                abort(404)

        return render_template('scenario.html', scenario=scenario)

    except HTTPException:
        raise

    except Exception:
        logger.exception('Ошибка на странице сценария sid=%s', sid)
        abort(500)


@web_bp.get('/results/<int:sid>')
@login_required
def results_page(sid):
    try:
        scenario = scenario_repo.get_by_id(sid)

        if not scenario:
            abort(404)

        return render_template('results.html', scenario=scenario)

    except HTTPException:
        raise

    except Exception:
        logger.exception('Ошибка на странице результатов sid=%s', sid)
        abort(500)


@web_bp.get('/runs/<int:rid>')
@login_required
def run_page(rid):
    try:
        run = run_repo.get_by_id(rid)

        if not run:
            abort(404)

        return render_template('run.html', run=run)

    except HTTPException:
        raise

    except Exception:
        logger.exception('Ошибка на странице запуска rid=%s', rid)
        abort(500)


@web_bp.get('/carriers')
@login_required
def carriers_page():
    return render_template('carriers.html')


@web_bp.get('/scenarios/<int:sid>/history')
@login_required
def scenario_history(sid):
    try:
        scenario = scenario_repo.get_by_id(sid)

        if not scenario:
            abort(404)

        return render_template('history.html', scenario=scenario)

    except HTTPException:
        raise

    except Exception:
        logger.exception('Ошибка на странице истории sid=%s', sid)
        abort(500)


@web_bp.app_errorhandler(403)
def forbidden(_):
    return render_template('403.html'), 403