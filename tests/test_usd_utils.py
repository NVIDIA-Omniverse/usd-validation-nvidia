# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from pxr import Sdf, Sdr, Usd

from nvidia_usd_validation import get_sdf_type_for_shader_property


@unittest.skipIf(Usd.GetVersion() < (0, 24, 11), "SdfTypeIndicator not available before USD 24.11")
class GetSdfTypeForShaderPropertyTest(unittest.TestCase):
    def test_returns_sdf_type(self):
        node = Sdr.Registry().GetShaderNodeByName("UsdPreviewSurface")
        if node is None:
            self.skipTest("UsdPreviewSurface not found in Sdr registry")
        prop = node.GetShaderInput("roughness")
        result = get_sdf_type_for_shader_property(prop)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, Sdf.ValueTypeName())
