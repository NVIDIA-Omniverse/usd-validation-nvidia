# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from pxr import Usd

from usd_validation_nvidia import BaseRuleChecker, FormatDependency, LocalUriResolver
from usd_validation_nvidia._compliance_runners import (
    AsyncComplianceCheckerRunner,
    ComplianceCheckerEvent,
    ComplianceCheckerEventRule,
    ComplianceCheckerEventType,
)
from usd_validation_nvidia._stats import ValidationStats


class ComplianceCheckerEventTypeTest(IsolatedAsyncioTestCase):
    def test_apply_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        rule = Mock(spec=BaseRuleChecker)

        # When
        ComplianceCheckerEventType.STAGE.apply(rule, (stage,))

        # Then
        rule.CheckStage.assert_called_once_with(stage)

    def test_apply_nok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        rule = Mock(spec=BaseRuleChecker)
        rule.CheckStage.side_effect = ValueError("Test error")

        # When
        ComplianceCheckerEventType.STAGE.apply(rule, (stage,))

        # Then
        rule._AddError.assert_called_once()

    async def test_apply_async_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        rule = Mock(spec=BaseRuleChecker)
        rule.CheckStage = AsyncMock()

        # When
        await ComplianceCheckerEventType.STAGE.applyAsync(rule, (stage,))

        # Then
        rule.CheckStage.assert_awaited_once_with(stage)

    async def test_apply_async_nok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        rule = Mock(spec=BaseRuleChecker)
        rule.CheckStage = AsyncMock(side_effect=ValueError("Test error"))

        # When
        await ComplianceCheckerEventType.STAGE.applyAsync(rule, (stage,))

        # Then
        rule.CheckStage.assert_awaited_once_with(stage)
        rule._AddError.assert_called_once()


class ComplianceCheckerEventRuleTest(IsolatedAsyncioTestCase):

    def test_is_empty_task_ok(self):
        # Given
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=BaseRuleChecker())

        # When / Then
        self.assertTrue(event_rule.is_empty_task())

    def test_is_empty_task_nok(self):
        # Given
        class _RuleOnlyStage(BaseRuleChecker):
            def CheckStage(self, stage): ...

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=_RuleOnlyStage())

        # When / Then
        self.assertFalse(event_rule.is_empty_task())

    def test_is_heavy_task_ok(self):
        # Given
        class _RuleOnlyStage(BaseRuleChecker):
            def CheckStage(self, stage): ...

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=_RuleOnlyStage())

        # When / Then
        self.assertTrue(event_rule.is_heavy_task())

    def test_is_heavy_task_nok(self):
        # Given
        class _RuleOnlyStage(BaseRuleChecker):
            def CheckPrim(self, prim): ...

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.PRIM, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=_RuleOnlyStage())

        # When / Then
        self.assertFalse(event_rule.is_heavy_task())

    def test_is_async_task_ok(self):
        # Given
        class _SyncRule(BaseRuleChecker):
            def CheckStage(self, stage): ...

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=_SyncRule())

        # When / Then
        self.assertFalse(event_rule.is_async_task())

    def test_is_async_task_nok(self):
        # Given
        class _AsyncRule(BaseRuleChecker):
            async def CheckStage(self, stage): ...

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())
        event_rule = ComplianceCheckerEventRule(event=event, rule=_AsyncRule())

        # When / Then
        self.assertTrue(event_rule.is_async_task())

    def test_is_heavy_task_format_dependency_ok(self):
        # Given
        class _RuleOnlyFormatDependency(BaseRuleChecker):
            def CheckFormatDependency(self, _): ...

        event = ComplianceCheckerEvent(
            ComplianceCheckerEventType.FORMAT_DEPENDENCY,
            FormatDependency(path="/dep.json", uri_resolver=LocalUriResolver(), root_asset_path="/dep.json"),
        )
        event_rule = ComplianceCheckerEventRule(event=event, rule=_RuleOnlyFormatDependency())

        # When / Then
        self.assertTrue(event_rule.is_heavy_task())


class AsyncComplianceCheckerRunnerTest(IsolatedAsyncioTestCase):
    async def test_append_empty_ok(self):
        # Given
        rule = BaseRuleChecker()
        stats = ValidationStats()
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=Mock())

        # When
        async with AsyncComplianceCheckerRunner(rules=[rule], stats=stats) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)

    async def test_append_stage_sync_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        func = Mock()

        class _HeavySyncRule(BaseRuleChecker):
            def CheckStage(self, stage):
                func(stage)

        rule = _HeavySyncRule()
        stats = ValidationStats()
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=stage)

        # When
        async with AsyncComplianceCheckerRunner(rules=[rule], stats=stats) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)
        func.assert_called_once_with(stage)

    async def test_append_prim_sync_ok(self):
        # Given
        prim = Mock(spec=Usd.Prim)
        func = Mock()

        class _LightSyncRule(BaseRuleChecker):
            def CheckPrim(self, prim):
                func(prim)

        rule = _LightSyncRule()
        stats = ValidationStats()
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.PRIM, value=prim)

        # When
        async with AsyncComplianceCheckerRunner(rules=[rule], stats=stats) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)
        func.assert_called_once_with(prim)

    async def test_append_stage_async_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        func = AsyncMock()

        class _HeavyAsyncRule(BaseRuleChecker):
            async def CheckStage(self, stage):
                await func(stage)

        rule = _HeavyAsyncRule()
        stats = ValidationStats()
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=stage)

        # When
        async with AsyncComplianceCheckerRunner(rules=[rule], stats=stats) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)
        func.assert_awaited_once_with(stage)

    async def test_append_prim_async_ok(self):
        # Given
        prim = Mock(spec=Usd.Prim)
        func = AsyncMock()

        class _LightAsyncRule(BaseRuleChecker):
            async def CheckPrim(self, prim):
                await func(prim)

        rule = _LightAsyncRule()
        stats = ValidationStats()
        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.PRIM, value=prim)

        # When
        async with AsyncComplianceCheckerRunner(rules=[rule], stats=stats) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)
        func.assert_awaited_once_with(prim)
