# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia import (
    BaseRuleChecker,
    CapabilityRegistry,
    add_registry_capability_callback,
    register_capabilities,
    register_capability,
    register_requirements,
    unregister_capabilities,
    unregister_capability,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import Capability as CapabilityDTO
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO


class CapabilitiesRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = CapabilityRegistry()
        self.capability = CapabilityDTO(
            id="test_capability",
            version="1.0.0",
            path="/path/test_capability",
        )

    def tearDown(self):
        try:
            unregister_capability(self.capability)
        except ValueError:
            pass

    def test_add_capability(self):
        self.registry.add(self.capability)

        self.assertIn(self.capability, self.registry.capabilities)
        self.assertEqual(self.registry.find(self.capability.id), self.capability)

    def test_find_capability(self):
        self.registry.add(self.capability)

        self.assertEqual(self.registry.find("test_capability"), self.capability)

    def test_find_nonexistent_capability(self):
        self.assertIsNone(self.registry.find("nonexistent"))

    def test_capabilities_property(self):
        self.registry.add(self.capability)

        self.assertIn(self.capability, self.registry.capabilities)

    def test_latest_capabilities_property(self):
        self.registry.add(self.capability)

        self.assertIn(self.capability, self.registry.latest_capabilities)

    def test_singleton(self):
        registry1 = CapabilityRegistry()
        registry2 = CapabilityRegistry()

        registry1.add(self.capability)

        self.assertIsNotNone(registry1.find("test_capability"))
        self.assertIsNotNone(registry2.find("test_capability"))

    def test_register_capability_ok(self):
        register_capability(self.capability)
        try:
            self.assertIn(self.capability, self.registry)
        finally:
            unregister_capability(self.capability)

    def test_unregister_capability_ok(self):
        register_capability(self.capability)
        unregister_capability(self.capability)
        self.assertNotIn(self.capability, self.registry)

    def test_unregister_capability_requirement_ok(self):
        requirement = RequirementDTO(code="CAPABILITY.REMOVE.REQ", version="1.0.0")
        capability = CapabilityDTO(
            id="implemented_requirement_capability",
            version="1.0.0",
            path="/path/original",
            requirements=[requirement],
        )

        class CapabilityRule(BaseRuleChecker):
            pass

        register_requirements(requirement)(CapabilityRule)
        register_capability(capability)

        try:
            unregister_capability(capability)

            self.assertNotIn(capability, self.registry)
        finally:
            unregister_requirements(CapabilityRule)

    def test_delitem_capability_ok(self):
        register_capability(self.capability)
        key = self.registry.create_key(self.capability)

        del self.registry[key]

        self.assertNotIn(self.capability, self.registry)
        self.assertIsNone(self.registry.find("test_capability"))

    def test_register_capabilities(self):
        self.assertTrue(register_capabilities([self.capability]))
        try:
            self.assertIn(self.capability, self.registry.capabilities)
        finally:
            unregister_capabilities([self.capability])

    def test_register_capabilities_duplicate_returns_false(self):
        register_capability(self.capability)
        try:
            self.assertFalse(register_capabilities([self.capability]))
        finally:
            unregister_capability(self.capability)

    def test_unregister_capabilities(self):
        register_capabilities([self.capability])
        self.assertTrue(unregister_capabilities([self.capability]))
        self.assertNotIn(self.capability, self.registry.capabilities)

    def test_add_callback_ok(self):
        callback = unittest.mock.Mock()
        _subscription = add_registry_capability_callback(callback)
        register_capability(self.capability)
        try:
            callback.assert_called_once()
        finally:
            unregister_capability(self.capability)
