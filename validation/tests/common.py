# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import importlib.metadata
import pathlib
from unittest import IsolatedAsyncioTestCase, TestCase

from usd_validation_nvidia.tests import (
    AsyncioValidationTestCaseMixin,
    ValidationTestCaseMixin,
)


def get_url(relative_path: str | pathlib.Path = "") -> str:
    return str(pathlib.Path(__file__).parent.joinpath("data").joinpath(relative_path))


def is_package_installed(package_name: str = "usd-core") -> bool:
    """
    Check if a package is installed.

    Args:
        package_name: The distribution name (e.g., "usd-core", not "pxr")

    Returns:
        bool: True if the package is installed, False otherwise
    """
    try:
        importlib.metadata.distribution(package_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


class ValidationTestCase(TestCase, ValidationTestCaseMixin): ...


class AsyncioValidationTestCase(IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin): ...
