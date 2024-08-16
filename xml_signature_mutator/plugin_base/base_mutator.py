import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Tuple

from lxml import etree


@dataclass(kw_only=True)
class BaseMutator(ABC):
    identifier: str
    logger = logging.getLogger()
    weight: int = 1

    def init(self, seed: bytearray) -> None:
        """Initialized this mutator. Called once per mutation."""
        random.seed(str(seed))

    def __post_init__(self) -> None:
        # configure parser to not strip CDATA or resolve entities.
        parser = etree.XMLParser(strip_cdata=False, resolve_entities=False, remove_comments=False)
        etree.set_default_parser(parser)

    @abstractmethod
    def mutate(
        self,
        input_xml: bytearray,
        xml_tree: etree._Element,
        additional_buffer: bytearray,
        max_size: int,
    ) -> bytearray:
        """Applies mutation functions and returns the result."""

    def is_subtree_of(self, child: Any, parent: Any) -> bool:
        """_summary_

        Args:
            child (Any): Element that we check if it is a child of parent
            parent (Any): Element who's children are searched

        Returns:
            bool: True, if child is contained in parent. Otherwise, False.
        """
        if child in parent.iterdescendants():
            return True
        return False

    # All code following this comment.
    # Copyright 2021 Jost Rossel
    # Licensed under the Apache License, Version 2.0

    def _pick_element(self, xml_tree: Any, exclude_root_node: bool = False) -> Tuple[int, Any]:
        """Pick a random element from the current document"""
        # Get a list of all elements, but nodes like PI and comments
        elems = list(xml_tree.getroot().iter(tag=etree.Element))

        # Is the root node excluded?
        if exclude_root_node:
            start = 1
        else:
            start = 0

        # Pick a random element
        try:
            elem_id = random.randint(start, len(elems) - 1)
            elem = elems[elem_id]
            self.logger.debug("Selected random element from file: %s", elem)
        except ValueError:
            # Should only occurs if "exclude_root_node = True"
            return (None, None)

        return (elem_id, elem)

    def _serialize_xml(self, tree: Any) -> bytearray:
        """Serialize a XML document. Basic wrapper around lxml.tostring()"""
        return etree.tostring(tree, with_tail=False, xml_declaration=False, encoding="unicode")
