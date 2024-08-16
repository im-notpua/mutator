import io
import logging
import random
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class InsertComment(BaseMutator):
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
            # Select node to insert comment into
            _, element = self._pick_element(xml_tree, exclude_root_node=False)
            if element is not None and element.text is not None and len(element.text.strip()) > 2:
                self.logger.debug("Found element to insert comment into subtree.")
                found = True
                break

        self.logger.debug("Inserting comment into element %s from input.", element)

        if random.choice((True, False)) or not found or len(element.text) < 1:
            xml_tree_str = self._serialize_xml(xml_tree)
            indices = random.sample(range(0, len(xml_tree_str)), 2)
            indices.sort()
            xml_tree_str = (
                xml_tree_str[: indices[0]]
                + "<!--"
                + xml_tree_str[indices[0] : indices[1]]
                + "-->"
                + xml_tree_str[indices[1] :]
            )
        else:
            index = random.randrange(0, len(element.text))
            element.text = (
                element.text[:index]
                + "insert_start_comment_here"
                + "insert_end_comment_here"
                + element.text[index:]
            )
            xml_tree_str = (
                self._serialize_xml(xml_tree)
                .replace("insert_start_comment_here", "<!--")
                .replace("insert_end_comment_here", "-->")
            )

        return bytearray(xml_tree_str.encode("utf-8"))


def register() -> None:
    plugin_util.register_plugin("insert_comment", InsertComment)
