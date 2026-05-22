"""
Описание: Модуль расчета критериев оценки перевозчиков.
Содержит класс CriteriaCalculator, реализующий расчет 8 критериев
на основе исторических данных о рейсах с двухпериодным взвешиванием.

Критерии:
  on_time_rate        (benefit) — своевременная доставка
  cancellation_rate   (cost)    — доля отменённых рейсов
  cargo_safety_rate   (benefit) — сохранность груза
  accident_rate       (cost)    — аварийность
  tracking_compliance (benefit) — GPS-трекинг
  pod_rate            (benefit) — документооборот (POD)
  feedback_score      (benefit) — репутация
  rate_per_km         (cost)    — ставка за км

Периоды:
  - Последние 60 дней  — вес 0.8 (актуальные данные)
  - От 61 до 360 дней  — вес 0.2 (история)
  Перевозчик исключается если за последние 60 дней < 3 доставленных рейсов.

Автор: Лосева Е.А.
Дата создания: ДД.ММ.ГГГГ
Последнее изменение: ДД.ММ.ГГГГ
Контакт: ekaterinaloseva91@gmail.com
"""
from datetime import datetime, timedelta
from app.models import Carrier, Shipment

ACCIDENT_SEVERITY_COEFFICIENTS = {
    'Легкое':  0.5,
    'Среднее': 1.0,
    'Тяжелое': 2.0,
}

PERIOD_SHORT = 60     # дней — актуальный период
PERIOD_LONG  = 360    # дней — горизонт истории
WEIGHT_SHORT = 0.8    # вес актуального периода
WEIGHT_LONG  = 0.2    # вес исторического периода
MIN_RECENT   = 3      # минимум доставленных рейсов за 60 дней


class CriteriaCalculator:

    def __init__(self):
        self.today        = datetime.now().date()
        self.cutoff_short = self.today - timedelta(days=PERIOD_SHORT)
        self.cutoff_long  = self.today - timedelta(days=PERIOD_LONG)
        self.carriers  = []
        self.shipments = []

    # ------------------------------------------------------------------
    # Загрузка данных
    # ------------------------------------------------------------------

    def load_data(self):
        """
        Назначение:
            Загружает всех перевозчиков и рейсы из базы данных.
        Параметры:
            Нет.
        Возвращает:
            CriteriaCalculator: self.
        """
        self.carriers  = Carrier.query.all()
        self.shipments = Shipment.query.all()
        return self

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _split(self, shipments):
        """
        Назначение:
            Разбивает список рейсов на два периода.
            recent  — последние 60 дней (вес 0.8)
            history — от 61 до 360 дней  (вес 0.2)
        Параметры:
            shipments (list[Shipment]): Список рейсов.
        Возвращает:
            tuple: (recent, history).
        """
        recent  = [s for s in shipments if s.pickup_window_start.date() >= self.cutoff_short]
        history = [s for s in shipments if self.cutoff_long <= s.pickup_window_start.date() < self.cutoff_short]
        return recent, history

    def _weighted_ratio(self, shipments, condition_fn):
        """
        Назначение:
            Считает взвешенную долю рейсов удовлетворяющих условию.
            Формула: (w_r × match_r/total_r + w_h × match_h/total_h) / (w_r + w_h) × 100%
        Параметры:
            shipments (list[Shipment]): Список рейсов.
            condition_fn (callable): Функция bool(shipment).
        Возвращает:
            float: Процент от 0 до 100.
        """
        recent, history = self._split(shipments)
        result  = 0.0
        total_w = 0.0

        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            if not group:
                continue
            match    = sum(1 for s in group if condition_fn(s))
            result  += w * (match / len(group))
            total_w += w

        return round(result / total_w * 100, 2) if total_w > 1e-12 else 0.0

    # ------------------------------------------------------------------
    # Основной метод расчёта
    # ------------------------------------------------------------------

    def calculate_all(self):
        """
        Назначение:
            Выполняет расчёт 8 критериев для всех перевозчиков.
            Перевозчики с менее чем MIN_RECENT доставленных рейсов
            за последние 60 дней исключаются из расчёта.
        Параметры:
            Нет.
        Возвращает:
            dict: {carrier_id: {company_name, criteria_raw}}.
        """
        results = {}

        for carrier in self.carriers:
            shipments = [s for s in self.shipments if s.carrier_id == carrier.carrier_id]
            delivered = [s for s in shipments if s.status == 'Доставлено']

            recent_delivered = [
                s for s in delivered
                if s.pickup_window_start.date() >= self.cutoff_short
            ]
            if len(recent_delivered) < MIN_RECENT:
                continue

            results[carrier.carrier_id] = {
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

        return results

    # ------------------------------------------------------------------
    # Критерии
    # ------------------------------------------------------------------

    def _on_time(self, delivered):
        """
        Назначение:
            Своевременная доставка (benefit).
            Количество рейсов выполненных в срок / общее количество × 100%.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Процент от 0 до 100.
        """
        return self._weighted_ratio(
            delivered,
            lambda s: bool(s.actual_delivery_time and s.delivery_window_end
                           and s.actual_delivery_time <= s.delivery_window_end)
        )

    def _cancellation(self, shipments):
        """
        Назначение:
            Доля отменённых рейсов (cost).
            Количество отменённых рейсов / общее количество × 100%.
        Параметры:
            shipments (list[Shipment]): Все рейсы перевозчика.
        Возвращает:
            float: Процент от 0 до 100.
        """
        return self._weighted_ratio(shipments, lambda s: s.status == 'Отменено')

    def _cargo_safety(self, delivered):
        """
        Назначение:
            Сохранность груза (benefit).
            Доля рейсов БЕЗ повреждения или потери груза.
            Формула: (1 - доля_рейсов_с_проблемами) × 100%.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Процент от 0 до 100.
        """
        damaged = self._weighted_ratio(
            delivered,
            lambda s: s.claim_type in ('Повреждение', 'Потеря')
        )
        return round(100.0 - damaged, 2)

    def _accident(self, delivered):
        """
        Назначение:
            Аварийность (cost).
            Сумма (количество ДТП × коэффициент тяжести) / общее количество рейсов × 100%.
            Коэффициенты: Легкое=0.5, Среднее=1.0, Тяжелое=2.0.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Индекс от 0 до 100.
        """
        recent, history = self._split(delivered)
        result  = 0.0
        total_w = 0.0

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

    def _tracking(self, delivered):
        """
        Назначение:
            Отслеживание — доля рейсов с GPS-трекингом (benefit).
            Количество рейсов с GPS / общее количество × 100%.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Процент от 0 до 100.
        """
        return self._weighted_ratio(delivered, lambda s: bool(s.has_gps))

    def _pod(self, delivered):
        """
        Назначение:
            Документооборот — доля рейсов с подтверждением доставки POD (benefit).
            Количество рейсов с POD / общее количество × 100%.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Процент от 0 до 100.
        """
        return self._weighted_ratio(delivered, lambda s: bool(s.has_pod))

    def _feedback(self, delivered):
        """
        Назначение:
            Репутация — средняя оценка клиентов (benefit).
            Сумма всех оценок / общее количество рейсов.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Оценка от 1.0 до 5.0.
        """
        recent, history = self._split(delivered)
        result  = 0.0
        total_w = 0.0

        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            if not group:
                continue
            result  += w * (sum(float(s.client_rating) for s in group) / len(group))
            total_w += w

        return round(result / total_w, 2) if total_w > 1e-12 else 0.0

    def _rpk(self, delivered):
        """
        Назначение:
            Ставка за км (cost).
            Сумма цен за км по каждому рейсу / общее количество рейсов.
            Считается как суммарная стоимость / суммарное расстояние
            внутри каждого периода.
        Параметры:
            delivered (list[Shipment]): Доставленные рейсы.
        Возвращает:
            float: Рублей за км.
        """
        recent, history = self._split(delivered)
        result  = 0.0
        total_w = 0.0

        for group, w in [(recent, WEIGHT_SHORT), (history, WEIGHT_LONG)]:
            if not group:
                continue
            total_price = sum(float(s.price) for s in group)
            total_dist  = sum(float(s.distance_km) for s in group if float(s.distance_km) > 0)
            if total_dist < 1e-12:
                continue
            result  += w * (total_price / total_dist)
            total_w += w

        return round(result / total_w, 2) if total_w > 1e-12 else 0.0