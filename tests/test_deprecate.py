# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia._deprecate import deprecated


class TestDeprecate(unittest.TestCase):
    def test_deprecated_function(self):
        @deprecated("This is deprecated")
        def test_func():
            pass

        with self.assertLogs(level="WARNING") as logs:
            test_func()
        self.assertIn("This is deprecated", logs.output[0])
        self.assertIn("test_deprecated_function", logs.output[1])

    def test_deprecated_class(self):
        @deprecated("This is deprecated")
        class TestClass:
            pass

        with self.assertLogs(level="WARNING") as logs:
            TestClass()
        self.assertIn("This is deprecated", logs.output[0])
        self.assertIn("test_deprecated_class", logs.output[1])

    def test_deprecated_method(self):
        class TestClass:
            @deprecated("This is deprecated")
            def test_method(self):
                pass

        with self.assertLogs(level="WARNING") as logs:
            TestClass().test_method()
        self.assertIn("This is deprecated", logs.output[0])
        self.assertIn("test_deprecated_method", logs.output[1])

    def test_deprecated_class_method(self):
        class TestClass:
            @classmethod
            @deprecated("This is deprecated")
            def test_class_method(cls):
                pass

        with self.assertLogs(level="WARNING") as logs:
            TestClass.test_class_method()
        self.assertIn("This is deprecated", logs.output[0])
        self.assertIn("test_deprecated_class_method", logs.output[1])

    def test_deprecated_property(self):
        class TestClass:
            @property
            @deprecated("This is deprecated")
            def test_property(self):
                pass

        with self.assertLogs(level="WARNING") as logs:
            TestClass().test_property
        self.assertIn("This is deprecated", logs.output[0])
        self.assertIn("test_deprecated_property", logs.output[1])
