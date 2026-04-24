# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest import TestCase

from nvidia_usd_validation import BaseRuleChecker
from nvidia_usd_validation._base_rule_metadata import BaseRuleCheckerMetadata


class BaseRuleCheckerMetadataTest(TestCase):
    def test_base_rule_checker_no_implementations(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.is_stage_implemented())
        self.assertFalse(metadata.is_diagnostics_implemented())
        self.assertFalse(metadata.is_unresolved_implemented())
        self.assertFalse(metadata.is_dependencies_implemented())
        self.assertFalse(metadata.is_layer_implemented())
        self.assertFalse(metadata.is_zip_implemented())
        self.assertFalse(metadata.is_prim_implemented())
        self.assertFalse(metadata.is_asset_implemented())
        self.assertFalse(metadata.is_only_stage_implemented())
        self.assertFalse(metadata.is_only_layer_implemented())
        self.assertFalse(metadata.is_only_zip_implemented())
        self.assertFalse(metadata.has_async_implementations())

    def test_is_stage_implemented_ok(self):
        # Given
        class _RuleWithStage(BaseRuleChecker):
            def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithStage)

        # When / Then
        self.assertTrue(metadata.is_stage_implemented())

    def test_is_diagnostics_implemented_ok(self):
        # Given
        class _RuleWithDiagnostics(BaseRuleChecker):
            def CheckDiagnostics(self, diagnostics): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithDiagnostics)

        # When / Then
        self.assertTrue(metadata.is_diagnostics_implemented())

    def test_is_unresolved_implemented_ok(self):
        # Given
        class _RuleWithUnresolved(BaseRuleChecker):
            def CheckUnresolvedPaths(self, unresolvedPaths): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithUnresolved)

        # When / Then
        self.assertTrue(metadata.is_unresolved_implemented())

    def test_is_dependencies_implemented_ok(self):
        # Given
        class _RuleWithDependencies(BaseRuleChecker):
            def CheckDependencies(self, usdStage, layerDeps, assetDeps): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithDependencies)

        # When / Then
        self.assertTrue(metadata.is_dependencies_implemented())

    def test_is_layer_implemented_ok(self):
        # Given
        class _RuleWithLayer(BaseRuleChecker):
            def CheckLayer(self, layer): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithLayer)

        # When / Then
        self.assertTrue(metadata.is_layer_implemented())

    def test_is_zip_implemented_ok(self):
        # Given
        class _RuleWithZip(BaseRuleChecker):
            def CheckZipFile(self, zipFile, packagePath): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithZip)

        # When / Then
        self.assertTrue(metadata.is_zip_implemented())

    def test_is_prim_implemented_ok(self):
        # Given
        class _RuleWithPrim(BaseRuleChecker):
            def CheckPrim(self, prim): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithPrim)

        # When / Then
        self.assertTrue(metadata.is_prim_implemented())

    def test_is_asset_implemented_nok(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.is_asset_implemented())

    def test_is_asset_implemented_layer_ok(self):
        # Given
        class _RuleWithLayer(BaseRuleChecker):
            def CheckLayer(self, layer): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithLayer)

        # When / Then
        self.assertTrue(metadata.is_asset_implemented())

    def test_is_asset_implemented_zip_ok(self):
        # Given
        class _RuleWithZip(BaseRuleChecker):
            def CheckZipFile(self, zipFile, packagePath): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithZip)

        # When / Then
        self.assertTrue(metadata.is_asset_implemented())

    def test_is_asset_implemented_dependencies_ok(self):
        # Given
        class _RuleWithDependencies(BaseRuleChecker):
            def CheckDependencies(self, usdStage, layerDeps, assetDeps): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithDependencies)

        # When / Then
        self.assertTrue(metadata.is_asset_implemented())

    def test_is_asset_implemented_unresolved_ok(self):
        # Given
        class _RuleWithUnresolved(BaseRuleChecker):
            def CheckUnresolvedPaths(self, unresolvedPaths): ...

        metadata = BaseRuleCheckerMetadata(_RuleWithUnresolved)

        # When / Then
        self.assertTrue(metadata.is_asset_implemented())

    def test_is_only_stage_implemented_nok_empty(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.is_only_stage_implemented())

    def test_is_only_stage_implemented_ok(self):
        # Given
        class _RuleOnlyStage(BaseRuleChecker):
            def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleOnlyStage)

        # When / Then
        self.assertTrue(metadata.is_only_stage_implemented())

    def test_is_only_stage_implemented_nok_multiple(self):
        # Given
        class _RuleStageAndPrim(BaseRuleChecker):
            def CheckStage(self, stage): ...

            def CheckPrim(self, prim): ...

        metadata = BaseRuleCheckerMetadata(_RuleStageAndPrim)

        # When / Then
        self.assertFalse(metadata.is_only_stage_implemented())

    def test_is_only_layer_implemented_nok_empty(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.is_only_layer_implemented())

    def test_is_only_layer_implemented_ok(self):
        # Given
        class _RuleOnlyLayer(BaseRuleChecker):
            def CheckLayer(self, layer): ...

        metadata = BaseRuleCheckerMetadata(_RuleOnlyLayer)

        # When / Then
        self.assertTrue(metadata.is_only_layer_implemented())

    def test_is_only_layer_implemented_nok_multiple(self):
        # Given
        class _RuleLayerAndStage(BaseRuleChecker):
            def CheckLayer(self, layer): ...

            def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleLayerAndStage)

        # When / Then
        self.assertFalse(metadata.is_only_layer_implemented())

    def test_is_only_zip_implemented_nok_empty(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.is_only_zip_implemented())

    def test_is_only_zip_implemented_ok(self):
        # Given
        class _RuleOnlyZip(BaseRuleChecker):
            def CheckZipFile(self, zipFile, packagePath): ...

        metadata = BaseRuleCheckerMetadata(_RuleOnlyZip)

        # When / Then
        self.assertTrue(metadata.is_only_zip_implemented())

    def test_is_only_zip_implemented_nok_multiple(self):
        # Given
        class _RuleZipAndStage(BaseRuleChecker):
            def CheckZipFile(self, zipFile, packagePath): ...

            def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleZipAndStage)

        # When / Then
        self.assertFalse(metadata.is_only_zip_implemented())

    def test_has_async_implementations_nok_empty(self):
        # Given
        metadata = BaseRuleCheckerMetadata(BaseRuleChecker)

        # When / Then
        self.assertFalse(metadata.has_async_implementations())

    def test_has_async_implementations_nok_sync(self):
        # Given
        class _RuleSyncStage(BaseRuleChecker):
            def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleSyncStage)

        # When / Then
        self.assertFalse(metadata.has_async_implementations())

    def test_has_async_implementations_stage_ok(self):
        # Given
        class _RuleAsyncStage(BaseRuleChecker):
            async def CheckStage(self, stage): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncStage)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_layer_ok(self):
        # Given
        class _RuleAsyncLayer(BaseRuleChecker):
            async def CheckLayer(self, layer): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncLayer)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_zip_ok(self):
        # Given
        class _RuleAsyncZip(BaseRuleChecker):
            async def CheckZipFile(self, zipFile, packagePath): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncZip)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_prim_ok(self):
        # Given
        class _RuleAsyncPrim(BaseRuleChecker):
            async def CheckPrim(self, prim): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncPrim)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_diagnostics_ok(self):
        # Given
        class _RuleAsyncDiagnostics(BaseRuleChecker):
            async def CheckDiagnostics(self, diagnostics): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncDiagnostics)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_unresolved_ok(self):
        # Given
        class _RuleAsyncUnresolved(BaseRuleChecker):
            async def CheckUnresolvedPaths(self, unresolvedPaths): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncUnresolved)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_dependencies_ok(self):
        # Given
        class _RuleAsyncDependencies(BaseRuleChecker):
            async def CheckDependencies(self, usdStage, layerDeps, assetDeps): ...

        metadata = BaseRuleCheckerMetadata(_RuleAsyncDependencies)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())

    def test_has_async_implementations_mixed_ok(self):
        # Given
        class _RuleMixedSyncAsync(BaseRuleChecker):
            def CheckStage(self, stage): ...

            async def CheckPrim(self, prim): ...

        metadata = BaseRuleCheckerMetadata(_RuleMixedSyncAsync)

        # When / Then
        self.assertTrue(metadata.has_async_implementations())
