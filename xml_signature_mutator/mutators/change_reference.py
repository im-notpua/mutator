import io
import logging
import random
from dataclasses import dataclass

from lxml import etree
from lxml.etree import XMLSyntaxError
from plugin_base import plugin_util
from plugin_base.base_mutator import BaseMutator


@dataclass
class ChangeReference(BaseMutator):
    logger = logging.getLogger(__name__)

    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:

        # find reference element
        prefix_map = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
        references = xml_tree.findall(".//ds:Reference", prefix_map)

        if references:
            reference = random.choice(references)
        else:
            self.logger.debug("Found no Reference element in document. Skipping mutation step,")
            return input_xml

        # find all IDs
        list_of_ids = []
        for node in xml_tree.getiterator():
            if node.attrib.get("ID"):
                list_of_ids.append("#" + node.attrib.get("ID"))

        # remove ID it currently holds
        if reference.attrib.get("URI") in list_of_ids:
            list_of_ids.remove(reference.attrib.get("URI"))
        if list_of_ids:
            xml_id = random.choice(list_of_ids)
        else:
            self.logger.debug("Found no ID attribute in document. Skipping mutation step,")
            return input_xml

        reference.attrib.update({"URI": xml_id})

        # replace attribute of Reference
        self.logger.debug("Changing reference of element %s to %s.", reference, xml_id)

        return bytearray(self._serialize_xml(xml_tree), encoding="utf-8")


def register() -> None:
    plugin_util.register_plugin("change_reference", ChangeReference)
