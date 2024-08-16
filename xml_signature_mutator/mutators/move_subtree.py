import io
import logging
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class MoveSubtree(BaseMutator):
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
            _, tree_to_move = self._pick_element(xml_tree, exclude_root_node=True)
            _, new_parent = self._pick_element(xml_tree, exclude_root_node=False)

            if tree_to_move is not None and new_parent is not None:
                if not (new_parent == tree_to_move or self.is_subtree_of(new_parent, tree_to_move)):
                    self.logger.debug("Found new parent for subtree.")
                    found = True
                    break

        if not found:
            self.logger.debug(
                "Did not find subtree and/or place to move it to. Skipping mutation step."
            )
            return input_xml

        self.logger.debug("Moving subtrees %s to %s from input.", tree_to_move, new_parent)

        tree_to_move.getparent().remove(tree_to_move)
        new_parent.append(tree_to_move)

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("move_subtree", MoveSubtree)
