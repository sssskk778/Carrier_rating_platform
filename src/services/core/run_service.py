"""
Сервис запуска расчёта рейтинга перевозчиков.
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


# --- Пороги отсева перевозчиков --------------------------------------------
# Ключ — код критерия (поле `code` в таблице criteria). ОБЯЗАТЕЛЬНО приведите
# эти коды в соответствие с реальными кодами в вашей БД.
#   'min' — значение должно быть НЕ НИЖЕ порога,
#   'max' — значение должно быть НЕ ВЫШЕ порога.
# Пороги заданы в процентах (0–100). Если в матрице хранятся доли (0–1),
# замените значения на 0.70 / 0.95 / 0.15.
THRESHOLDS = {
    'on_time_rate':      ('min', 40.0),   # своевременность доставки, % ≥ 70
    'cargo_safety_rate':    ('min', 50.0),   # сохранность груза, % ≥ 95
    'cancellation_rate': ('max', 35.0),   # доля отменённых рейсов, % ≤ 15
}

# Значения поля `kind`, означающие критерий-минимизатор ("чем меньше, тем лучше").
# Приведите в соответствие с тем, как kind кодируется у вас в TOPSIS/VIKOR.
COST_KINDS = {'cost', 'min', 'minimize', '-', 'затраты', 'минимизация'}


def _is_benefit(kind) -> bool:
    """True, если критерий — максимизатор (чем больше, тем лучше)."""
    return str(kind).strip().lower() not in COST_KINDS


class RunService:

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

            # --- Отсев по порогам -----------------------------------------
            # Проверяются только те пороговые критерии, что присутствуют среди
            # выбранных в сценарии. Для отсутствующих критериев проверка
            # пропускается (держите своевременность/сохранность/отмены в выборе).
            threshold_cols = {
                selected_codes.index(code): rule
                for code, rule in THRESHOLDS.items()
                if code in selected_codes
            }

            def _passes(row) -> bool:
                for col, (direction, limit) in threshold_cols.items():
                    val = row[col]
                    if val is None or math.isnan(val):
                        return False  # не можем проверить порог — исключаем
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

            # --- Расчёт ----------------------------------------------------
            if method == 'vikor':
                scores, _   = self.vikor.compute(matrix_np, kinds, weights)
                method_name = 'VIKOR'
            else:
                scores, _   = self.topsis.compute(matrix_np, kinds, weights)
                method_name = 'TOPSIS'

            # --- Ранжирование с тай-брейком по самому весомому критерию ----
            # При равном score выше встаёт перевозчик с лучшим значением
            # критерия с максимальным весом (с учётом направления критерия).
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