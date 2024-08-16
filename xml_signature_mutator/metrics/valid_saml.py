import logging

from plugin_base import plugin_util
from plugin_base.base_metric import BaseMetric


class ValidSAML(BaseMetric):
    logger = logging.getLogger(__name__)

    def evaluate(self, state: dict, data: dict) -> list:
        self.logger.debug("ValidSAML metric evlauating...")

        metric = self._get_measurements(data, "percent_saml_valid")

        res = {}

        for identifier, score in metric:
            res.update({identifier: score})

        return res

    def stage_duration(self, current_stage_duration: int, state: dict, data: dict) -> int:
        return current_stage_duration
        # implement generator


def register() -> None:
    plugin_util.register_plugin("valid_saml", ValidSAML)
