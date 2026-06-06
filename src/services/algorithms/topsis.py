"""
Модуль расчёта рейтинга перевозчиков методом TOPSIS.
Technique for Order Preference by Similarity to Ideal Solution —
метод многокритериального принятия решений, ранжирующий альтернативы
по близости к идеальному и антиидеальному решениям.
Автор: Лосева Е.А.
Дата создания: 23.04.2026
Последнее изменение: 06.05.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import numpy as np
from typing import List, Tuple, Dict, Any


class TopsisService:
    """
    Расчёт рейтинга перевозчиков методом TOPSIS.
    Методы:
        compute — выполняет расчёт TOPSIS и возвращает scores и debug-инфо.
    """

    def compute(
        self,
        raw_matrix: np.ndarray,
        kinds: List[str],
        weights: List[float]
    ) -> Tuple[List[float], List[Dict[str, Any]]]:

        if raw_matrix is None or len(raw_matrix) == 0:
            raise ValueError("Матрица пустая")

        X = np.array(raw_matrix, dtype=float)

        if np.isnan(X).any() or np.isinf(X).any():
            raise ValueError("Матрица содержит NaN или бесконечные значения")

        m, n = X.shape

        if len(kinds) != n:
            raise ValueError(f"Длина kinds должна быть {n}, сейчас {len(kinds)}")

        if len(weights) != n:
            raise ValueError(f"Длина weights должна быть {n}, сейчас {len(weights)}")

        allowed_kinds = {"benefit", "cost"}

        for i, k in enumerate(kinds):
            if not isinstance(k, str):
                raise TypeError(f"kinds[{i}] должен быть строкой")

            k_norm = k.strip().lower()

            if k_norm not in allowed_kinds:
                raise ValueError(
                    f"Недопустимый тип критерия: '{k}'. "
                    f"Допустимые значения: benefit, cost"
                )

            kinds[i] = k_norm

        weights_arr = np.array(weights, dtype=float)

        if np.isnan(weights_arr).any() or np.isinf(weights_arr).any():
            raise ValueError("Веса содержат NaN или бесконечные значения")

        if np.any(weights_arr < 0):
            raise ValueError("Веса не могут быть отрицательными")

        weight_sum = weights_arr.sum()
        if weight_sum <= 0:
            raise ValueError("Сумма весов должна быть больше 0")

        weights_arr = weights_arr / weight_sum

        denom = np.sqrt((X ** 2).sum(axis=0))
        denom = np.where(denom == 0, 1, denom)

        X_norm = X / denom
        V = X_norm * weights_arr

        ideal_best = np.zeros(n)
        ideal_worst = np.zeros(n)

        for j in range(n):
            col = V[:, j]

            if kinds[j] == "benefit":
                ideal_best[j] = col.max()
                ideal_worst[j] = col.min()
            else:
                ideal_best[j] = col.min()
                ideal_worst[j] = col.max()

        d_pos = np.sqrt(((V - ideal_best) ** 2).sum(axis=1))
        d_neg = np.sqrt(((V - ideal_worst) ** 2).sum(axis=1))

        score = d_neg / (d_pos + d_neg + 1e-12)

        debug = [
            {
                "distance_to_best": float(d_pos[i]),
                "distance_to_worst": float(d_neg[i]),
                "norm_values": X_norm[i].tolist(),
            }
            for i in range(m)
        ]

        return score.tolist(), debug