import copy
import io
import logging
import os
import pathlib
import random
import re
from dataclasses import dataclass, field

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class FallbackMutator(BaseMutator):
    logger = logging.getLogger(__name__)
    init_trees: list = field(default_factory=list)
    between_elem_reg = re.compile(r">([^$]){0,2}<")
    opentag_reg = re.compile(r"<[^/][\w:.-]*[^>]*>")

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

        xml_tree_str = ""
        try:
            xml_tree_str = input_xml.decode("utf-8")
        except Exception as exp:
            self.logger.info("Exception while decoding input: %s. Use bitflip mutator.", exp)
            return self.flip_bit(input_xml)

        if len(xml_tree_str) < 2:
            choice = 5
        else:
            choice = random.choice([0, 1, 2, 3, 4, 5, 6])

        try:
            # Insert CDATA anywhere
            if choice == 0:
                result = self.insert_cdata(xml_tree_str)

            # Insert comment anywhere
            elif choice == 1:
                result = self.insert_comment(xml_tree_str)

            # Insert special character anywhere
            elif choice == 2:
                result = self.insert_special_char(xml_tree_str)

            # Delete random part of input
            elif choice == 3:
                result = self.delete_random(xml_tree_str)

            # Delete whole subtree
            elif choice == 4:
                result = self.delete_element(xml_tree_str)

            # Add random element from initial set
            elif choice == 5:
                result = self.add_random_element(xml_tree_str)

            # Flip random bit in input
            elif choice == 6:
                result = self.flip_bit(input_xml)
                return result

        except Exception as exp:
            self.logger.critical("Default mutator failed with exception %s.", exp)
            return None

        return bytearray(result.encode("utf-8"))

    def insert_cdata(self, xml_tree_str) -> str:
        indices = random.sample(range(0, len(xml_tree_str)), 2)
        indices.sort()
        xml_tree_str = (
            xml_tree_str[: indices[0]]
            + "<![CDATA["
            + xml_tree_str[indices[0] : indices[1]]
            + "]]>"
            + xml_tree_str[indices[1] :]
        )
        return xml_tree_str

    def insert_comment(self, xml_tree_str) -> str:
        indices = random.sample(range(0, len(xml_tree_str)), 2)
        indices.sort()
        xml_tree_str = (
            xml_tree_str[: indices[0]]
            + "<!--"
            + xml_tree_str[indices[0] : indices[1]]
            + "-->"
            + xml_tree_str[indices[1] :]
        )
        return xml_tree_str

    def insert_special_char(self, xml_tree_str) -> str:
        index = random.randint(0, len(xml_tree_str) - 1)
        xml_tree_str = (
            xml_tree_str[:index] + random.choice(["<", ">", "&", "'", '"']) + xml_tree_str[index:]
        )
        return xml_tree_str

    def delete_random(self, xml_tree_str) -> str:
        indices = random.sample(range(0, len(xml_tree_str)), 2)
        indices.sort()
        xml_tree_str = xml_tree_str[: indices[0]] + xml_tree_str[indices[1] :]
        return xml_tree_str

    def delete_element(self, xml_tree_str) -> str:
        # super ugly... "parsing" XML with regex
        # find all opening tags
        indices = [(m.start(), m.end()) for m in self.opentag_reg.finditer(xml_tree_str)]

        # start at element 2 to not remove whole element
        try:
            element_indicies = random.randint(1, len(indices) - 1)
        # No element found, delete random part
        except Exception:
            return self.delete_random(xml_tree_str)

        indices.sort()
        # extract tag of opening element
        element_tag = (
            xml_tree_str[indices[element_indicies][0] : indices[element_indicies][1]]
            .split(" ", maxsplit=1)
            .pop(0)
            .strip("<>")
        )

        # find position of closing tag if it exists
        closing_tag = xml_tree_str.find("/" + element_tag, indices[element_indicies][1])
        # if no closing tag or self closing, remove only the element
        if (
            closing_tag == -1
            or xml_tree_str[indices[element_indicies][0] : indices[element_indicies][1]][-2] == "/"
        ):
            result = (
                xml_tree_str[: indices[element_indicies][0]]
                + xml_tree_str[indices[element_indicies][1] :]
            )
        # remove open and end tag and everything in between
        else:
            closing_tag_index = xml_tree_str.find(">", closing_tag) + 1
            result = xml_tree_str[: indices[element_indicies][0]] + xml_tree_str[closing_tag_index:]

        return result

    def add_random_element(self, xml_tree_str) -> str:

        init_tree_copy = copy.deepcopy(self.init_trees)
        selected_tree = random.choice(init_tree_copy)
        _, new_child = self._pick_element(selected_tree, exclude_root_node=False)
        if new_child is None:
            self.logger.debug("Did not find element.")
            return xml_tree_str
        new_child_str = self._serialize_xml(new_child)

        if len(xml_tree_str) == 0:
            return new_child_str

        indices = [m.start() for m in self.between_elem_reg.finditer(xml_tree_str)]
        try:
            index = random.choice(indices) + 1
        except Exception as exp:
            self.logger.debug("No element found in document. Insert at random place. %s.", exp)
            index = random.randint(0, len(xml_tree_str) - 1)

        xml_tree_str = xml_tree_str[:index] + new_child_str + xml_tree_str[index:]
        return xml_tree_str

    def flip_bit(self, input_xml) -> str:
        _input_xml = copy.deepcopy(input_xml)
        index = random.randint(0, len(_input_xml) - 1)
        _input_xml[index] ^= random.randint(1, 255)
        return _input_xml


def register() -> None:
    plugin_util.register_plugin("fallback_mutator", FallbackMutator)
