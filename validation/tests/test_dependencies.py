# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import importlib.metadata
import unittest
from unittest import mock

from usd_validation_nvidia._dependencies import (
    is_package_installed,
    is_usd_distribution_conflict,
)


class DependenciesTest(unittest.TestCase):

    def setUp(self):
        is_package_installed.cache_clear()
        is_usd_distribution_conflict.cache_clear()

    def tearDown(self):
        is_package_installed.cache_clear()
        is_usd_distribution_conflict.cache_clear()

    def test_is_package_installed_ok(self):
        with mock.patch("importlib.metadata.distribution"):
            self.assertTrue(is_package_installed("example"))

    def test_is_package_installed_not_found_ok(self):
        with mock.patch("importlib.metadata.distribution", side_effect=importlib.metadata.PackageNotFoundError):
            self.assertFalse(is_package_installed("example"))

    def test_is_package_installed_metadata_error_ok(self):
        with mock.patch("importlib.metadata.distribution", side_effect=RuntimeError):
            self.assertFalse(is_package_installed("example"))

    def test_is_usd_distribution_conflict_ok(self):
        with mock.patch("importlib.metadata.distribution"):
            self.assertTrue(is_usd_distribution_conflict())

    def test_is_usd_distribution_conflict_single_provider_ok(self):
        for installed_package in ("usd-core", "usd-exchange"):
            with self.subTest(installed_package=installed_package):
                is_package_installed.cache_clear()
                is_usd_distribution_conflict.cache_clear()

                def distribution(package_name):
                    if package_name == installed_package:
                        return mock.Mock()
                    raise importlib.metadata.PackageNotFoundError

                with mock.patch("importlib.metadata.distribution", side_effect=distribution):
                    self.assertFalse(is_usd_distribution_conflict())
