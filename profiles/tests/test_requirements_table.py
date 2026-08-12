# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from usd_profiles_nvidia.model import Compatibility, Tag


class TestRequirementsTableDirective(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.temp_dir, "src")
        self.build_dir = os.path.join(self.temp_dir, "build")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _build_sphinx_project(self, resources_folder: str) -> None:
        from sphinx.application import Sphinx

        resources_dir = Path(__file__).parent / "resources" / resources_folder
        shutil.copytree(resources_dir, self.src_dir)
        with open(os.path.join(self.src_dir, "conf.py"), "w") as f:
            f.write("extensions = [" + os.linesep)
            f.write("    'myst_parser'," + os.linesep)
            f.write("    'usd_profiles_nvidia.sphinx.ext'," + os.linesep)
            f.write("]" + os.linesep)
            f.write("myst_enable_extensions = ['colon_fence']" + os.linesep)

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

    def _read_html(self, relative_path: str) -> str:
        html_path = os.path.join(self.build_dir, relative_path)
        self.assertTrue(os.path.exists(html_path), f"Expected HTML file at {html_path}")
        with open(html_path, encoding="utf-8") as f:
            return f.read()

    def test_simple_spec(self):
        self._build_sphinx_project("simple-spec")

        html = self._read_html("capabilities/geometry/capability-geometry.html")
        self.assertIn(Tag.PERFORMANCE.emoji, html)
        self.assertIn(Compatibility.RTX.title, html)
        self.assertIn("Use appropriate mesh count for scene", html)
        self.assertIn(
            "https://nvidia-omniverse.github.io/usd-validation-nvidia/validation/docs/requirements.html#vg-rtx-002",
            html,
        )

    def test_capability_flat(self):
        self._build_sphinx_project("capability-flat")

        html = self._read_html("geometry/capability-geometry.html")
        self.assertIn(Tag.PERFORMANCE.emoji, html)
        self.assertIn(Compatibility.RTX.title, html)
        self.assertIn("Use appropriate mesh count for scene", html)

    def test_capability_toctree(self):
        self._build_sphinx_project("capability-toctree")

        html = self._read_html("geometry/capability-geometry.html")
        self.assertIn(Tag.PERFORMANCE.emoji, html)
        self.assertIn(Compatibility.RTX.title, html)
        self.assertIn("Use appropriate mesh count for scene", html)
