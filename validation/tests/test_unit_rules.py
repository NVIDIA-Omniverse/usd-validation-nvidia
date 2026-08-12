# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from common import AsyncioValidationTestCase

import usd_validation_nvidia.capabilities as cap


class UpAxisZCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_006)


class MetersPerUnit1CheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_007)
