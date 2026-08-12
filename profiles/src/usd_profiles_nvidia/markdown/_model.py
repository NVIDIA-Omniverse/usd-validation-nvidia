# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import ClassVar

__all__ = [
    "Bullet",
    "BulletList",
    "Document",
    "Fence",
    "Link",
    "Section",
    "Sections",
    "Table",
    "TableCell",
    "TableRow",
]


@dataclass(slots=True)
class TableCell:
    """A table cell is a cell in a table."""

    content: str


class TableRow(list[TableCell]):
    """A table row is a row in a table."""

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"


class Table(list[TableRow]):
    """A table is a list of rows."""

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {}
        for row in self:
            values: list[str] = [cell.content for cell in row]
            key: str = values[0].lower()
            value: str = values[1]
            data[key] = value
        return data


@dataclass(slots=True)
class Fence:
    """A fence is a code block."""

    info: str
    content: str

    def __post_init__(self):
        self.content = self.content.strip()

    def is_directive(self) -> bool:
        return self.info.startswith("{") and self.info.endswith("}")

    @property
    def directive(self) -> str | None:
        if self.is_directive():
            return self.info[1:-1]
        return None

    @property
    def lines(self) -> list[str]:
        return [line.strip() for line in self.content.split("\n") if line.strip()]


@dataclass(slots=True)
class Link:
    """A link is a link in a document."""

    href: str
    text: str | None = None


@dataclass(slots=True)
class Bullet:
    """A bullet is a bullet in a document."""

    content: str = ""
    links: list[Link] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)

    def flatten(self) -> list[Bullet]:
        bullets: list[Bullet] = [Bullet(content=self.content, links=self.links)]
        for bullet in self.bullets:
            bullets.extend(bullet.flatten())
        return bullets


class BulletList(list[Bullet]):
    """A bullet list is a list of bullets in a document."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def flatten(self) -> list[Bullet]:
        bullets: list[Bullet] = []
        for bullet in self:
            bullets.extend(bullet.flatten())
        return bullets


class WalkSectionsMixin:
    def walk_sections(self) -> Generator[Section, None, None]:
        """Walk and yield each section including self."""
        yield self
        for section in self.sections:
            yield from section.walk_sections()


@dataclass(slots=True)
class Section(WalkSectionsMixin):
    """A section is a section in a document."""

    level: int = 1
    title: str = ""
    content: str = ""
    tables: list[Table] = field(default_factory=list)
    fences: list[Fence] = field(default_factory=list)
    bullets: list[BulletList] = field(default_factory=list)
    sections: Sections = field(default_factory=lambda: Sections())


class Sections(list[Section]):
    """A sections is a list of sections in a document."""

    def get(self, key: str, default: Section | None = None) -> Section | None:
        """Get a section by name, returning default if not found."""
        for section in self:
            if section.title.lower() == key.lower():
                return section
        return default


@dataclass(slots=True)
class Document(WalkSectionsMixin):
    """A markdown document."""

    sections: Sections = field(default_factory=Sections)
    content: str = ""
    tables: list[Table] = field(default_factory=list)
    fences: list[Fence] = field(default_factory=list)
    bullets: list[BulletList] = field(default_factory=list)
    level: ClassVar[int] = 0
