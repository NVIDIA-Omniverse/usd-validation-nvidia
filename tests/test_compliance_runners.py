# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock

from pxr import Usd

from usd_validation_nvidia import (
    BaseRuleChecker,
    ComplianceCheckerEvent,
    ComplianceCheckerEventRule,
    ComplianceCheckerEventType,
    FormatDependency,
    LocalUriResolver,
    ValidationStats,
)
from usd_validation_nvidia._compliance_runners import (
    AsyncComplianceCheckerRunner,
    AsyncCoroutineRunner,
    AsyncCoroutineTaskRunner,
    AsyncNoopRunner,
    AsyncThreadRunner,
    AsyncThreadTaskRunner,
    SyncComplianceCheckerRunner,
    SyncCoroutineRunner,
    SyncInlineRunner,
    SyncNoopRunner,
)


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

    def test_apply_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        func = Mock()

        class _SyncStageRule(BaseRuleChecker):
            def CheckStage(self, stage):
                func(stage)

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=stage)
        event_rule = ComplianceCheckerEventRule(event=event, rule=_SyncStageRule())

        # When
        event_rule.apply(ValidationStats())

        # Then
        func.assert_called_once_with(stage)

    async def test_apply_async_ok(self):
        # Given
        stage = Mock(spec=Usd.Stage)
        func = AsyncMock()

        class _AsyncStageRule(BaseRuleChecker):
            async def CheckStage(self, stage):
                await func(stage)

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.STAGE, value=stage)
        event_rule = ComplianceCheckerEventRule(event=event, rule=_AsyncStageRule())

        # When
        await event_rule.applyAsync(ValidationStats())

        # Then
        func.assert_awaited_once_with(stage)


class SyncNoopRunnerTest(TestCase):
    def test_counts_empty_task(self):
        # Given
        runner = SyncNoopRunner(ValidationStats())
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_empty_task.return_value = True

        # When
        runner.submit(event_rule)

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)


class SyncInlineRunnerTest(TestCase):
    def test_runs_sync_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = SyncInlineRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_async_task.return_value = False

        # When
        runner.submit(event_rule)
        runner.flush()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.apply.assert_called_once_with(stats)


class SyncCoroutineRunnerTest(TestCase):
    def test_runs_async_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = SyncCoroutineRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_async_task.return_value = True
        event_rule.applyAsync = AsyncMock()

        # When
        runner.submit(event_rule)
        runner.flush()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.applyAsync.assert_awaited_once_with(stats)


class AsyncNoopRunnerTest(IsolatedAsyncioTestCase):
    async def test_counts_empty_task(self):
        # Given
        runner = AsyncNoopRunner(ValidationStats())
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_empty_task.return_value = True

        # When
        await runner.submit_async(event_rule)

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)


class AsyncCoroutineRunnerTest(IsolatedAsyncioTestCase):
    async def test_runs_light_async_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = AsyncCoroutineRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_heavy_task.return_value = False
        event_rule.is_async_task.return_value = True
        event_rule.applyAsync = AsyncMock()

        # When
        await runner.submit_async(event_rule)
        await runner.flush_async()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.applyAsync.assert_awaited_once_with(stats)


class AsyncThreadRunnerTest(IsolatedAsyncioTestCase):
    async def test_runs_light_sync_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = AsyncThreadRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_heavy_task.return_value = False
        event_rule.is_async_task.return_value = False

        # When
        await runner.submit_async(event_rule)
        await runner.flush_async()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.apply.assert_called_once_with(stats)


class AsyncCoroutineTaskRunnerTest(IsolatedAsyncioTestCase):
    async def test_runs_heavy_async_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = AsyncCoroutineTaskRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_heavy_task.return_value = True
        event_rule.is_async_task.return_value = True
        event_rule.applyAsync = AsyncMock()

        # When
        await runner.submit_async(event_rule)
        await runner.flush_async()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.applyAsync.assert_awaited_once_with(stats)


class AsyncThreadTaskRunnerTest(IsolatedAsyncioTestCase):
    async def test_runs_heavy_sync_event_on_flush(self):
        # Given
        stats = ValidationStats()
        runner = AsyncThreadTaskRunner(stats)
        event_rule = Mock(spec=ComplianceCheckerEventRule)
        event_rule.is_heavy_task.return_value = True
        event_rule.is_async_task.return_value = False

        # When
        await runner.submit_async(event_rule)
        await runner.flush_async()

        # Then
        self.assertTrue(runner.accepts(event_rule))
        self.assertEqual(runner.counter, 1)
        event_rule.apply.assert_called_once_with(stats)


class SyncComplianceCheckerRunnerTest(TestCase):
    def test_append_dispatches_event(self):
        # Given
        prim = Mock(spec=Usd.Prim)
        func = Mock()

        class _SyncPrimRule(BaseRuleChecker):
            def CheckPrim(self, prim):
                func(prim)

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.PRIM, value=prim)

        # When
        with SyncComplianceCheckerRunner(rules=[_SyncPrimRule()], stats=ValidationStats()) as runner:
            runner.append(event)

        # Then
        func.assert_called_once_with(prim)


class AsyncComplianceCheckerRunnerTest(IsolatedAsyncioTestCase):
    async def test_append_dispatches_event(self):
        # Given
        prim = Mock(spec=Usd.Prim)
        func = AsyncMock()

        class _AsyncPrimRule(BaseRuleChecker):
            async def CheckPrim(self, prim):
                await func(prim)

        event = ComplianceCheckerEvent(type=ComplianceCheckerEventType.PRIM, value=prim)

        # When
        async with AsyncComplianceCheckerRunner(rules=[_AsyncPrimRule()], stats=ValidationStats()) as runner:
            await runner.append(event)

        # Then
        self.assertEqual(runner.counter, 1)
        func.assert_awaited_once_with(prim)
