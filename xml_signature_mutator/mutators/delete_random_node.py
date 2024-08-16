import io
import logging
import re
from dataclasses import dataclass
from xmlrpc.client import Boolean

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class DeleteRandomNode(BaseMutator):
    delete_children: Boolean = False
    logger = logging.getLogger(__name__)
    openclose_reg = re.compile(r"<delete_this_element.*>([^$]*)</delete_this_element[^>]*>")
    selfclose_reg = re.compile(r"<delete_this_element.*/>")

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        # Select a node to modify (but the root one)
        _, rand_elem = self._pick_element(xml_tree, exclude_root_node=True)
        # If the document includes only a top-level element
        # Then we can't pick a element (given that "exclude_root_node = True")

        # Is the document deep enough?
        if rand_elem is None:
            self.logger.debug("There is no element to delete")
            return input_xml
        self.logger.debug("Deleting element %s from input.", rand_elem)

        # If we delete the node but keep the children, safe children first
        if not self.delete_children:
            try:
                # Get position of rand_elem in list of parent's children
                index = rand_elem.getparent().getchildren().index(rand_elem)
                # Move all children of rand_element to parent
                # Keep order of elements; hence, insert in reverse order
                if len(rand_elem.getchildren()) > 0:
                    children = rand_elem.getchildren()
                    children.reverse()
                    for child in children:
                        rand_elem.getparent().insert(index, child)

            except Exception as exp:
                self.logger.debug(
                    "Error keeping children of deleted note. Abort mutation. %s.", exp
                )

        # Remove the node
        rand_elem.tag = "delete_this_element"
        xml_tree_str = self._serialize_xml(xml_tree)

        xml_tree_str = re.sub(self.openclose_reg, "", xml_tree_str)
        xml_tree_str = re.sub(self.selfclose_reg, "", xml_tree_str)

        xml_tree = etree.parse(
            io.BytesIO(
                bytearray(
                    xml_tree_str,
                    encoding="utf-8",
                )
            )
        )

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("delete_random_node", DeleteRandomNode)
