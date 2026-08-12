# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
from typing import ClassVar

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

from usd_profiles_nvidia.api import Feature, Requirement
from usd_profiles_nvidia.markdown import FeatureParser
from usd_profiles_nvidia.model import tag_priority
from usd_profiles_nvidia.store import RequirementStore

from ._common import get_directives_environment

logger = logging.getLogger(__name__)


class FeaturesTableDirective(SphinxDirective):
    """
    A custom directive that generates feature tables programmatically.

    Usage (with JSON file):
        ```{features-table}
        ```

    Usage (with inline content):
        ```{features-table}
        HI.001
        HI.002
        ```
    """

    has_content: ClassVar[bool] = True

    def run(self) -> list[nodes.Node]:
        root_dir: str = self.env.srcdir
        doc_file: str = self.env.doc2path(self.env.docname)

        feature: Feature | None = FeatureParser(root_dir, doc_file).parse()
        if feature is None:
            logger.warning(f"features-table directive used, but document {doc_file} is not a feature")
            return []
        elif not feature.requirements:
            logger.warning(f"features-table directive used, but document {doc_file} has no requirements")
            return []

        requirement_store: RequirementStore = self.env.requirement_store
        requirements: list[Requirement] = requirement_store.find_all(feature.requirements)

        table_content: str = self._generate_table_content(requirements)
        try:
            string_list = StringList(table_content.split("\n"), source="features-table")
            result = []
            self.state.nested_parse(string_list, 0, result)
            return result
        except Exception as e:
            logger.error(f"Error parsing generated table content: {e}")
            return []

    def _generate_table_content(self, requirements: list[Requirement]) -> str:
        """
        Generate the table content using the Jinja2 template.

        Args:
            requirements: List of requirements to generate the table content for

        Returns:
            The table content as a string
        """
        template = get_directives_environment().get_template("_requirements_table.md.j2")
        return template.render(requirements=sorted(requirements, key=lambda x: (tag_priority(x.tags), x.code)))


def setup(app) -> dict[str, bool]:
    app.add_directive("features-table", FeaturesTableDirective)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
