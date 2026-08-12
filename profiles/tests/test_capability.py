# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_profiles_nvidia.api import Capability


class TestCapability(unittest.TestCase):

    def test_dto_fields(self):
        capability = Capability(
            id="semantic_labels", version="1.0.0", path="capabilities/semantic_labels", requirements=[]
        )

        self.assertEqual(capability.id, "semantic_labels")
        self.assertEqual(capability.version, "1.0.0")
        self.assertEqual(capability.path, "capabilities/semantic_labels")
        self.assertEqual(capability.requirements, [])
