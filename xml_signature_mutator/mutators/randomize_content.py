import io
import logging
import random
import string
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class RandomizeContent(BaseMutator):
    logger = logging.getLogger(__name__)

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        # Select node to insert comment into
        _, element = self._pick_element(xml_tree, exclude_root_node=False)

        if element is None:
            self.logger.debug("Did not find element.")
            return input_xml

        self.logger.debug("Randomizing content of element %s.", element)

        length = random.randint(1, 500)
        element.text = "".join(random.choices(string.ascii_letters + string.digits, k=length))

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("randomize_content", RandomizeContent)
