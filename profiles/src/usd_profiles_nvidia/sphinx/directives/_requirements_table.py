# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
from typing import ClassVar

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

from usd_profiles_nvidia.api import Capability, Requirement
from usd_profiles_nvidia.markdown import CapabilityParser
from usd_profiles_nvidia.model import tag_priority

from ._common import get_directives_environment

logger = logging.getLogger(__name__)


class RequirementsTableDirective(SphinxDirective):
    """
    A custom directive that generates requirement tables programmatically.

    Default usage:
        ```{requirements-table}
        ```

    Usage with inline content:
        ```{requirements-table}

        requirements/hierarchy-has-root.md
        requirements/hierarchy-has-children.md
        ```
    """

    has_content: ClassVar[bool] = True

    def run(self) -> list[nodes.Node]:
        root_dir: str = self.env.srcdir
        source, _ = self.state_machine.get_source_and_line(self.lineno)
        doc_file: str = source if os.path.isabs(source) else os.path.join(root_dir, source)

        capability: Capability | None = CapabilityParser(root_dir, doc_file).parse()
        if capability is None:
            logger.warning(f"requirements-table directive used, but document {doc_file} is not a capability")
            return []
        elif not capability.requirements:
            logger.warning(f"requirements-table directive used, but document {doc_file} has no requirements")
            return []

        requirements: list[Requirement] = capability.requirements
        table_content: str = self._generate_table_content(requirements)

        env = self.state.document.settings.env
        docname: str = env.docname
        for requirement in requirements:
            if requirement.path:
                env.included[docname].add(requirement.path)

        try:
            string_list = StringList(table_content.split("\n"), source="requirements-table")
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
    app.add_directive("requirements-table", RequirementsTableDirective)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
