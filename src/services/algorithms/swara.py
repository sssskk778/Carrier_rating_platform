"""
Модуль расчета весов критериев методом SWARA.
Step-wise Weight Assessment Ratio Analysis — метод пошагового
определения весов на основе экспертного ранжирования критериев.

Автор: Лосева Е.А.
Дата создания: ДД.ММ.ГГГГ
Последнее изменение: ДД.ММ.ГГГГ
Контакт: ekaterinaloseva91@gmail.com
"""
import math

class SwaraService:
    """
    Назначение:
        Расчет весов критериев методом SWARA.
    Параметры:
        Нет.
    Возвращает:
        dict[str, float]: Словарь {код_критерия: вес}, сумма весов = 1.
    """

    @staticmethod
    def compute(ranking: list[str], s_values: list[float]) -> dict[str, float]:
        """
        Назначение:
            Расчет весов критериев методом SWARA.
        Параметры:
            ranking (list[str]): Критерии от важного к неважному.
            s_values (list[float]): Сравнительная важность (на сколько % j-1 важнее j).
        Возвращает:
            dict[str, float]: {код_критерия: вес}, сумма весов = 1.
        """

        if not isinstance(ranking, list):
            raise TypeError(f"ranking must be list, got {type(ranking).__name__}")
        if not isinstance(s_values, list):
            raise TypeError(f"s_values must be list, got {type(s_values).__name__}")

        n = len(ranking)

        if n == 0:
            raise ValueError("ranking cannot be empty")
        if n < 2:
            raise ValueError(f"Need at least 2 criteria, got {n}")

        if len(set(ranking)) != n:
            duplicates = [c for c in ranking if ranking.count(c) > 1]
            unique_dupes = list(set(duplicates))
            raise ValueError(f"Duplicate criteria in ranking: {unique_dupes}")

        if len(s_values) != n - 1:
            raise ValueError(f"Ожидается {n - 1} значений s_values, получено {len(s_values)}")

        for idx, s in enumerate(s_values):
            if not isinstance(s, (int, float)):
                raise TypeError(f"s_values[{idx}] must be int or float, got {type(s).__name__}")
            if isinstance(s, float) and math.isnan(s):
                raise ValueError(f"s_values[{idx}] is NaN")
            if s < 0:
                raise ValueError(f"Сравнительная важность не может быть отрицательной: {s}")

        k = [1.0]
        for s in s_values:
            k.append(s + 1.0)

        q = [1.0]
        for j in range(1, n):
            q.append(q[j - 1] / k[j])

        total_q = sum(q)
        if total_q < 1e-12:
            raise ValueError("Sum of intermediate weights is zero, check s_values")

        weights = {ranking[j]: q[j] / total_q for j in range(n)}
        return weights

    @staticmethod
    def validate_s_values(s_values: list[float]) -> bool:
        """
        Назначение:
            Проверка корректности значений сравнительной важности.
        Параметры:
            s_values (list[float]): Значения сравнительной важности.
        Возвращает:
            bool: True если все значения >= 0 и не NaN.
        """
        if not isinstance(s_values, list):
            return False
        return all(
            isinstance(s, (int, float))
            and not (isinstance(s, float) and math.isnan(s))
            and s >= 0
            for s in s_values
        )