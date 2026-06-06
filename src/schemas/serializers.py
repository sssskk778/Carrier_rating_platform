"""
Сериализаторы, для преобразования моделей БД в словари для JSON-ответов.
Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import json
from src.models import Dataset, Carrier, Scenario, Run, RunResult, Criterion


def serialize_dataset(d: Dataset) -> dict:
    return {
        'id':            d.id,
        'name':          d.name,
        'file_name':     d.file_name,
        'description':   d.description,
        'records_count': d.records_count,
        'created_at':    d.created_at.isoformat() if d.created_at else None,
    }


def serialize_carrier(c: Carrier) -> dict:
    return {
        'carrier_id':   c.carrier_id,
        'company_name': c.company_name,
        'fleet_type':   c.fleet_type,
        'region':       c.region,
    }


def serialize_criterion(c: Criterion) -> dict:
    return {
        'id':       c.id,
        'code':     c.code,
        'name':     c.name,
        'kind':     c.kind,
        'order_no': c.order_no,
    }


def serialize_scenario(s: Scenario, criteria: list = None) -> dict:
    criteria = criteria or []
    return {
        'id':            s.id,
        'name':          s.name,
        'description':   s.description,
        'method':        s.method,
        'status':        s.status,
        'criterion_ids': [c.id for c in criteria],
        'criteria':      [serialize_criterion(c) for c in criteria],
    }


def serialize_run(r: Run) -> dict:
    return {
        'id':          r.id,
        'status':      r.status,
        'started_at':  r.started_at.isoformat() if r.started_at else None,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
        'meta':        json.loads(r.meta_json or '{}'),
        'scenario_id': r.scenario_id,
    }


def serialize_run_result(r: RunResult) -> dict:
    return {
        'company_name': r.carrier.company_name,
        'carrier_id':   r.carrier_id,
        'rank':         r.rank,
        'score':        r.score,
        'details':      json.loads(r.details_json or '{}'),
    }