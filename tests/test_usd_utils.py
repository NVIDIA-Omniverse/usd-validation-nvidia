# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest import mock

from pxr import Sdf, Sdr, Usd

from usd_validation_nvidia import get_sdf_type_for_shader_property
import usd_validation_nvidia._usd_utils as usd_utils


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

    def test_returns_sdf_type_from_indicator(self):
        type_indicator = mock.Mock()
        type_indicator.HasSdfType.return_value = True
        type_indicator.GetSdfType.return_value = Sdf.ValueTypeNames.Color3f
        shader_property = mock.Mock()
        shader_property.GetTypeAsSdfType.return_value = type_indicator

        result = get_sdf_type_for_shader_property(shader_property)

        self.assertEqual(result, Sdf.ValueTypeNames.Color3f)

    def test_returns_sdr_type_from_indicator(self):
        type_indicator = mock.Mock(spec_set=["HasSdfType", "GetSdrType"])
        type_indicator.HasSdfType.return_value = False
        type_indicator.GetSdrType.return_value = "float"
        shader_property = mock.Mock()
        shader_property.GetTypeAsSdfType.return_value = type_indicator

        result = get_sdf_type_for_shader_property(shader_property)

        self.assertEqual(result, Sdf.ValueTypeNames.Float)

    def test_returns_ndr_type_from_indicator(self):
        type_indicator = mock.Mock(spec_set=["HasSdfType", "GetNdrType"])
        type_indicator.HasSdfType.return_value = False
        type_indicator.GetNdrType.return_value = "token"
        shader_property = mock.Mock()
        shader_property.GetTypeAsSdfType.return_value = type_indicator

        result = get_sdf_type_for_shader_property(shader_property)

        self.assertEqual(result, Sdf.ValueTypeNames.Token)

    def test_returns_token_for_unknown_indicator(self):
        type_indicator = mock.Mock(spec_set=["HasSdfType"])
        type_indicator.HasSdfType.return_value = False
        shader_property = mock.Mock()
        shader_property.GetTypeAsSdfType.return_value = type_indicator

        result = get_sdf_type_for_shader_property(shader_property)

        self.assertEqual(result, Sdf.ValueTypeNames.Token)

    def test_returns_legacy_type_indicator_value(self):
        type_indicator = mock.MagicMock()
        type_indicator.__getitem__.side_effect = lambda index: (Sdf.ValueTypeNames.Token, "float")[index]
        shader_property = mock.Mock()
        shader_property.GetTypeAsSdfType.return_value = type_indicator

        with mock.patch.object(usd_utils.Usd, "GetVersion", return_value=(0, 24, 10)):
            result = get_sdf_type_for_shader_property(shader_property)
        self.assertEqual(result, Sdf.ValueTypeNames.Float)
