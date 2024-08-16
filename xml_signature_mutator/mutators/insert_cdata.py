import io
import logging
import random
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class InsertCDATA(BaseMutator):
    logger = logging.getLogger(__name__)

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        found: bool = False
        for _ in range(0, 20):
            # Select node to insert cdata into
            _, element = self._pick_element(xml_tree, exclude_root_node=False)
            if element is not None and element.text is not None and len(element.text.strip()) > 0:
                self.logger.debug("Found element to insert CDATA into.")
                found = True
                break

        self.logger.debug("Inserting CDATA into element %s.", element)

        if random.choice((True, False)) or not found or len(element.text) < 1:
            xml_tree_str = self._serialize_xml(xml_tree)
            indices = random.sample(range(0, len(xml_tree_str)), 2)
            indices.sort()
            xml_tree_str = (
                xml_tree_str[: indices[0]]
                + "<![CDATA["
                + xml_tree_str[indices[0] : indices[1]]
                + "]]>"
                + xml_tree_str[indices[1] :]
            )
        # insert empty CDATA
        else:
            index = random.randrange(0, len(element.text))
            element.text = (
                element.text[:index]
                + "place_start_cdata_here"
                + "place_end_cdata_here"
                + element.text[index:]
            )
            xml_tree_str = (
                self._serialize_xml(xml_tree)
                .replace("place_start_cdata_here", "<![CDATA[")
                .replace("place_end_cdata_here", "]]>")
            )

        self.logger.debug("Inserting CDATA into element %s.", element)

        return bytearray(xml_tree_str.encode("utf-8"))


def register() -> None:
    plugin_util.register_plugin("insert_cdata", InsertCDATA)
