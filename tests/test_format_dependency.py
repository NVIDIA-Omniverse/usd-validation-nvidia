# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for CheckFormatDependency, FORMAT_DEPENDENCY event, and engine.validate() for non-USD assets."""

import json
import os
import pathlib
import unittest

from nvidia_usd_validation import (
    BaseRuleChecker,
    FormatDependency,
    UriResolver,
    ValidationEngine,
    register_format,
    unregister_format,
)
from nvidia_usd_validation.tests import IsAFailure, ValidationTestCaseMixin
from pxr import Ar, Usd

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "asset_format")


class _StubFormat:
    """A format whose supports() matches *.stubfmt and get_dependencies returns a fixed list."""

    _DEPS = ["/a/dep1.stubfmt", "/a/dep2.stubfmt", "/a/dep3.stubfmt"]

    def supports(self, asset_path: str) -> bool:
        return asset_path.endswith(".stubfmt")

    def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]:
        return [asset_path, *self._DEPS]


class _JsonSimReadyFormat:
    """AssetFormat that reads SimReady-style JSON manifests (matches any *.json for test convenience)."""

    def supports(self, asset_path: str) -> bool:
        return asset_path.endswith(".json")

    def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]:
        resolved = Ar.GetResolver().Resolve(asset_path)
        if not resolved:
            return []
        ar_asset = Ar.GetResolver().OpenAsset(resolved)
        if not ar_asset:
            return []
        try:
            data = json.loads(bytes(ar_asset.GetBuffer()).decode("utf-8"))
        except Exception:
            return []

        manifest_dir = uri_resolver.parent_uri(asset_path)
        catalog = (data.get("catalog") or {}).get("items") or []
        if catalog:
            return [asset_path] + [
                uri_resolver.join_uri(manifest_dir, item["source_path"]) for item in catalog if "source_path" in item
            ]

        deps = []
        for dep in data.get("dependencies") or []:
            rel = dep.get("relative_path", "")
            if rel:
                deps.extend(self.get_dependencies(uri_resolver.join_uri(manifest_dir, rel), uri_resolver))
        return [asset_path, *deps] if deps else []


class TestEngineValidateRawAsset(unittest.TestCase, ValidationTestCaseMixin):

    _STUB_ASSET = os.path.join(_DATA_DIR, "test_asset.stubfmt")

    def setUp(self):
        register_format()(_StubFormat)

    def tearDown(self):
        unregister_format(_StubFormat)

    def test_is_asset_supported_for_registered_format(self):
        self.assertTrue(ValidationEngine.is_asset_supported(self._STUB_ASSET))

    def test_is_asset_supported_false_for_unknown_extension(self):
        self.assertFalse(ValidationEngine.is_asset_supported("/path/unknown.xyz"))

    def test_validate_calls_check_format_dependency(self):
        received: list[str] = []

        class Collector(BaseRuleChecker):
            def CheckFormatDependency(self, dependency: FormatDependency) -> None:
                received.append(dependency.path)

        self.assertSuccess(asset=self._STUB_ASSET, rule=Collector)
        # root + 3 fixed deps from _StubFormat
        self.assertEqual(len(received), 4)

    def test_validate_rule_can_report_failure(self):
        class AlwaysFail(BaseRuleChecker):
            def CheckFormatDependency(self, _: FormatDependency) -> None:
                self._AddFailedCheck("deliberate failure")

        self.assertFailure(asset=self._STUB_ASSET, rule=AlwaysFail)

    def test_validate_rule_can_report_failure_at_dependency(self):
        class AlwaysFail(BaseRuleChecker):
            def CheckFormatDependency(self, dependency: FormatDependency) -> None:
                self._AddFailedCheck("deliberate failure", at=dependency)

        self.assertRule(
            asset=self._STUB_ASSET,
            rule=AlwaysFail,
            asserts=[
                IsAFailure("deliberate failure", at=pathlib.Path(self._STUB_ASSET)),
                IsAFailure("deliberate failure", at=pathlib.Path("/a/dep1.stubfmt")),
                IsAFailure("deliberate failure", at=pathlib.Path("/a/dep2.stubfmt")),
                IsAFailure("deliberate failure", at=pathlib.Path("/a/dep3.stubfmt")),
            ],
        )

    def test_validate_returns_error_for_unregistered_extension(self):
        self.assertFailure(asset=os.path.join(_DATA_DIR, "diffuse.png"), rule=BaseRuleChecker)

    def test_validate_returns_error_for_missing_file(self):
        self.assertFailure(asset="/does/not/exist.stubfmt", rule=BaseRuleChecker)


@unittest.skipUnless(Usd.GetVersion() >= (0, 25, 5), "Ar.OpenAsset requires USD 25.05+")
class TestEngineValidateRawAssetWithRealData(unittest.TestCase, ValidationTestCaseMixin):

    _LEAF = os.path.join(_DATA_DIR, "simready_leaf.json")

    def setUp(self):
        register_format()(_JsonSimReadyFormat)

    def tearDown(self):
        unregister_format(_JsonSimReadyFormat)

    def test_validate_hook_called_for_non_usd_dependencies(self):
        received: list[str] = []

        class Collector(BaseRuleChecker):
            def CheckFormatDependency(self, dependency: FormatDependency) -> None:
                received.append(dependency.path)

        self.assertSuccess(asset=self._LEAF, rule=Collector)
        # simready_leaf.json has 2 catalog items: apple.usd (→ USD workflow) and diffuse.png (→ FORMAT_DEPENDENCY)
        # FORMAT_DEPENDENCY fires for: manifest itself + diffuse.png = 2
        self.assertEqual(len(received), 2)
        self.assertEqual(received[0], self._LEAF)

    def test_validate_usd_dependency_triggers_stage_check(self):
        stage_roots: list[str] = []

        class StageCollector(BaseRuleChecker):
            def CheckStage(self, usdStage) -> None:
                stage_roots.append(usdStage.GetRootLayer().identifier)

        self.assertSuccess(asset=self._LEAF, rule=StageCollector)
        # apple.usd is the only USD catalog item in simready_leaf.json
        self.assertEqual(len(stage_roots), 1)
        self.assertTrue(stage_roots[0].endswith("apple.usd"))
