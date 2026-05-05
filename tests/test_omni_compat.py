# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest


class TestOmniAssetValidatorShim(unittest.TestCase):
    def test_class_identity(self):
        from omni.asset_validator import ValidationEngine
        from nvidia_usd_validation import ValidationEngine as NvValidationEngine
        self.assertIs(ValidationEngine, NvValidationEngine)

    def test_all_identity(self):
        import omni.asset_validator
        import nvidia_usd_validation
        self.assertEqual(omni.asset_validator.__all__, nvidia_usd_validation.__all__)

    def test_from_import(self):
        from omni.asset_validator import ValidationEngine  # noqa: F401


class TestOmniCapabilitiesShim(unittest.TestCase):
    def test_class_identity(self):
        from omni.capabilities import Capabilities
        from nvidia_usd_validation.capabilities import Capabilities as NvCapabilities
        self.assertIs(Capabilities, NvCapabilities)

    def test_all_identity(self):
        import omni.capabilities
        import nvidia_usd_validation.capabilities
        self.assertIs(omni.capabilities.__all__, nvidia_usd_validation.capabilities.__all__)

    def test_from_import(self):
        from omni.capabilities import Capabilities  # noqa: F401
