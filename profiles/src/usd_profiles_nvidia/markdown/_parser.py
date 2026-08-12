# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import cache, cached_property, singledispatch

from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode

from usd_profiles_nvidia.model import Naming, Version

from ._model import (
    Bullet,
    BulletList,
    Document,
    Fence,
    Link,
    Section,
    Table,
    TableCell,
    TableRow,
)

logger = logging.getLogger(__name__)


@cache
def get_markdown_parser() -> MarkdownIt:
    return MarkdownIt().enable("table")


@singledispatch
def walk_md(path: str) -> list[str]:
    """
    Walk a path (file or directory) and return all .md file paths.

    Args:
        path: Single path (str) or list of paths (files and/or directories)

    Returns:
        List of absolute paths to .md files
    """
    # Single path case: the actual implementation
    md_files: list[str] = []
    if os.path.isfile(path):
        if path.endswith(".md"):
            md_files.append(path)
    elif os.path.isdir(path):
        for source_dir, _, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith(".md"):
                    md_files.append(os.path.join(source_dir, filename))
    return md_files


@walk_md.register(list)
def _(paths: list[str]) -> list[str]:
    """Handle list of paths by applying single-path logic to each."""
    md_files: list[str] = []
    for path in paths:
        md_files.extend(walk_md(path))
    return md_files


@dataclass
class DocumentParser:
    path: str

    def parse(self) -> Document:
        with open(self.path, encoding="utf-8") as file:
            content: str = file.read()
            tokens: list[Token] = get_markdown_parser().parse(content)
            root: SyntaxTreeNode = SyntaxTreeNode(tokens)
            return self._parse_tree(root)

    def _text_content(self, node: SyntaxTreeNode) -> str:
        values: list[str] = []
        for child in node.children:
            match child.type:
                case "paragraph":
                    values.append(self._text_content(child))
                case "inline" | "text":
                    values.append(child.content)
        return "".join(values)

    def _links_content(self, node: SyntaxTreeNode) -> list[Link]:
        links: list[Link] = []
        for child in node.children:
            match child.type:
                case "paragraph" | "inline":
                    links.extend(self._links_content(child))
                case "link":
                    links.append(Link(href=child.attrs["href"], text=self._text_content(child)))
        return links

    def _parse_section(self, node: SyntaxTreeNode) -> Section:
        section: Section = Section(level=int(node.tag[1:]), title=self._text_content(node))
        return section

    def _parse_table(self, node: SyntaxTreeNode) -> Table:
        table: Table = Table()
        for section_node in node.children:
            for row_node in section_node.children:
                row: TableRow = TableRow()
                for cell_node in row_node.children:
                    cell: TableCell = TableCell(content=self._text_content(cell_node))
                    row.append(cell)
                table.append(row)
        return table

    def _parse_bullet_list(self, node: SyntaxTreeNode) -> BulletList:
        bullet_list: BulletList = BulletList()
        for bullet_node in node.children:
            bullet: Bullet = Bullet(
                content=self._text_content(bullet_node),
                links=self._links_content(bullet_node),
            )
            for item_node in bullet_node.children:
                if item_node.type == "bullet_list":
                    bullet.bullets.extend(self._parse_bullet_list(item_node))
            bullet_list.append(bullet)
        return bullet_list

    def _parse_fence(self, node: SyntaxTreeNode) -> Fence:
        return Fence(info=node.info, content=node.content)

    def _parse_tree(self, root: SyntaxTreeNode) -> Document:
        document: Document = Document()
        stack: list[Section | Document] = [document]
        for node in root.children:
            top: Section | Document = stack[-1]
            match node.type:
                case "heading":
                    section = self._parse_section(node)
                    while stack and stack[-1].level >= section.level:
                        stack.pop()
                    stack[-1].sections.append(section)
                    stack.append(section)
                case "paragraph":
                    top.content += self._text_content(node)
                case "table":
                    top.tables.append(self._parse_table(node))
                case "bullet_list":
                    top.bullets.append(self._parse_bullet_list(node))
                case "fence":
                    top.fences.append(self._parse_fence(node))
        return document


@dataclass
class FileParser:
    root_dir: str
    source_file: str

    @property
    def relpath(self) -> str:
        """
        Returns the relative path of the source file from the source directory.
        """
        return "/" + os.path.relpath(self.source_file, self.root_dir).replace("\\", "/")

    @property
    def default_name(self) -> str:
        """
        Returns the default name, that is the filename without the extension.
        """
        basename = os.path.basename(self.source_file)
        default_name = os.path.splitext(basename)[0]
        return default_name

    @property
    def default_id(self) -> str:
        """
        Returns the default id, that is the identifier of the default name.
        """
        return Naming.identifier(self.default_name)

    @cached_property
    def document(self) -> Document:
        """
        Returns the document parsed from the source file.
        """
        return DocumentParser(self.source_file).parse()

    @property
    def default_version(self) -> Version:
        """
        Returns the default version of the document.
        """
        return Version(1, 0, 0)

    @cached_property
    def main_section(self) -> Section:
        """
        Returns the main section of the document.
        """
        if len(self.document.sections) == 0:
            raise ValueError(f"{self.relpath} has no sections.")
        elif len(self.document.sections) > 1:
            logger.warning(f"{self.relpath} has more than one section.")
        return self.document.sections[0]

    @property
    def title(self) -> str:
        """
        Returns the title of the document, i.e.:

        ```
        # Title
        ```
        """
        if not self.main_section.title:
            raise ValueError(f"{self.relpath} has no title.")
        return self.main_section.title

    @property
    def description(self) -> str:
        """
        Returns the description of the document, i.e.:

        ```
        # Title

        Description
        ```
        """
        if not self.main_section.content:
            raise ValueError(f"{self.relpath} has no content.")
        return self.main_section.content

    @property
    def summary_content(self) -> str:
        """
        Returns the summary content of the document, i.e.:

        ```
        # Title

        Description

        ## Summary

        Summary content
        ```
        """
        summary_section: Section | None = self.main_section.sections.get("summary")
        if summary_section is None:
            raise ValueError(f"{self.relpath} has no summary section.")
        return summary_section.content

    @property
    def description_content(self) -> str:
        """
        Returns the description content of the document, i.e.:

        ```
        # Title

        Description

        ## Description

        Description content
        ```
        """
        description_section: Section | None = self.main_section.sections.get("description")
        if description_section is None:
            raise ValueError(f"{self.relpath} has no description section.")
        return description_section.content

    @property
    def overview_content(self) -> str:
        """
        Returns the overview content of the document, i.e.:

        ```
        # Title

        ## Overview

        Overview content
        ```
        """
        overview_section: Section | None = self.main_section.sections.get("overview")
        if overview_section is None:
            logger.warning(f"{self.relpath} has no overview section.")
            return ""
        return overview_section.content

    @property
    def main_table(self) -> Table:
        """
        Returns the main table of the document, i.e.:

        ```
        # Title

        | Key   | Value |
        | ----- | ----- |
        | code  | X.001 |
        ```
        """
        if not self.main_section.tables:
            raise ValueError(f"{self.relpath} has no tables in the main section.")
        return self.main_section.tables[0]

    def normpath(self, relpath: str) -> str | None:
        """
        Returns the normalized path of the given relative path, or None if it does not exist.

        Args:
            relpath: The relative path to normalize.

        Returns:
            The normalized path, or None if it does not exist.
        """
        dirname: str = os.path.dirname(self.source_file)
        abspath: str = os.path.join(dirname, relpath)
        normpath: str = os.path.normpath(abspath)
        if os.path.exists(normpath):
            return normpath
        elif os.path.exists(normpath + ".md"):
            return normpath + ".md"
        else:
            return None
