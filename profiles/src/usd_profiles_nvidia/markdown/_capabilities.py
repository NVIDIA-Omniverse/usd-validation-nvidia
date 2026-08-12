# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
from dataclasses import dataclass

from usd_profiles_nvidia.api import Capability, Requirement
from usd_profiles_nvidia.model import Metadata

from ._parser import walk_md
from ._references import ReferencesParser

logger = logging.getLogger(__name__)


class _CapabilityParser(ReferencesParser):

    @property
    def default_name(self) -> str:
        return super().default_name.removeprefix("capability-")

    def run(self) -> Capability | None:
        requirements: list[Requirement] = []
        if requirements_table := self.requirements_table:
            requirements.extend(requirements_table)
        elif requirements_dir := self.requirements_dir:
            logger.warning(f"Capability {self.relpath} has no requirements table, using requirements directory.")
            requirements.extend(requirements_dir)
        else:
            logger.warning(f"Capability {self.relpath} has no requirements table or directory.")
            return None
        return Capability(
            id=self.default_id,
            version=str(self.default_version),
            path=Metadata(path=self.relpath).path,
            requirements=requirements,
        )


@dataclass
class CapabilityParser:
    """
    Parser for a single capability.

    Args:
        root_dir: Sphinx srcdir.
        source_file: The file to parse capabilities from.
    """

    root_dir: str
    source_file: str

    def parse(self) -> Capability | None:
        """
        Parse the capability from the source file. Returns None if the
        source file is not a valid capability file.
        """
        logger.info(f"Parsing capability from: {self.source_file}")
        return _CapabilityParser(self.root_dir, self.source_file).run()


@dataclass
class MdCapabilitiesParser:
    """
    Markdown parser for all capabilities in the root directory.

    Args:
        root_dir: Sphinx srcdir.
        path: The path to the capabilities directory.
    """

    root_dir: str
    path: str

    def parse(self) -> list[Capability]:
        """
        Parse all capabilities from the root directory.
        """
        capabilities: list[Capability] = []
        for source_path in walk_md(self.path):
            filename = os.path.basename(source_path)
            if not filename.startswith("capability-"):
                continue
            if capability := CapabilityParser(self.root_dir, source_path).parse():
                capabilities.append(capability)
        return capabilities


CapabilitiesParser = MdCapabilitiesParser
