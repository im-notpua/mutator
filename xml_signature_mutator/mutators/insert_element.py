import copy
import io
import logging
import os
import pathlib
import random
from dataclasses import dataclass, field

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class InsertElement(BaseMutator):
    logger = logging.getLogger(__name__)
    init_trees: list = field(default_factory=list)

    def init(self, seed: bytearray) -> None:
        """Initialized this mutator. Called once per mutation."""
        random.seed(str(seed))

        input_dir = pathlib.Path(os.getenv("INPUT_DIR", None))
        if input_dir:
            for file in input_dir.glob("*.xml"):
                with file.open("r+b") as file:
                    self.logger.debug('Loading initial input "%s".', file.name)
                    input_xml = bytearray(file.read())

                    try:
                        xml_tree = etree.parse(io.BytesIO(input_xml))
                        self.init_trees.append(xml_tree)

                    except XMLSyntaxError as exp:
                        self.logger.debug(
                            "Could not get elements from input %s due to parser exception: %s.",
                            file,
                            exp,
                        )

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        _, parent = self._pick_element(xml_tree, exclude_root_node=False)

        if parent is None:
            self.logger.debug("Input was empty. Return input.")
            return input_xml

        # create copy if init inputs, otherwise operations would be performed on initial list
        init_tree_copy = copy.deepcopy(self.init_trees)
        selected_tree = random.choice(init_tree_copy)
        _, new_child = self._pick_element(selected_tree, exclude_root_node=True)

        if new_child is None:
            self.logger.debug("Element selected from initial inputs was none. Return input.")
            return input_xml

        self.logger.debug("Inserting element %s as child of element %s", new_child, parent)

        if random.choice((True, False)):
            try:
                parent.append(new_child)
            except Exception as exp:
                self.logger.debug("Error while inserting element into tree, %s", exp)
        else:
            try:
                for child in new_child.iterchildren():
                    new_child.remove(child)
                parent.append(new_child)
            except Exception as exp:
                self.logger.debug("Error while inserting element into tree, %s", exp)

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("insert_element", InsertElement)
