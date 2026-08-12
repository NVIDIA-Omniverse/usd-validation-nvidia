# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
from functools import cached_property

from usd_profiles_nvidia.api import Requirement, RequirementRef
from usd_profiles_nvidia.model import IdVersion

from ._model import BulletList, Section
from ._parser import FileParser
from ._requirements import RequirementsParser


class ReferencesParser(FileParser):

    @cached_property
    def requirements_section(self) -> Section | None:
        if len(self.document.sections) != 1:
            return None
        return self.document.sections[0].sections.get("requirements")

    @property
    def requirements_table(self) -> list[Requirement] | None:
        """
        Returns the requirements declared in the `requirements-table` directive.
        """
        if self.requirements_section is None:
            return None

        for fence in self.requirements_section.fences:
            if fence.directive == "requirements-table":
                paths: list[str] = []

                lines: list[str] = fence.lines
                if not lines:
                    default_path: str | None = self.normpath("requirements")
                    if default_path is None:
                        raise ValueError("`requirements-table` directive path `requirements` does not exist.")
                    paths.append(default_path)

                for relpath in lines:
                    path: str | None = self.normpath(relpath)
                    if path is None:
                        raise ValueError(f"`requirements-table` directive path `{relpath}` does not exist.")
                    paths.append(path)

                return RequirementsParser(self.root_dir, paths).parse()
        return None

    @property
    def requirements_dir(self) -> list[Requirement] | None:
        """
        Returns the requirements declared in the requirements directory.
        """
        default_path: str | None = self.normpath("requirements")
        if default_path is None:
            return None
        return RequirementsParser(self.root_dir, [default_path]).parse()

    @property
    def features_table(self) -> list[RequirementRef] | None:
        """
        Returns the requirements declared in the `features-table` directive.
        """
        if self.requirements_section is None:
            return None

        for fence in self.requirements_section.fences:
            if fence.directive == "features-table":
                lines: list[str] = fence.lines
                if not lines:
                    return []

                versions: list[RequirementRef] = []
                for line in lines:
                    id_version = IdVersion.parse(line)
                    version = str(id_version.version) if id_version.version is not None else None
                    versions.append(RequirementRef(id_version.id, version))
                return versions
        return None

    def get_requirements_list(self, section: Section) -> list[Requirement] | None:
        """
        Returns the requirements declared in a bullet list of links.
        """
        if not section.bullets:
            return None
        bullet_list: BulletList = section.bullets[0]
        paths: list[str] = []
        for bullet in bullet_list.flatten():
            for link in bullet.links:
                path: str | None = self.normpath(link.href)
                if path is None:
                    raise ValueError(f"Requirement path {link.href} does not exist.")
                basename: str = os.path.basename(path)
                if basename.startswith("capability-"):
                    continue
                elif basename.endswith(".py"):
                    continue
                else:
                    paths.append(path)
        return RequirementsParser(self.root_dir, paths).parse()

    @property
    def requirements_list(self) -> list[Requirement] | None:
        """
        Returns the requirements declared in a bullet list of links.
        """
        if self.requirements_section is None:
            return None
        return self.get_requirements_list(self.requirements_section)
