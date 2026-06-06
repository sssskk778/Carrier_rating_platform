"""
Модуль расчёта критериев оценки перевозчиков.
8 критериев с двухпериодным взвешиванием (60 дней / 360 дней).
"""
from datetime import datetime, timedelta
from src.repositories import CarrierRepository, ShipmentRepository

ACCIDENT_SEVERITY_COEFFICIENTS = {
    'Легкое':  0.5,
    'Среднее': 1.0,
    'Тяжелое': 2.0,
}

PERIOD_SHORT = 60
PERIOD_LONG  = 360
WEIGHT_SHORT = 0.8
WEIGHT_LONG  = 0.2
MIN_RECENT   = 3


class CriteriaCalculator:

    def __init__(self):
        self.today        = datetime.now().date()
        self.cutoff_short = self.today - timedelta(days=PERIOD_SHORT)
        self.cutoff_long  = self.today - timedelta(days=PERIOD_LONG)
        self.carriers     = []
        self.shipments    = []
        self._carriers_repo  = CarrierRepository()
        self._shipments_repo = ShipmentRepository()

    def build_matrix(self, selected_codes: list) -> tuple:
        """Загружает данные и возвращает (matrix_raw, carriers_list, calculated_data)."""
        self.carriers  = self._carriers_repo.get_all()
        self.shipments = self._shipments_repo.get_since(self.cutoff_long)

        calculated_data = {}
        for carrier in self.carriers:
            shipments = [s for s in self.shipments if s.carrier_id == carrier.carrier_id]
            delivered = [s for s in shipments if s.status == 'Доставлено']
            recent_delivered = [
                s for s in delivered
                if s.pickup_window_start.date() >= self.cutoff_short
            ]
            if len(recent_delivered) < MIN_RECENT:
                continue
            calculated_data[carrier.carrier_id] = {
                'company_name': carrier.company_name,
                'criteria_raw': {
                    'on_time_rate':        self._on_time(delivered),
                    'cancellation_rate':   self._cancellation(shipments),
                    'cargo_safety_rate':   self._cargo_safety(delivered),
                    'accident_rate':       self._accident(delivered),
                    'tracking_compliance': self._tracking(delivered),
                    'pod_rate':            self._pod(delivered),
                    'feedback_score':      self._feedback(delivered),
                    'rate_per_km':         self._rpk(delivered),
                }
            }

        matrix_raw, carriers_list = [], []
        for carrier in self.carriers:
            if carrier.carrier_id not in calculated_data:
                continue
            row = [
                float(calculated_data[carrier.carrier_id]['criteria_raw'].get(code, 0.0) or 0.0)
                for code in selected_codes
            ]
            matrix_raw.append(row)
            carriers_list.append(carrier)

        return matrix_raw, carriers_list, calculated_data

    def _split(self, shipments):
        recent  = [s for s in shipments if s.pickup_window_start.date() >= self.cutoff_short]
        history = [s for s in shipments if self.cutoff_long <= s.pickup_window_start.date() < self.cutoff_short]
        return recent, history

    def _weighted_ratio(self, shipments, condition_fn) -> float:
        recent, history = self._split(shipments)
        result, total_w = 0.0, 0.0
        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            if not group:
                continue
            result  += w * (sum(1 for s in group if condition_fn(s)) / len(group))
            total_w += w
        return round(result / total_w * 100, 2) if total_w > 1e-12 else 0.0

    def _on_time(self, delivered) -> float:
        return self._weighted_ratio(
            delivered,
            lambda s: bool(s.actual_delivery_time and s.delivery_window_end
                           and s.actual_delivery_time <= s.delivery_window_end)
        )

    def _cancellation(self, shipments) -> float:
        return self._weighted_ratio(shipments, lambda s: s.status == 'Отменено')

    def _cargo_safety(self, delivered) -> float:
        return round(100.0 - self._weighted_ratio(
            delivered, lambda s: s.claim_type in ('Повреждение', 'Потеря')
        ), 2)

    def _accident(self, delivered) -> float:
        """Взвешенная частота аварий с учётом тяжести (инцидентов на рейс × 100%)."""
        recent, history = self._split(delivered)
        result, total_w = 0.0, 0.0
        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            if not group:
                continue
            acc_sum = sum(
                ACCIDENT_SEVERITY_COEFFICIENTS.get(s.accident_severity, 1.0)
                for s in group
                if s.carrier_fault and s.accident_severity and s.accident_severity != 'Нет'
            )
            result  += w * (acc_sum / len(group))
            total_w += w
        return round(result / total_w * 100, 2) if total_w > 1e-12 else 0.0

    def _tracking(self, delivered) -> float:
        return self._weighted_ratio(delivered, lambda s: bool(s.has_gps))

    def _pod(self, delivered) -> float:
        return self._weighted_ratio(delivered, lambda s: bool(s.has_pod))

    def _feedback(self, delivered) -> float:
        """Средневзвешенная оценка клиентов (1-5)."""
        recent, history = self._split(delivered)
        result, total_w = 0.0, 0.0
        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            rated = [s for s in group if s.client_rating is not None]
            if not rated:
                continue
            result  += w * (sum(float(s.client_rating) for s in rated) / len(rated))
            total_w += w
        return round(result / total_w, 2) if total_w > 1e-12 else 0.0

    def _rpk(self, delivered) -> float:
        """Средневзвешенная ставка за км (руб/км)."""
        recent, history = self._split(delivered)
        result, total_w = 0.0, 0.0
        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            valid = [
                s for s in group
                if s.price is not None and s.distance_km is not None
                and float(s.distance_km) > 0 and float(s.price) > 0
            ]
            if not valid:
                continue
            total_price = sum(float(s.price) for s in valid)
            total_dist  = sum(float(s.distance_km) for s in valid)
            result  += w * (total_price / total_dist)
            total_w += w
        return round(result / total_w, 2) if total_w > 1e-12 else 0.0