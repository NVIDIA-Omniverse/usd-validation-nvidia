# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from unittest import mock

from nvidia_usd_validation import default_implementation, default_implementation_method


class DefaultImplementationTest(unittest.IsolatedAsyncioTestCase):
    default = mock.Mock()
    numpy = mock.Mock()

    def setUp(self):
        DefaultImplementationTest.default.reset_mock()
        DefaultImplementationTest.numpy.reset_mock()

    @default_implementation_method
    @staticmethod
    def compute_value(value):
        DefaultImplementationTest.default()

    @compute_value.numpy
    @staticmethod
    def _(value):
        DefaultImplementationTest.numpy()

    async def test_default_class_method_dispatch(self):
        with mock.patch.object(self.compute_value, "is_numpy_installed") as is_numpy_installed_mock:
            is_numpy_installed_mock.return_value = False

            self.compute_value(1)
            DefaultImplementationTest.default.assert_called()
            DefaultImplementationTest.numpy.assert_not_called()

    async def test_numpy_class_method_dispatch(self):
        with mock.patch.object(
            DefaultImplementationTest.compute_value, "is_numpy_installed"
        ) as is_numpy_installed_mock:
            is_numpy_installed_mock.return_value = True

            DefaultImplementationTest.compute_value(1)
            DefaultImplementationTest.numpy.assert_called()
            DefaultImplementationTest.default.assert_not_called()

    async def test_default_dispatch(self):
        default = mock.Mock()
        numpy = mock.Mock()
        value = 1

        @default_implementation
        def compute_value(_):
            default()

        @compute_value.numpy
        def _(_):
            numpy()

        with mock.patch.object(compute_value, "is_numpy_installed") as is_numpy_installed_mock:
            is_numpy_installed_mock.return_value = False

            compute_value(value)
            default.assert_called()
            numpy.assert_not_called()

    async def test_numpy_dispatch(self):
        default = mock.Mock()
        numpy = mock.Mock()
        value = 1

        @default_implementation
        def compute_value(_):
            default()

        @compute_value.numpy
        def _(_):
            numpy()

        with mock.patch.object(compute_value, "is_numpy_installed") as is_numpy_installed_mock:
            is_numpy_installed_mock.return_value = True

            compute_value(value)
            numpy.assert_called()
            default.assert_not_called()
