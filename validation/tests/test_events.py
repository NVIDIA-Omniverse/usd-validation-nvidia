# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_validation_nvidia import create_event_stream


class TestEvents(unittest.TestCase):

    def test_subscribe_ok(self):
        # Given
        callback = unittest.mock.Mock()

        # When
        event_stream = create_event_stream()
        _listener = event_stream.create_event_listener(callback)
        event_stream.notify()

        # Then
        callback.assert_called_once()
        self.assertEqual(len(event_stream), 1)

    def test_unsubscribe_automatically_ok(self):
        # Given
        callback = unittest.mock.Mock()

        def scenario(event_stream):
            _listener = event_stream.create_event_listener(callback)
            event_stream.notify()

        # When
        event_stream = create_event_stream()
        scenario(event_stream)
        event_stream.notify()

        # Then
        callback.assert_called_once()
        self.assertEqual(len(event_stream), 0)

    def test_unsubscribe_manually_ok(self):
        # Given
        callback = unittest.mock.Mock()

        # When
        event_stream = create_event_stream()
        listener = event_stream.create_event_listener(callback)
        event_stream.notify()
        listener.unsubscribe()
        event_stream.notify()

        # Then
        callback.assert_called_once()
        self.assertEqual(len(event_stream), 0)

    def test_batching_ok(self):
        # Given
        callback = unittest.mock.Mock()

        # When
        event_stream = create_event_stream()
        _listener = event_stream.create_event_listener(callback)
        with event_stream:
            event_stream.notify()
            event_stream.notify()

        # Then
        callback.assert_called_once()

    def test_batching_empty_ok(self):
        # Given
        callback = unittest.mock.Mock()

        # When
        event_stream = create_event_stream()
        _listener = event_stream.create_event_listener(callback)
        with event_stream:
            ...

        # Then
        callback.assert_not_called()

    def test_batching_nested_ok(self):
        # Given
        callback = unittest.mock.Mock()

        # When
        event_stream = create_event_stream()
        _listener = event_stream.create_event_listener(callback)
        with event_stream:
            with event_stream:
                event_stream.notify()
                event_stream.notify()
            callback.assert_not_called()

        # Then
        callback.assert_called_once()
