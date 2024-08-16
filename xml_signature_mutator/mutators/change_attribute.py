import io
import logging
import os
import pathlib
import random
import string
from dataclasses import dataclass, field

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class ChangeAttribute(BaseMutator):
    logger = logging.getLogger(__name__)
    init_attr_keys: set = field(default_factory=set)
    init_attr_values: set = field(default_factory=set)

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

                        for element in xml_tree.getroot().iterdescendants():
                            for key, value in element.attrib.items():
                                self.init_attr_keys.add(key)
                                self.init_attr_values.add(value)

                    except XMLSyntaxError as exp:
                        self.logger.info(
                            "During init, could not get elements from input %s due to parser exception: %s.",
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

        _, rand_elem = self._pick_element(xml_tree)

        if rand_elem is None:
            self.logger.debug("Did not find element.")
            return input_xml

        self.logger.debug("Changing attributes of element %s.", rand_elem)

        # 50/50 delete random attribute or add random attribute
        # If element has no attributes always add random one.
        if random.choice((True, False)) or len(rand_elem.keys()) == 0:
            for _ in range(0, 20):
                new_attr = random.choice(list(self.init_attr_keys))
                if new_attr not in list(rand_elem.attrib) or len(rand_elem.keys()) == 0:
                    if random.choice((True, False)):
                        rand_elem.attrib[new_attr] = random.choice(list(self.init_attr_values))
                    else:
                        rand_elem.attrib[new_attr] = "".join(
                            random.choices(
                                string.ascii_letters + string.digits, k=random.randint(0, 500)
                            )
                        )
                    break
        else:
            del rand_elem.attrib[random.choice(rand_elem.attrib.keys())]

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("change_attribute", ChangeAttribute)
