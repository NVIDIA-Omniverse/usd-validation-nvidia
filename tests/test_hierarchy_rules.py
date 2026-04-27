# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import nvidia_usd_validation.capabilities as cap
from common import AsyncioValidationTestCase


class HierarchyHasRootCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.HI_001)


class RootPrimXformableCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.HI_003)
