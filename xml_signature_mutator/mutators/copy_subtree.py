import copy
import io
import logging
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class CopySubtree(BaseMutator):
    logger = logging.getLogger(__name__)

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        # Select a node to modify (but the root one)
        found: bool = False
        for _ in range(0, 20):
            # Select subtrees to swap
            _, tree_to_copy = self._pick_element(xml_tree, exclude_root_node=True)
            _, new_parent = self._pick_element(xml_tree, exclude_root_node=False)

            if tree_to_copy is not None and new_parent is not None:
                if not tree_to_copy == new_parent:
                    found = True
                    break

        if not found:
            self.logger.debug("Did not find subtrees to copy. Skipping mutation step.")
            return input_xml

        tree_copy = copy.deepcopy(tree_to_copy)
        new_parent.append(tree_copy)

        self.logger.debug("Copying subtree %s to %s.", tree_to_copy, new_parent)

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("copy_subtree", CopySubtree)
