# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import nvidia_usd_validation.capabilities as cap
from common import AsyncioValidationTestCase


class UpAxisZCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_006)


class MetersPerUnit1CheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_007)
