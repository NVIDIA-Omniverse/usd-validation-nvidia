# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest
from pathlib import Path

from usd_profiles_nvidia.markdown import RequirementsParser
from usd_profiles_nvidia.model import ExampleResult, ExampleSnippetLanguage


class TestExamplesParser(unittest.TestCase):

    def test_parse_ok(self):
        base_dir = Path(__file__).parent / "resources" / "examples-specs"
        parser = RequirementsParser(root_dir=str(base_dir), paths=[str(base_dir / "requirements")])
        requirements = parser.parse()

        self.assertEqual(len(requirements), 1)
        self.assertIsInstance(requirements[0].examples, tuple)
        self.assertEqual(len(requirements[0].examples), 2)

        self.assertEqual(requirements[0].examples[0].result, ExampleResult.FAILURE)
        self.assertEqual(requirements[0].examples[0].snippet.language, ExampleSnippetLanguage.USD)
        self.assertIn('def Xform "Xform1"', requirements[0].examples[0].snippet.content)
        self.assertEqual("Scattered Xforms without common root", requirements[0].examples[0].display_name)

        self.assertEqual(requirements[0].examples[1].result, ExampleResult.SUCCESS)
        self.assertEqual(requirements[0].examples[1].snippet.language, ExampleSnippetLanguage.USD)
        self.assertIn('def Xform "RootXform"', requirements[0].examples[1].snippet.content)
        self.assertEqual("All Xforms under single root", requirements[0].examples[1].display_name)
