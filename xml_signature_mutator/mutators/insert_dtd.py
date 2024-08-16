import io
import logging
import random
import string
import time
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class InsertDTD(BaseMutator):
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
            # Select node to insert dtd into
            _, element = self._pick_element(xml_tree, exclude_root_node=False)
            if element is not None and element.text is not None and len(element.text.strip()) > 0:
                self.logger.debug("Found element to insert dtd into.")
                found = True
                break

        self.logger.debug("Inserting dtd into element %s.", element)

        _entity = "".join(random.choices(string.ascii_lowercase, k=10))

        xml_tree_str = self._serialize_xml(xml_tree)

        doc_type = ""

        if xml_tree.docinfo.doctype:
            doc_type, xml_tree_str = xml_tree_str.split("]>", maxsplit=1)

        # random DTD anywhere
        if random.choice((True, False)) or not found or len(element.text) < 1:

            _content = ""
            indices = random.sample(range(0, len(xml_tree_str)), 2)
            indices.sort()
            _content = xml_tree_str[indices[0] : indices[1]]
            xml_tree_str = (
                (
                    xml_tree_str[: indices[0]]
                    + "place_start_entity_here"
                    + _entity
                    + "place_end_entity_here"
                    + xml_tree_str[indices[1] :]
                )
                .replace("place_start_entity_here", "&")
                .replace("place_end_entity_here", ";")
            )

        # replace no text, only empty DTD
        else:
            _content = ""
            index = random.randrange(0, len(element.text))
            element.text = (
                element.text[:index]
                + "place_start_entity_here"
                + _entity
                + "place_end_entity_here"
                + element.text[index:]
            )
            xml_tree_str = (
                self._serialize_xml(xml_tree)
                .replace("place_start_entity_here", "&")
                .replace("place_end_entity_here", ";")
            )

        # create entity that is going to be inserted
        entity = f'<!ENTITY {_entity} "{_content}">'

        # if DOCTYPE exists already, append. Otherwise create DOCTYPE
        if doc_type:
            doc_type += entity + "]>"

        else:
            doc_type = f"<!DOCTYPE Response [\n{entity}]>"

        xml_tree_str = doc_type + xml_tree_str

        return bytearray(xml_tree_str.encode("utf-8"))


def register() -> None:
    plugin_util.register_plugin("insert_dtd", InsertDTD)
