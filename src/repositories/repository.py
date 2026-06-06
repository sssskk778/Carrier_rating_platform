"""
Слой доступа к данным. Содержат только запросы к БД
Автор: Лосева Е.А.
Дата создания: 14.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from src import db
from src.models import (
    Carrier, Shipment, Dataset,
    Scenario, ScenarioCriterion, Criterion,
    Run, RunResult, User
)

class UserRepository:
    """
    Репозиторий для работы с пользователями системы.
    Методы:
        get_by_id — найти пользователя по ID.
        get_by_username — найти пользователя по имени.
        save — добавить нового пользователя в сессию.
    """

    def get_by_id(self, user_id: int):
        return db.session.get(User, user_id)

    def get_by_username(self, username: str):
        return User.query.filter_by(username=username).first()

    def save(self, user: User) -> User:
        db.session.add(user)
        return user


class CarrierRepository:
    """
    Репозиторий для работы с перевозчиками.
    Методы:
        get_all — получить всех перевозчиков, отсортированных по названию.
        get_by_id — найти перевозчика по ID.
        count — вернуть общее количество перевозчиков в базе.
    """

    def get_all(self) -> list:
        return Carrier.query.order_by(Carrier.company_name.asc()).all()

    def get_by_id(self, carrier_id: int):
        return db.session.get(Carrier, carrier_id)

    def count(self) -> int:
        return Carrier.query.count()


class ShipmentRepository:
    """
    Репозиторий для работы с перевозками.
    Методы:
        get_all — получить все перевозки.
        get_by_carrier — перевозки конкретного перевозчика.
        get_by_dataset — перевозки из конкретного набора данных.
        get_filtered — перевозки с фильтрацией по нескольким полям.
        count_by_dataset — количество перевозок в наборе данных.
        get_by_id — найти перевозку по ID.
        get_since — перевозки начиная с указанной даты.
        save — добавить перевозку в сессию.
    """

    def get_all(self) -> list:
        return Shipment.query.all()

    def get_by_carrier(self, carrier_id: int) -> list:
        return Shipment.query.filter_by(carrier_id=carrier_id).all()

    def get_by_dataset(self, dataset_id: int) -> list:
        return Shipment.query.filter_by(dataset_id=dataset_id).all()

    def get_filtered(self, carrier_id=None, dataset_id=None, status=None) -> list:
        q = Shipment.query
        if carrier_id:
            q = q.filter_by(carrier_id=carrier_id)
        if dataset_id:
            q = q.filter_by(dataset_id=dataset_id)
        if status:
            q = q.filter_by(status=status)
        return q.all()

    def count_by_dataset(self, dataset_id: int) -> int:
        return Shipment.query.filter_by(dataset_id=dataset_id).count()

    def get_by_id(self, shipment_id: int):
        return db.session.get(Shipment, shipment_id)

    def get_since(self, cutoff_date) -> list:
        return Shipment.query.filter(
            Shipment.pickup_window_start >= cutoff_date
        ).all()

    def save(self, shipment: Shipment) -> Shipment:
        db.session.add(shipment)
        return shipment


class DatasetRepository:
    """
    Репозиторий для работы с наборами данных.
    Методы:
        get_all — получить все наборы данных (новые сверху).
        get_by_id — найти набор данных по ID.
        save — добавить набор данных в сессию.
        delete — пометить набор данных на удаление.
    """

    def get_all(self) -> list:
        return Dataset.query.order_by(Dataset.id.desc()).all()

    def get_by_id(self, dataset_id: int):
        return db.session.get(Dataset, dataset_id)

    def save(self, dataset: Dataset) -> Dataset:
        db.session.add(dataset)
        return dataset

    def delete(self, dataset: Dataset) -> None:
        db.session.delete(dataset)


class ScenarioRepository:
    """
    Репозиторий для работы со сценариями.
    Методы:
        get_all — получить все сценарии.
        get_by_id — найти сценарий по ID.
        save — добавить сценарий в сессию.
        delete — пометить сценарий на удаление.
    """

    def get_all(self) -> list:
        return Scenario.query.order_by(Scenario.id.asc()).all()

    def get_by_id(self, scenario_id: int):
        return db.session.get(Scenario, scenario_id)

    def save(self, scenario: Scenario) -> Scenario:
        db.session.add(scenario)
        return scenario

    def delete(self, scenario: Scenario) -> None:
        db.session.delete(scenario)


class CriterionRepository:
    """
    Репозиторий для работы с критериями.
    Методы:
        get_all — получить все критерии.
        get_by_id — найти критерий по ID.
        get_by_ids — найти критерии по списку ID.
        delete_scenario_criteria — удалить все критерии сценария.
        save_scenario_criterion — добавить связку критерия со сценарием.
    """

    def get_all(self) -> list:
        return Criterion.query.order_by(Criterion.order_no.asc()).all()

    def get_by_id(self, criterion_id: int):
        return db.session.get(Criterion, criterion_id)

    def get_by_ids(self, ids: list) -> list:
        if not ids:
            return []
        return Criterion.query.filter(Criterion.id.in_(ids)).all()

    def delete_scenario_criteria(self, scenario_id: int) -> None:
        ScenarioCriterion.query.filter_by(scenario_id=scenario_id).delete()

    def save_scenario_criterion(self, sc: ScenarioCriterion) -> None:
        db.session.add(sc)


class ScenarioCriterionRepository:
    """
    Репозиторий для работы со связями сценарий-критерий.
    Методы:
        get_by_scenario — все критерии сценария.
        get_enabled_by_scenario — только включённые критерии сценария.
        delete_by_scenario — удалить все связи для сценария.
    """

    def get_by_scenario(self, scenario_id: int) -> list:
        return (ScenarioCriterion.query
                .filter_by(scenario_id=scenario_id)
                .order_by(ScenarioCriterion.order_no.asc())
                .all())

    def get_enabled_by_scenario(self, scenario_id: int) -> list:
        return (ScenarioCriterion.query
                .filter_by(scenario_id=scenario_id, is_enabled=True)
                .order_by(ScenarioCriterion.order_no.asc())
                .all())

    def delete_by_scenario(self, scenario_id: int) -> None:
        ScenarioCriterion.query.filter_by(scenario_id=scenario_id).delete()


class RunRepository:
    """
    Репозиторий для работы с запусками расчётов.
    Методы:
        get_by_id — найти запуск по ID.
        get_latest_by_scenario — последний запуск для сценария.
        get_all_by_scenario — все запуски сценария (новые сверху).
        save — добавить запуск в сессию.
    """

    def get_by_id(self, run_id: int):
        return db.session.get(Run, run_id)

    def get_latest_by_scenario(self, scenario_id: int):
        return Run.query.filter_by(scenario_id=scenario_id).order_by(Run.id.desc()).first()

    def get_all_by_scenario(self, scenario_id: int) -> list:
        return Run.query.filter_by(scenario_id=scenario_id).order_by(Run.id.desc()).all()

    def save(self, run: Run) -> Run:
        db.session.add(run)
        return run


class RunResultRepository:
    """
    Репозиторий для работы с результатами запусков.
    Методы:
        get_by_run — результаты запуска, отсортированные по рангу.
        save — добавить результат в сессию.
    """

    def get_by_run(self, run_id: int) -> list:
        return RunResult.query.filter_by(run_id=run_id).order_by(RunResult.rank.asc()).all()

    def save(self, result: RunResult) -> RunResult:
        db.session.add(result)
        return result