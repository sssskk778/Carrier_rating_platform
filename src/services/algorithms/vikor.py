"""
Модуль расчёта рейтинга перевозчиков методом VIKOR -
метод многокритериальной оптимизации и компромиссного решения,
ранжирующий альтернативы по близости к идеальному решению
с учётом групповой полезности и индивидуального сожаления.
Автор: Лосева Е.А.
Дата создания: 23.04.2026
Последнее изменение: 05.05.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import numpy as np
from typing import List, Tuple, Dict, Any


class VikorService:
    """
    Многокритериальная оценка альтернатив методом VIKOR.
    Атрибуты:
        v — вес стратегии большинства (0.5 = компромисс, 1.0 = максимум групповой полезности).
    Методы:
        compute — выполняет расчёт VIKOR и возвращает scores и debug-инфо.
    """

    def __init__(self, v: float = 0.5):
        if not (0 <= v <= 1):
            raise ValueError("Параметр v должен быть в диапазоне [0, 1]")
        self.v = v

    def compute(
        self,
        raw_matrix: np.ndarray,
        kinds: List[str],
        weights: List[float]
    ) -> Tuple[List[float], Dict[str, Any]]:

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
                    f"Недопустимый тип критерия '{k}'. "
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

        f_best = np.zeros(n)
        f_worst = np.zeros(n)

        for j in range(n):
            col = X[:, j]

            if kinds[j] == "benefit":
                f_best[j], f_worst[j] = col.max(), col.min()
            else:
                f_best[j], f_worst[j] = col.min(), col.max()

        D = np.zeros_like(X)

        for j in range(n):
            denom = f_best[j] - f_worst[j]

            if abs(denom) < 1e-12:
                D[:, j] = 0.0
            else:
                D[:, j] = (f_best[j] - X[:, j]) / denom

        S = np.zeros(m)
        R = np.zeros(m)

        for i in range(m):
            for j in range(n):
                weighted = weights_arr[j] * D[i, j]
                S[i] += weighted
                R[i] = max(R[i], weighted)

        S_min, S_max = S.min(), S.max()
        R_min, R_max = R.min(), R.max()

        Q = np.zeros(m)

        for i in range(m):
            s_part = 0.0 if abs(S_max - S_min) < 1e-12 else (S[i] - S_min) / (S_max - S_min)
            r_part = 0.0 if abs(R_max - R_min) < 1e-12 else (R[i] - R_min) / (R_max - R_min)

            Q[i] = self.v * s_part + (1 - self.v) * r_part

        Q_min, Q_max = Q.min(), Q.max()

        scores = (
            np.ones(m)
            if abs(Q_max - Q_min) < 1e-12
            else 1.0 - (Q - Q_min) / (Q_max - Q_min)
        )

        debug = {
            "f_best": f_best.tolist(),
            "f_worst": f_worst.tolist(),
            "D_values": D.tolist(),
            "S_values": S.tolist(),
            "R_values": R.tolist(),
            "Q_values": Q.tolist(),
            "scores": scores.tolist(),
        }

        return scores.tolist(), debug