# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import asyncio
import unittest

from common import get_url
from pxr import Usd

from usd_validation_nvidia import (
    MAXIMUM_BATCH_SIZE,
    MAXIMUM_COUNT_SIZE,
    AsyncBatchRunner,
    AsyncCounter,
    DelegateContextManager,
    PeriodicCallback,
)


class TestPeriodicCallback(unittest.IsolatedAsyncioTestCase):
    async def test_periodic_callback(self):
        # Track number of callback invocations
        counter = 0

        def callback():
            nonlocal counter
            counter += 1

        async with PeriodicCallback(callback, interval_seconds=0.1):
            await asyncio.sleep(0.35)

        # Should be called ~4-5 times during execution plus once at exit
        self.assertGreaterEqual(counter, 4)

    async def test_periodic_callback_cancellation(self):
        counter = 0

        def callback():
            nonlocal counter
            counter += 1

        # Exit context immediately
        async with PeriodicCallback(callback, interval_seconds=1.0):
            pass

        # Should only be called once at start and once at exit
        self.assertEqual(counter, 2)


class TestAsyncCounter(unittest.IsolatedAsyncioTestCase):
    async def test_async_counter(self):
        async with AsyncCounter() as counter:
            # Count individual items
            await counter.count(1)
            await counter.count(2)
            await counter.count(3)

            self.assertEqual(counter.counter, 6)

    async def test_async_counter_batch_yield(self):
        async with AsyncCounter() as counter:
            # Count enough items to trigger batch yield
            for i in range(MAXIMUM_COUNT_SIZE + 10):
                await counter.count(i)

            self.assertGreater(counter.counter, MAXIMUM_COUNT_SIZE + 10)

    async def test_async_counter_empty(self):
        async with AsyncCounter() as counter:
            # Don't count anything
            self.assertEqual(counter.counter, 0)


class TestAsyncRunner(unittest.IsolatedAsyncioTestCase):
    class TestRunner(AsyncBatchRunner):
        def run(self, events) -> None: ...

    async def test_async_runner(self):
        async with self.TestRunner() as runner:
            # Add individual items
            await runner.append(1)
            await runner.append(2)
            await runner.append(3)

            self.assertEqual(len(runner.events), 3)
            self.assertEqual(runner.counter, 3)

    async def test_async_runner_batch_flush(self):
        async with self.TestRunner() as runner:
            # Add enough items to trigger batch flush
            for i in range(MAXIMUM_BATCH_SIZE + 10):
                await runner.append(i)

            # Events should be empty after hitting batch size since flush() was called
            self.assertEqual(len(runner.events), 10)  # Only the remainder after MAXIMUM_BATCH_SIZE
            self.assertEqual(runner.counter, MAXIMUM_BATCH_SIZE + 10)

        # Verify earlier events were flushed
        self.assertEqual(len(runner.events), 0)

    async def test_async_runner_empty(self):
        async with self.TestRunner() as runner:
            # Don't add anything
            self.assertEqual(len(runner.events), 0)
            self.assertEqual(runner.counter, 0)


class TestDelegateContextManager(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_context_manager(self):
        path = get_url("helloworld.usda")
        with DelegateContextManager() as ctx:
            # Create a stage with the delegate
            Usd.Stage.Open(path)
            stage_open_diagnostics = ctx.delegate.TakeUncoalescedDiagnostics()
            self.assertIsNotNone(stage_open_diagnostics)
