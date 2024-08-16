import io
import logging
import random
from ast import List
from dataclasses import dataclass, field

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class InsertSpecialChar(BaseMutator):
    special_chars: List = field(default_factory=lambda: ["<", ">", "&", "'", '"'])
    logger = logging.getLogger(__name__)

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        xml_tree_str = self._serialize_xml(xml_tree)

        index = random.randrange(0, len(xml_tree_str))

        xml_tree_str = (
            xml_tree_str[:index] + random.choice(self.special_chars) + xml_tree_str[index:]
        )

        return bytearray(xml_tree_str.encode("utf-8"))


def register() -> None:
    plugin_util.register_plugin("insert_special_char", InsertSpecialChar)
