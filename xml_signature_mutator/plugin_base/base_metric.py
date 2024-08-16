from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseMetric(ABC):

    identifier: str
    weight: int = 1

    @abstractmethod
    def evaluate(self, state: dict, data: dict) -> list:
        """Computes changes to probability distribution based on available data

        Args:
            state (dict): the current state of the fuzzer
            data (dict): the data collected up to this point

        Returns:
            list: the changes in probabilities suggested
        """

    def stage_duration(self, current_stage_duration: int, state: dict, data: dict) -> int:
        """Return new stage duration
        Default to current stage duration.
        """

        return current_stage_duration

    def _get_measurements(self, data: dict, metric: str):
        tmp = []

        for identifier, metrics in data.items():
            if identifier == "fallback_mutator":
                continue

            value = metrics.get(metric, 0)

            tmp.append((identifier, value))

        max_val = max(tmp, key=lambda tup: tup[1])[1]
        min_val = min(tmp, key=lambda tup: tup[1])[1]

        if max_val == 0:
            max_val = 1

        res = []
        for key, value in tmp:
            val_norm = (value - min_val) / (max_val - min_val)
            if val_norm < 0.1:
                val_norm = 0.1
            res.append((key, val_norm))

        return res
