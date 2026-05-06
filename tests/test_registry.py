# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
import unittest.mock
from dataclasses import dataclass

from usd_validation_nvidia import IdVersion, Registry, SemVer, VersionedRegistry


@dataclass
class Item:
    id: str
    version: str


class ItemRegistry(VersionedRegistry[Item]):
    def create_key(self, value: Item) -> IdVersion:
        return IdVersion(value.id, SemVer(value.version))


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry: Registry[str, str] = Registry()

    def test_add_ok(self):
        self.registry.add("key", "value")
        self.assertEqual(self.registry.get("key"), "value")

    def test_get_ok(self):
        self.registry.add("key", "value")
        self.assertEqual(self.registry.get("key"), "value")

    def test_get_missing_ok(self):
        self.assertIsNone(self.registry.get("missing"))
        self.assertEqual(self.registry.get("missing", "default"), "default")

    def test_getitem_ok(self):
        self.registry.add("key", "value")
        self.assertEqual(self.registry["key"], "value")

    def test_getitem_missing_nok(self):
        with self.assertRaises(KeyError):
            _ = self.registry["missing"]

    def test_delitem_ok(self):
        self.registry.add("key", "value")
        del self.registry["key"]
        self.assertIsNone(self.registry.get("key"))

    def test_iter_ok(self):
        self.registry.add("a", "1")
        self.registry.add("b", "2")
        self.assertCountEqual(list(self.registry), ["1", "2"])

    def test_len_ok(self):
        self.assertEqual(len(self.registry), 0)
        self.registry.add("a", "1")
        self.assertEqual(len(self.registry), 1)

    def test_keys_values_items_ok(self):
        self.registry.add("a", "1")
        self.registry.add("b", "2")
        self.assertCountEqual(self.registry.keys(), ["a", "b"])
        self.assertCountEqual(self.registry.values(), ["1", "2"])
        self.assertCountEqual(self.registry.items(), [("a", "1"), ("b", "2")])

    def test_clear_ok(self):
        self.registry.add("a", "1")
        self.registry.clear()
        self.assertEqual(len(self.registry), 0)

    def test_callback_on_add_ok(self):
        callback = unittest.mock.Mock()
        _subscription = self.registry.add_callback(callback)
        self.registry.add("a", "1")
        callback.assert_called_once()

    def test_callback_on_delete_ok(self):
        callback = unittest.mock.Mock()
        self.registry.add("a", "1")
        _subscription = self.registry.add_callback(callback)
        del self.registry["a"]
        callback.assert_called_once()

    def test_callback_on_clear_ok(self):
        callback = unittest.mock.Mock()
        _subscription = self.registry.add_callback(callback)
        self.registry.clear()
        callback.assert_called_once()


class VersionedRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = ItemRegistry()
        self.item_v1 = Item("widget", "1.0.0")
        self.item_v1_2 = Item("widget", "1.2.0")
        self.item_v2 = Item("widget", "2.0.0")

    def test_add_ok(self):
        self.registry.add(self.item_v1)
        self.assertIn(self.item_v1, self.registry)

    def test_add_duplicate_nok(self):
        self.registry.add(self.item_v1)
        with self.assertRaises(ValueError):
            self.registry.add(self.item_v1)

    def test_remove_ok(self):
        self.registry.add(self.item_v1)
        self.registry.remove(self.item_v1)
        self.assertNotIn(self.item_v1, self.registry)

    def test_remove_missing_nok(self):
        with self.assertRaises(ValueError):
            self.registry.remove(self.item_v1)

    # --- find ---

    def test_find_latest_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.find("widget"), self.item_v2)
        self.assertEqual(self.registry.find("widget", SemVer.LATEST), self.item_v2)

    def test_find_exact_version_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.find("widget", "1.0.0"), self.item_v1)
        self.assertEqual(self.registry.find("widget", "2.0.0"), self.item_v2)

    def test_find_nonregistered_version_nok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertIsNone(self.registry.find("widget", "1.5.0"))

    def test_find_unknown_id_nok(self):
        self.assertIsNone(self.registry.find("unknown"))

    # --- resolve ---

    def test_resolve_latest_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.resolve("widget"), self.item_v2)
        self.assertEqual(self.registry.resolve("widget", SemVer.LATEST), self.item_v2)

    def test_resolve_exact_version_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.resolve("widget", "1.0.0"), self.item_v1)
        self.assertEqual(self.registry.resolve("widget", "2.0.0"), self.item_v2)

    def test_resolve_compatible_version_ok(self):
        # Requesting 1.1.0 should return 1.2.0 (same major, higher minor)
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v1_2)
        self.assertEqual(self.registry.resolve("widget", "1.1.0"), self.item_v1_2)

    def test_resolve_incompatible_major_nok(self):
        # Only 1.x registered, requesting 2.0.0 minimum — no compatible version
        self.registry.add(self.item_v1)
        self.assertIsNone(self.registry.resolve("widget", "2.0.0"))

    def test_resolve_unknown_id_nok(self):
        self.assertIsNone(self.registry.resolve("unknown"))

    # --- latest ---

    def test_latest_keys_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.latest_keys(), [IdVersion("widget", SemVer("2.0.0"))])

    def test_latest_values_ok(self):
        self.registry.add(self.item_v1)
        self.registry.add(self.item_v2)
        self.assertEqual(self.registry.latest_values(), [self.item_v2])

    # --- callbacks ---

    def test_callback_on_add_ok(self):
        callback = unittest.mock.Mock()
        _subscription = self.registry.add_callback(callback)
        self.registry.add(self.item_v1)
        callback.assert_called_once()
