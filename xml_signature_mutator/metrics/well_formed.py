import logging

from plugin_base import plugin_util
from plugin_base.base_metric import BaseMetric


class WellFormed(BaseMetric):
    logger = logging.getLogger(__name__)

    def evaluate(self, state: dict, data: dict) -> list:
        self.logger.debug("WellFormed metric evlauating...")

        metric = self._get_measurements(data, "percent_well_formed")

        res = {}

        for identifier, score in metric:
            res.update({identifier: score})

        return res

    def stage_duration(self, current_stage_duration: int, state: dict, data: dict) -> int:
        return current_stage_duration
        # implement generator


def register() -> None:
    plugin_util.register_plugin("well_formed", WellFormed)
