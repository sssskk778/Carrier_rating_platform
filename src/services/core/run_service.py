"""
Сервис запуска расчёта рейтинга перевозчиков.

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import json
import math
from datetime import datetime, timezone

import numpy as np
from src import db
from src.models import Run, RunResult
from src.repositories import (
    RunRepository, RunResultRepository, ScenarioRepository,
    CriterionRepository, ScenarioCriterionRepository
)
from src.services.algorithms.swara import SwaraService
from src.services.algorithms.criterion_calc import CriteriaCalculator, MIN_RECENT, PERIOD_SHORT
from src.services.algorithms.topsis import TopsisService
from src.services.algorithms.vikor import VikorService


THRESHOLDS = {
    'on_time_rate':      ('min', 40.0),
    'cargo_safety_rate': ('min', 50.0),
    'cancellation_rate': ('max', 35.0),
}

COST_KINDS = {'cost', 'min', 'minimize', '-', 'затраты', 'минимизация'}


def _is_benefit(kind) -> bool:
    return str(kind).strip().lower() not in COST_KINDS


class RunService:
    """
    Запуск расчёта рейтинга перевозчиков.
    Атрибуты:
        topsis            — сервис расчёта TOPSIS.
        vikor             — сервис расчёта VIKOR.
        runs              — репозиторий запусков.
        results           — репозиторий результатов.
        scenarios         — репозиторий сценариев.
        criteria          — репозиторий критериев.
        scenario_criteria — репозиторий связей сценарий-критерий.
    Методы:
        execute — полный цикл расчёта: загрузка данных, SWARA, отсев,
                  TOPSIS/VIKOR, ранжирование, сохранение результатов.
    """

    def __init__(self):
        self.topsis            = TopsisService()
        self.vikor             = VikorService(v=0.5)
        self.runs              = RunRepository()
        self.results           = RunResultRepository()
        self.scenarios         = ScenarioRepository()
        self.criteria          = CriterionRepository()
        self.scenario_criteria = ScenarioCriterionRepository()

    def execute(self, scenario_id: int, user_id: int) -> Run:
        scenario = self.scenarios.get_by_id(scenario_id)
        if not scenario:
            raise ValueError(f'Сценарий {scenario_id} не найден')

        scenario.status = 'в обработке'
        db.session.commit()

        try:
            method = scenario.method or 'topsis'

            links = self.scenario_criteria.get_enabled_by_scenario(scenario.id)
            if len(links) < 2:
                raise ValueError('Выберите минимум 2 критерия в настройках сценария')

            criterion_ids     = [link.criterion_id for link in links]
            selected_criteria = self.criteria.get_by_ids(criterion_ids)
            if not selected_criteria:
                raise ValueError('Критерии не найдены в базе данных')

            selected_codes = [c.code for c in selected_criteria]
            kinds          = [c.kind for c in selected_criteria]

            config = scenario.get_swara_config()
            if not config or not config.get('ranking'):
                raise ValueError('Настройте веса критериев SWARA перед запуском')

            calculator = CriteriaCalculator()
            matrix_raw, carriers_list, calculated_data = calculator.build_matrix(selected_codes)

            if not calculator.carriers or not calculator.shipments:
                raise ValueError(
                    'Нет загруженных данных. '
                    'Загрузите Excel-файл с перевозчиками и рейсами в разделе "Загрузки".'
                )

            if not matrix_raw:
                raise ValueError(
                    f'Нет перевозчиков с минимум {MIN_RECENT} доставленными рейсами '
                    f'за последние {PERIOD_SHORT} дней.'
                )

            swara_weights = SwaraService.compute(config['ranking'], config['s_values'])
            weights       = [swara_weights.get(code, 0.0) for code in selected_codes]
            matrix_np     = np.array(matrix_raw, dtype=float)

            threshold_cols = {
                selected_codes.index(code): rule
                for code, rule in THRESHOLDS.items()
                if code in selected_codes
            }

            def _passes(row) -> bool:
                for col, (direction, limit) in threshold_cols.items():
                    val = row[col]
                    if val is None or math.isnan(val):
                        return False
                    if direction == 'min' and val < limit:
                        return False
                    if direction == 'max' and val > limit:
                        return False
                return True

            kept = [i for i in range(len(carriers_list)) if _passes(matrix_np[i])]
            if not kept:
                raise ValueError(
                    'Ни один перевозчик не прошёл пороги отсева '
                    '(своевременность ≥ 70%, сохранность ≥ 95%, '
                    'отменённые рейсы ≤ 15%).'
                )

            carriers_list = [carriers_list[i] for i in kept]
            matrix_np     = matrix_np[kept]

            if method == 'vikor':
                scores, _   = self.vikor.compute(matrix_np, kinds, weights)
                method_name = 'VIKOR'
            else:
                scores, _   = self.topsis.compute(matrix_np, kinds, weights)
                method_name = 'TOPSIS'

            top_idx        = int(np.argmax(weights))
            top_is_benefit = _is_benefit(kinds[top_idx])

            def _rank_key(i):
                tie = matrix_np[i][top_idx]
                return (scores[i], tie if top_is_benefit else -tie)

            ranking = sorted(range(len(scores)), key=_rank_key, reverse=True)

            run = Run(
                scenario_id=scenario.id,
                initiated_by=user_id,
                status='done',
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                meta_json=json.dumps({
                    'criteria_codes': selected_codes,
                    'criteria_names': [c.name for c in selected_criteria],
                    'criteria_kinds': kinds,
                    'weights':        weights,
                    'method':         method_name,
                    'swara_config':   config,
                }, ensure_ascii=False)
            )
            self.runs.save(run)
            db.session.flush()

            for rank, idx in enumerate(ranking, start=1):
                carrier = carriers_list[idx]
                self.results.save(RunResult(
                    run_id=run.id,
                    carrier_id=carrier.carrier_id,
                    rank=rank,
                    score=scores[idx],
                    details_json=json.dumps({
                        'criteria_values_raw': calculated_data[carrier.carrier_id]['criteria_raw'],
                        'criteria_codes':      selected_codes,
                    }, ensure_ascii=False),
                ))

            scenario.status = 'расчёт выполнен'
            db.session.commit()

        except Exception:
            scenario.status = 'ошибка'
            db.session.commit()
            raise

        return run
