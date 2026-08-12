# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import importlib
import importlib.resources
import os
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory


class TestWheel(unittest.TestCase):

    def test_sphinx_artifacts(self):
        style_css = importlib.resources.files("usd_profiles_nvidia") / "sphinx" / "static" / "_static" / "_style.css"

        self.assertTrue(style_css.is_file(), f"Expected packaged Sphinx CSS at {style_css}")

    @unittest.skipUnless(__name__ == "__main__", "Run directly with 'python tests/test_wheel.py' to enable")
    def test_codegen(self):
        with TemporaryDirectory() as tmpdirname:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "usd_profiles_nvidia.codegen",
                    "--docs-root",
                    "tests/resources/simple-spec",
                    "--destination-dir",
                    tmpdirname,
                    "--namespace",
                    "test_codegen",
                ]
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, "test_codegen", "__init__.py")))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, "test_codegen", "_requirements.py")))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, "test_codegen", "_capabilities.py")))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, "test_codegen", "_profiles.py")))
            self.assertTrue(os.path.exists(os.path.join(tmpdirname, "test_codegen", "_features.py")))

            sys.path.insert(0, tmpdirname)
            try:
                test_codegen = importlib.import_module("test_codegen")

                self.assertTrue(hasattr(test_codegen.Capabilities, "GEOMETRY"))
                self.assertEqual(test_codegen.Capabilities.GEOMETRY.id, "geometry")
                self.assertTrue(hasattr(test_codegen.Requirements, "VG_RTX_002_V1_0_0"))
                self.assertEqual(test_codegen.Requirements.VG_RTX_002_V1_0_0.code, "VG.RTX.002")
                self.assertEqual(test_codegen.Requirements.VG_RTX_002_V1_0_0.version, "1.0.0")
            finally:
                sys.path.pop(0)
