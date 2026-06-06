"""
Сервис управления сценариями оценки.
Содержит только бизнес-логику: создание, обновление, удаление, веса SWARA.
"""
from src import db
from src.models import Scenario, ScenarioCriterion
from src.services.algorithms.swara import SwaraService
from src.repositories import ScenarioRepository, CriterionRepository


class ScenarioService:

    def __init__(self):
        self.repo     = ScenarioRepository()
        self.criteria = CriterionRepository()

    def create(self, payload: dict, user_id: int) -> Scenario:
        scenario = Scenario(
            name=(payload.get('name') or '').strip(),
            description=(payload.get('description') or '').strip(),
            method=payload.get('method', 'topsis'),
            status='черновик',
            created_by=user_id,
        )
        self.repo.save(scenario)
        db.session.flush()
        self._sync_criteria(scenario.id, payload.get('criterion_ids', []))
        db.session.commit()
        return scenario

    def update(self, scenario_id: int, payload: dict) -> Scenario:
        scenario = self._get(scenario_id)
        scenario.name        = (payload.get('name') or '').strip()
        scenario.description = (payload.get('description') or '').strip()
        scenario.method      = payload.get('method', 'topsis')
        self.criteria.delete_scenario_criteria(scenario.id)
        self._sync_criteria(scenario.id, payload.get('criterion_ids', []))
        db.session.commit()
        return scenario

    def delete(self, scenario_id: int) -> None:
        scenario = self._get(scenario_id)
        self.repo.delete(scenario)
        db.session.commit()

    def set_swara_weights(self, scenario_id: int, ranking: list, s_values: list) -> dict:
        scenario = self._get(scenario_id)
        scenario.set_swara_config(ranking, s_values)
        db.session.commit()
        return {
            'id':           scenario.id,
            'swara_config': scenario.get_swara_config(),
            'weights':      SwaraService.compute(ranking, s_values),
        }

    def _get(self, scenario_id: int) -> Scenario:
        scenario = self.repo.get_by_id(scenario_id)
        if not scenario:
            raise ValueError(f'Сценарий {scenario_id} не найден')
        return scenario

    def _sync_criteria(self, scenario_id: int, criterion_ids: list) -> None:
        if not criterion_ids:
            return
        existing_ids = {c.id for c in self.criteria.get_by_ids(criterion_ids)}
        missing = set(criterion_ids) - existing_ids
        if missing:
            raise ValueError(f'Критерии не найдены: {sorted(missing)}')
        for idx, cid in enumerate(criterion_ids, start=1):
            self.criteria.save_scenario_criterion(ScenarioCriterion(
                scenario_id=scenario_id,
                criterion_id=cid,
                is_enabled=True,
                order_no=idx,
            ))