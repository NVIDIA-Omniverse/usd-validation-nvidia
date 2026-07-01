# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest


class TestOmniAssetValidatorShim(unittest.TestCase):
    def test_class_identity(self):
        from omni.asset_validator import ValidationEngine
        from usd_validation_nvidia import ValidationEngine as NvValidationEngine

        self.assertIs(ValidationEngine, NvValidationEngine)

    def test_all_identity(self):
        import omni.asset_validator
        import usd_validation_nvidia

        self.assertEqual(omni.asset_validator.__all__, usd_validation_nvidia.__all__)

    def test_from_import(self):
        from omni.asset_validator import ValidationEngine  # noqa: F401

    def test_requirement_ref_protocol_exports(self):
        from omni.asset_validator import (
            RequirementRefProtocol as OmniRequirementRefProtocol,
        )
        from usd_validation_nvidia import RequirementRefProtocol
        from usd_validation_nvidia.capabilities import (
            RequirementRefProtocol as CapRequirementRefProtocol,
        )

        self.assertIs(RequirementRefProtocol, CapRequirementRefProtocol)
        self.assertIs(OmniRequirementRefProtocol, RequirementRefProtocol)


class TestOmniAssetValidatorTestsShim(unittest.TestCase):
    def test_class_identity(self):
        from omni.asset_validator.tests import ValidationTestCaseMixin
        from usd_validation_nvidia.tests import (
            ValidationTestCaseMixin as NvValidationTestCaseMixin,
        )

        self.assertIs(ValidationTestCaseMixin, NvValidationTestCaseMixin)

    def test_all_identity(self):
        import omni.asset_validator.tests
        import usd_validation_nvidia.tests

        self.assertEqual(omni.asset_validator.tests.__all__, usd_validation_nvidia.tests.__all__)

    def test_from_import(self):
        from omni.asset_validator.tests import ValidationTestCaseMixin  # noqa: F401


class TestOmniCapabilitiesShim(unittest.TestCase):
    def test_class_identity(self):
        from omni.capabilities import Capabilities
        from usd_validation_nvidia.capabilities import Capabilities as NvCapabilities

        self.assertIs(Capabilities, NvCapabilities)

    def test_all_identity(self):
        import omni.capabilities
        import usd_validation_nvidia.capabilities

        self.assertEqual(omni.capabilities.__all__, usd_validation_nvidia.capabilities.__all__)

    def test_from_import(self):
        from omni.capabilities import Capabilities  # noqa: F401
