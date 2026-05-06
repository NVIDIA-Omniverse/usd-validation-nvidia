# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for the AssetFormat protocol and AssetFormatRegistry."""

import json
import os
import unittest
from unittest.mock import MagicMock

from pxr import Ar, Usd

from usd_validation_nvidia import (
    AssetFormat,
    AssetFormatRegistry,
    LocalUriResolver,
    UriResolver,
    add_registry_asset_format_callback,
    register_format,
    unregister_format,
)

_SIMREADY_FILENAME = "com.nvidia.simready.packaging.json"
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "asset_format")


class SimReadyAssetFormat:
    """Local test fixture implementing AssetFormat for SimReady packaging manifests."""

    def supports(self, asset_path: str) -> bool:
        return asset_path.endswith(_SIMREADY_FILENAME)

    def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]:
        content = self._read(asset_path)
        if content is None:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []

        manifest_dir = uri_resolver.parent_uri(asset_path)

        catalog = data.get("catalog") or {}
        items = catalog.get("items") or []
        if items:
            children = [
                uri_resolver.join_uri(manifest_dir, item["source_path"]) for item in items if "source_path" in item
            ]
            return [asset_path, *children]

        deps = data.get("dependencies") or []
        children = []
        for dep in deps:
            rel = dep.get("relative_path", "")
            if rel:
                children.extend(self.get_dependencies(uri_resolver.join_uri(manifest_dir, rel), uri_resolver))
        return [asset_path, *children] if children else []

    @staticmethod
    def _read(asset_path: str) -> str | None:
        resolved: Ar.ResolvedPath = Ar.GetResolver().Resolve(asset_path)
        if not resolved:
            return None
        ar_asset = Ar.GetResolver().OpenAsset(resolved)
        if not ar_asset:
            return None
        return bytes(ar_asset.GetBuffer()).decode("utf-8")


class TestAssetFormatProtocol(unittest.TestCase):

    def test_structural_subtype(self):
        self.assertIsInstance(SimReadyAssetFormat(), AssetFormat)

    def test_missing_supports_not_protocol(self):
        class NoSupports:
            def get_dependencies(self, _: str) -> list[str]:
                return []

        self.assertNotIsInstance(NoSupports(), AssetFormat)

    def test_missing_get_dependencies_not_protocol(self):
        class NoGetDeps:
            def supports(self, _: str) -> bool:
                return False

        self.assertNotIsInstance(NoGetDeps(), AssetFormat)


class TestAssetFormatRegistry(unittest.TestCase):

    def test_register_rejects_non_protocol(self):
        class NotAFormat:
            pass

        with self.assertRaises(TypeError):
            register_format()(NotAFormat)

    def test_register_and_find(self):
        register_format()(SimReadyAssetFormat)
        try:
            self.assertIsNotNone(AssetFormatRegistry().find(f"/some/path/{_SIMREADY_FILENAME}"))
        finally:
            unregister_format(SimReadyAssetFormat)

    def test_find_returns_none_when_no_match(self):
        register_format()(SimReadyAssetFormat)
        try:
            self.assertIsNone(AssetFormatRegistry().find("/some/file.usd"))
        finally:
            unregister_format(SimReadyAssetFormat)

    def test_unregister(self):
        register_format()(SimReadyAssetFormat)
        unregister_format(SimReadyAssetFormat)
        self.assertIsNone(AssetFormatRegistry().find(f"/some/{_SIMREADY_FILENAME}"))

    def test_first_match_wins(self):
        class AnotherFormat(SimReadyAssetFormat):
            pass

        register_format()(SimReadyAssetFormat)
        register_format()(AnotherFormat)
        try:
            found = AssetFormatRegistry().find(f"/path/{_SIMREADY_FILENAME}")
            self.assertIsInstance(found, SimReadyAssetFormat)
            self.assertNotIsInstance(found, AnotherFormat)
        finally:
            unregister_format(SimReadyAssetFormat)
            unregister_format(AnotherFormat)

    def test_callback_on_register(self):
        callback = MagicMock()
        listener = add_registry_asset_format_callback(callback)
        try:
            register_format()(SimReadyAssetFormat)
            callback.assert_called_once()
        finally:
            listener.unsubscribe()
            unregister_format(SimReadyAssetFormat)

    def test_callback_on_unregister(self):
        register_format()(SimReadyAssetFormat)
        callback = MagicMock()
        listener = add_registry_asset_format_callback(callback)
        try:
            unregister_format(SimReadyAssetFormat)
            callback.assert_called_once()
        finally:
            listener.unsubscribe()


class TestSimReadyAssetFormatSupports(unittest.TestCase):

    def setUp(self):
        self.fmt = SimReadyAssetFormat()

    def test_supports_simready_filename(self):
        self.assertTrue(self.fmt.supports(f"/any/path/{_SIMREADY_FILENAME}"))

    def test_does_not_support_usd(self):
        self.assertFalse(self.fmt.supports("/path/asset.usd"))

    def test_does_not_support_partial_name(self):
        self.assertFalse(self.fmt.supports("/path/packaging.json"))


@unittest.skipUnless(Usd.GetVersion() >= (0, 25, 5), "Ar.OpenAsset requires USD 25.05+")
class TestSimReadyAssetFormatGetDependencies(unittest.TestCase):

    def setUp(self):
        self.fmt = SimReadyAssetFormat()
        self.resolver = LocalUriResolver()

    def test_leaf_returns_catalog_source_paths(self):
        path = os.path.join(_DATA_DIR, "simready_leaf.json")
        deps = self.fmt.get_dependencies(path, self.resolver)
        self.assertEqual(
            deps,
            [
                os.path.join(_DATA_DIR, "simready_leaf.json"),
                os.path.join(_DATA_DIR, "apple.usd"),
                os.path.join(_DATA_DIR, "diffuse.png"),
            ],
        )

    def test_bundle_returns_child_manifest_paths(self):
        path = os.path.join(_DATA_DIR, "simready_bundle.json")
        deps = self.fmt.get_dependencies(path, self.resolver)
        self.assertEqual(
            deps,
            [
                os.path.join(_DATA_DIR, "simready_bundle.json"),
                os.path.join(_DATA_DIR, "simready_leaf.json"),
                os.path.join(_DATA_DIR, "apple.usd"),
                os.path.join(_DATA_DIR, "diffuse.png"),
            ],
        )
