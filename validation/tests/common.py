# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import pathlib
from unittest import IsolatedAsyncioTestCase, TestCase

from usd_validation_nvidia.tests import (
    AsyncioValidationTestCaseMixin,
    ValidationTestCaseMixin,
)


def get_url(relative_path: str | pathlib.Path = "") -> str:
    return str(pathlib.Path(__file__).parent.joinpath("data").joinpath(relative_path))


class ValidationTestCase(TestCase, ValidationTestCaseMixin): ...


class AsyncioValidationTestCase(IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin): ...
