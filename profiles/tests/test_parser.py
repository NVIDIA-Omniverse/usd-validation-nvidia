# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia.markdown import DocumentParser


class TestDocumentParser(unittest.TestCase):
    def _parse_md(self, content: str):
        """Write content to a temporary .md file, parse it, and return the Document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.md")
            Path(path).write_text(content, encoding="utf-8")
            return DocumentParser(path=path).parse()

    def test_single_section(self):
        md = """
# My Section
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "My Section")
        self.assertEqual(doc.sections[0].content, "")
        self.assertEqual(doc.sections[0].tables, [])
        self.assertEqual(len(doc.sections[0].sections), 0)

    def test_single_section_with_paragraph(self):
        md = """
# My Section

A paragraph of text.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "My Section")
        self.assertIn("A paragraph of text", doc.sections[0].content)

    def test_preamble_paragraph_before_first_heading(self):
        md = """
Intro paragraph before any heading.

# My Section
"""
        doc = self._parse_md(md)
        self.assertEqual(doc.content, "Intro paragraph before any heading.")
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "My Section")

    def test_preamble_blocks_before_first_heading(self):
        md = """
| Key   | Value |
| ----- | ----- |
| code  | X.001 |

```python
x = 1
```

- Item one.

# My Section
"""
        doc = self._parse_md(md)
        self.assertEqual(doc.tables[0].to_dict()["code"], "X.001")
        self.assertEqual(doc.fences[0].content, "x = 1")
        self.assertEqual(doc.bullets[0][0].content, "Item one.")
        self.assertEqual(doc.sections[0].title, "My Section")

    def test_single_section_with_multiple_paragraphs(self):
        md = """
# My Section

A paragraph of text.

Another paragraph of text.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "My Section")
        self.assertIn("A paragraph of text", doc.sections[0].content)
        self.assertIn("Another paragraph of text", doc.sections[0].content)

    def test_single_section_with_table(self):
        md = """
# With Table

| Key   | Value |
| ----- | ----- |
| code  | X.001 |
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Table")
        self.assertEqual(len(doc.sections[0].tables), 1)
        table = doc.sections[0].tables[0]
        self.assertEqual(len(table), 2)
        data = table.to_dict()
        self.assertEqual(len(data), 2)
        self.assertEqual(data["key"], "Value")
        self.assertEqual(data["code"], "X.001")

    def test_single_section_with_subsection_and_paragraph(self):
        md = """
# Parent

## Child

Content in the subsection.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        parent = doc.sections[0]
        self.assertEqual(parent.title, "Parent")
        self.assertEqual(len(parent.sections), 1)
        child = parent.sections[0]
        self.assertEqual(child.title, "Child")
        self.assertIn("Content in the subsection", child.content)

    def test_single_section_with_fence_code(self):
        md = """
# With Code

```python
x = 1
```
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Code")
        self.assertEqual(len(doc.sections[0].fences), 1)
        fence = doc.sections[0].fences[0]
        self.assertEqual(fence.info, "python")
        self.assertIn("x = 1", fence.content)

    def test_single_section_with_directive_fence(self):
        md = """
# With Directive

```{note}
This is a note.
```
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Directive")
        self.assertEqual(len(doc.sections[0].fences), 1)
        fence = doc.sections[0].fences[0]
        self.assertTrue(fence.is_directive())
        self.assertEqual(fence.directive, "note")
        self.assertIn("This is a note", fence.content)

    def test_single_section_with_multiple_subsections(self):
        md = """
# Parent

## First

Content one.

## Second

Content two.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        parent = doc.sections[0]
        self.assertEqual(parent.title, "Parent")
        self.assertEqual(len(parent.sections), 2)
        self.assertEqual(parent.sections[0].title, "First")
        self.assertIn("Content one", parent.sections[0].content)
        self.assertEqual(parent.sections[1].title, "Second")
        self.assertIn("Content two", parent.sections[1].content)

    def test_single_section_with_bullet_list(self):
        md = """
# With Bullet List

- Item one.
- Item two.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Bullet List")
        self.assertEqual(len(doc.sections[0].bullets), 1)
        bullet_list = doc.sections[0].bullets[0]
        self.assertEqual(len(bullet_list), 2)
        self.assertEqual(bullet_list[0].content, "Item one.")
        self.assertEqual(bullet_list[1].content, "Item two.")

    def test_single_section_with_bullet_list_with_link(self):
        md = """
# With Bullet List with Link

- Check first item: [Item one](link-one).
- Check second item: [Item two](link-two).
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Bullet List with Link")
        self.assertEqual(len(doc.sections[0].bullets), 1)
        bullet_list = doc.sections[0].bullets[0]
        self.assertEqual(len(bullet_list), 2)
        self.assertEqual(bullet_list[0].content, "Check first item: [Item one](link-one).")
        self.assertEqual(bullet_list[1].content, "Check second item: [Item two](link-two).")
        self.assertEqual(len(bullet_list[0].links), 1)
        self.assertEqual(bullet_list[0].links[0].href, "link-one")
        self.assertEqual(bullet_list[0].links[0].text, "Item one")
        self.assertEqual(len(bullet_list[1].links), 1)
        self.assertEqual(bullet_list[1].links[0].href, "link-two")
        self.assertEqual(bullet_list[1].links[0].text, "Item two")

    def test_single_section_with_bullet_list_with_sublist(self):
        md = """
# With Bullet List with Sublist

- Item one.
  - Subitem one.
  - Subitem two.
- Item two.
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Bullet List with Sublist")
        self.assertEqual(len(doc.sections[0].bullets), 1)
        bullet_list = doc.sections[0].bullets[0]
        self.assertEqual(len(bullet_list), 2)
        self.assertEqual(bullet_list[0].content, "Item one.")
        self.assertEqual(bullet_list[1].content, "Item two.")
        self.assertEqual(len(bullet_list[0].bullets), 2)
        self.assertEqual(bullet_list[0].bullets[0].content, "Subitem one.")
        self.assertEqual(bullet_list[0].bullets[1].content, "Subitem two.")

    def test_single_section_with_bullet_list_with_link_in_sublist(self):
        md = """
# With Bullet List with Link in Sublist

- Item one.
  - Subitem one: [Subitem one link](subitem-one-link).
  - Subitem two: [Subitem two link](subitem-two-link).
"""
        doc = self._parse_md(md)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "With Bullet List with Link in Sublist")
        self.assertEqual(len(doc.sections[0].bullets), 1)
        bullet_list = doc.sections[0].bullets[0]
        self.assertEqual(len(bullet_list), 1)
        self.assertEqual(bullet_list[0].content, "Item one.")
        self.assertEqual(len(bullet_list[0].links), 0)
        self.assertEqual(len(bullet_list[0].bullets), 2)
        self.assertEqual(bullet_list[0].bullets[0].content, "Subitem one: [Subitem one link](subitem-one-link).")
        self.assertEqual(bullet_list[0].bullets[1].content, "Subitem two: [Subitem two link](subitem-two-link).")
        self.assertEqual(len(bullet_list[0].bullets[0].links), 1)
        self.assertEqual(bullet_list[0].bullets[0].links[0].href, "subitem-one-link")
        self.assertEqual(bullet_list[0].bullets[0].links[0].text, "Subitem one link")
        self.assertEqual(len(bullet_list[0].bullets[1].links), 1)
        self.assertEqual(bullet_list[0].bullets[1].links[0].href, "subitem-two-link")
        self.assertEqual(bullet_list[0].bullets[1].links[0].text, "Subitem two link")
