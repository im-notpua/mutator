import logging

from plugin_base import plugin_util
from plugin_base.base_metric import BaseMetric


class DummyMetric(BaseMetric):
    logger = logging.getLogger(__name__)

    def evaluate(self, state: dict, data: dict) -> list:
        self.logger.debug("dummy metric evlauating...")
        self.logger.debug("New findings metric evlauating...")

        res = {}

        for identifier, _ in data.items():
            if identifier == "fallback_mutator":
                continue
            res.update({identifier: 1})

        return res

    def stage_duration(self, current_stage_duration: int, state: dict, data: dict) -> int:
        return current_stage_duration


def register() -> None:
    plugin_util.register_plugin("dummy_metric", DummyMetric)
