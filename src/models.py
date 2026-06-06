"""
Описание: Модуль моделей базы данных Carrier Rating Platform. Содержит описание всех таблиц и связей между ними.
Автор: Лосева Е.А.
Дата создания: ДД.ММ.ГГГГ
Последнее изменение: ДД.ММ.ГГГГ
Контакт: ekaterinaloseva91@gmail.com
"""
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from src import db
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, value: str):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value: str) -> bool:
        return check_password_hash(self.password_hash, value)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    file_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    records_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Criterion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    order_no = db.Column(db.Integer, nullable=False)

class Carrier(db.Model):
    carrier_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    fleet_type = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)

class Shipment(db.Model):
    shipment_id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id', ondelete='CASCADE'), nullable=True, index=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carrier.carrier_id', ondelete='SET NULL'), nullable=True, index=True)
    pickup_window_start = db.Column(db.DateTime, nullable=True)
    delivery_window_end = db.Column(db.DateTime, nullable=True)
    actual_delivery_time = db.Column(db.DateTime, nullable=True)
    client_rating = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    distance_km = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), nullable=True, index=True)
    has_gps = db.Column(db.Boolean, default=False)
    has_pod = db.Column(db.Boolean, default=False)
    accident_severity = db.Column(db.String(20), nullable=True)
    carrier_fault = db.Column(db.Boolean, default=False)
    claim_type = db.Column(db.String(20), nullable=True)

class Scenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    method = db.Column(db.String(30), nullable=False, default='topsis')
    swara_config_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default='draft')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by_user = db.relationship('User', backref='scenarios', foreign_keys=[created_by])

    def get_swara_config(self):
        return json.loads(self.swara_config_json) if self.swara_config_json else {}

    def set_swara_config(self, ranking, s_values):
        self.swara_config_json = json.dumps({
            'ranking': ranking,
            's_values': s_values
        })

class ScenarioCriterion(db.Model):
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id', ondelete='CASCADE'), primary_key=True)
    criterion_id = db.Column(db.Integer, db.ForeignKey('criterion.id', ondelete='CASCADE'), primary_key=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    order_no = db.Column(db.Integer, nullable=False)

class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id', ondelete='CASCADE'), nullable=False, index=True)
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='created')
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    meta_json = db.Column(db.Text, nullable=True)

class RunResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('run.id', ondelete='CASCADE'), nullable=False, index=True)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carrier.carrier_id', ondelete='CASCADE'), nullable=False, index=True)
    rank = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Float, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    carrier = db.relationship('Carrier', backref='run_results')
