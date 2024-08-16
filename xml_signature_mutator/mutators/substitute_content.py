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
class SubstituteContent(BaseMutator):
    logger = logging.getLogger(__name__)
    contents: set = field(default_factory=set)

    def init(self, seed: bytearray) -> None:
        """Initialized this mutator. Called once per mutation."""
        random.seed(str(seed))

        # add content that should always be tested
        self.contents.add("")
        self.contents.add("\n")

        input_dir = pathlib.Path(os.getenv("INPUT_DIR", None))
        if input_dir:
            for file in input_dir.glob("*.xml"):
                with file.open("r+b") as file:
                    self.logger.debug('Loading initial input "%s".', file.name)
                    input_xml = bytearray(file.read())

                    try:
                        xml_tree = etree.parse(io.BytesIO(input_xml))

                        for element in xml_tree.getroot().iterdescendants():
                            if element.text:
                                self.contents.add(element.text.strip())

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

        # Select node to insert comment into
        _, element = self._pick_element(xml_tree, exclude_root_node=False)

        if element is None:
            self.logger.debug("Did not find element.")
            return input_xml

        self.logger.debug("Changing content of element %s.", element)

        if random.choice((True, False)) or element.text is None:
            _contents = list(self.contents)
            if element.text in _contents:
                _contents.remove(element.text)
            element.text = random.choice(_contents)

        else:
            element.text = None

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("substitute_content", SubstituteContent)
