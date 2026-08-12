# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia.model import Compatibility, Tag


class TestFeaturesTableDirective(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.temp_dir, "src")
        self.build_dir = os.path.join(self.temp_dir, "build")

        resources_dir = Path(__file__).parent / "resources" / "simple-profile"
        shutil.copytree(resources_dir, self.src_dir)

        with open(os.path.join(self.src_dir, "conf.py"), "w") as f:
            f.write("extensions = [" + os.linesep)
            f.write("    'myst_parser'," + os.linesep)
            f.write("    'usd_profiles_nvidia.sphinx.ext'," + os.linesep)
            f.write("]" + os.linesep)
            f.write("myst_enable_extensions = ['colon_fence']" + os.linesep)

        with open(os.path.join(self.src_dir, "index.md"), "w") as f:
            f.write("# Index" + os.linesep)
            f.write("```{toctree}" + os.linesep)
            f.write("profile-simple" + os.linesep)
            f.write("capabilities/capability-hierarchy" + os.linesep)
            f.write("features/simple" + os.linesep)
            f.write("```" + os.linesep)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_features_table_generates_html(self):
        from sphinx.application import Sphinx

        app = Sphinx(
            srcdir=self.src_dir,
            confdir=self.src_dir,
            outdir=self.build_dir,
            doctreedir=os.path.join(self.build_dir, "doctrees"),
            buildername="html",
            status=None,
            warning=None,
        )
        app.build()

        html_path = os.path.join(self.build_dir, "features", "simple.html")
        self.assertTrue(os.path.exists(html_path), f"Expected HTML file at {html_path}")

        with open(html_path, encoding="utf-8") as f:
            html = f.read()

        # Check requirement from hierarchy-has-root.md is rendered in the features table
        self.assertIn(Tag.ESSENTIAL.emoji, html)
        self.assertIn(Compatibility.OPENUSD.title, html)
        self.assertIn("Prim hierarchy must have a single root prim", html)
        self.assertIn(
            "https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/requirements.html#hi-001",
            html,
        )
