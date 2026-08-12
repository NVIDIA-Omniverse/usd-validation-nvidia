# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import unittest

from usd_profiles_nvidia.markdown import CapabilitiesParser
from usd_profiles_nvidia.model import Compatibility, Tag


class TestCapabilitiesParser(unittest.TestCase):

    def test_parse(self):
        root_dir = os.path.join(os.path.dirname(__file__), "resources", "simple-spec")
        parser = CapabilitiesParser(root_dir=root_dir, path=root_dir)
        capabilities = parser.parse()

        self.assertEqual(len(capabilities), 1)
        self.assertEqual(capabilities[0].id, "geometry")
        self.assertEqual(capabilities[0].version, "1.0.0")
        self.assertEqual(capabilities[0].path, "capabilities/geometry/capability-geometry")
        self.assertEqual(len(capabilities[0].requirements), 1)
        self.assertEqual(capabilities[0].requirements[0].code, "VG.RTX.002")
        self.assertEqual(capabilities[0].requirements[0].display_name, "usdgeom-mesh-count")
        self.assertEqual(capabilities[0].requirements[0].message, "Use appropriate mesh count for scene.")
        self.assertEqual(capabilities[0].requirements[0].compatibility, Compatibility.RTX.display_name)
        self.assertEqual(capabilities[0].requirements[0].tags, (Tag.PERFORMANCE.display_name,))
