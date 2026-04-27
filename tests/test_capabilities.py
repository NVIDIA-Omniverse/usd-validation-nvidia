# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest.mock import Mock

from nvidia_usd_validation import (
    Capability,
    CapabilityRegistry,
    add_registry_capability_callback,
    register_capabilities,
    register_capability,
    unregister_capabilities,
    unregister_capability,
)


class CapabilitiesRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = CapabilityRegistry()
        self.mock_capability = Mock(spec=Capability)
        self.mock_capability.id = "test_capability"
        self.mock_capability.version = "1.0.0"
        self.mock_capability.name = "test_capability"
        self.mock_capability.requirements = []

    def tearDown(self):
        try:
            unregister_capability(self.mock_capability)
        except ValueError:
            pass

    def test_add_capability(self):
        self.registry.add_capability(self.mock_capability)

        self.assertIn(self.mock_capability, self.registry.capabilities)
        self.assertEqual(self.registry.find_capability(self.mock_capability.id), self.mock_capability)

    def test_find_capability(self):
        self.registry.add_capability(self.mock_capability)

        self.assertEqual(self.registry.find_capability("test_capability"), self.mock_capability)

    def test_find_nonexistent_capability(self):
        self.assertIsNone(self.registry.find_capability("nonexistent"))

    def test_capabilities_property(self):
        self.registry.add_capability(self.mock_capability)

        self.assertIn(self.mock_capability, self.registry.capabilities)

    def test_latest_capabilities_property(self):
        self.registry.add_capability(self.mock_capability)

        self.assertIn(self.mock_capability, self.registry.latest_capabilities)

    def test_singleton(self):
        registry1 = CapabilityRegistry()
        registry2 = CapabilityRegistry()

        registry1.add_capability(self.mock_capability)

        self.assertIsNotNone(registry1.find_capability("test_capability"))
        self.assertIsNotNone(registry2.find_capability("test_capability"))

    def test_register_capability_ok(self):
        register_capability(self.mock_capability)
        try:
            self.assertIn(self.mock_capability, self.registry)
        finally:
            unregister_capability(self.mock_capability)

    def test_unregister_capability_ok(self):
        register_capability(self.mock_capability)
        unregister_capability(self.mock_capability)
        self.assertNotIn(self.mock_capability, self.registry)

    def test_register_capabilities(self):
        register_capabilities([self.mock_capability])
        try:
            self.assertIn(self.mock_capability, self.registry.capabilities)
        finally:
            unregister_capabilities([self.mock_capability])

    def test_unregister_capabilities(self):
        register_capabilities([self.mock_capability])
        unregister_capabilities([self.mock_capability])
        self.assertNotIn(self.mock_capability, self.registry.capabilities)

    def test_add_callback_ok(self):
        callback = unittest.mock.Mock()
        _subscription = add_registry_capability_callback(callback)
        register_capability(self.mock_capability)
        try:
            callback.assert_called_once()
        finally:
            unregister_capability(self.mock_capability)
