# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from common import AsyncioValidationTestCase, get_url
from nvidia_usd_validation import LayerId, UnicodeNameChecker
from nvidia_usd_validation.tests import IsAWarning
from pxr import Sdf, Usd


@unittest.skipIf(Usd.GetVersion() < (0, 24, 3), "Skipping test because USD version is less than 24.3")
class UnicodeNameCheckerTest(AsyncioValidationTestCase):
    async def test_prim_name_is_not_nfc_normalized(self):
        asset_url = LayerId(identifier=get_url("Unicode/nonNFCPrim.usda")).identifier
        await self.assertRuleAsync(
            asset=asset_url,
            rule=UnicodeNameChecker,
            asserts=[
                IsAWarning(
                    message="The name (primÅ) of prim spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/root/primÅ')",
                ),
            ],
        )

    async def test_property_is_not_nfc_normalized(self):
        asset_url = LayerId(identifier=get_url("Unicode/nonNFCProperty.usda")).identifier
        await self.assertRuleAsync(
            asset=asset_url,
            rule=UnicodeNameChecker,
            asserts=[
                IsAWarning(
                    message="The name (propertyÅ) of attribute spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/prim.propertyÅ')",
                ),
            ],
        )

    async def test_variant_is_not_nfc_normalized(self):
        asset_url = LayerId(identifier=get_url("Unicode/nonNFCVariants.usda")).identifier
        await self.assertRuleAsync(
            asset=asset_url,
            rule=UnicodeNameChecker,
            asserts=[
                IsAWarning(
                    message="The name (variantÅ) of variant spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', " + "'/prim{variantSetÅ=variantÅ}')",
                ),
                IsAWarning(
                    message="The name (variantSetÅ) of variant set spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', " + "'/prim{variantSetÅ=}')",
                ),
            ],
        )

    async def test_prim_has_ambiguous_children_same(self):
        asset_url = LayerId(identifier=get_url("Unicode/ambiguousChildrenSame.usda")).identifier
        await self.assertRuleAsync(
            asset=asset_url,
            rule=UnicodeNameChecker,
            asserts=[
                IsAWarning(
                    message="Prim 'primÅ' is ambiguous with sibling prim 'primÅ' under the following forms: ['NFC', 'NFD', 'NFKC', 'NFKD'].",
                    at=Sdf.Path("/primÅ"),
                ),
                IsAWarning(
                    message="The name (primÅ) of prim spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/reference/primÅ')",
                ),
                IsAWarning(
                    message="The name (primÅ) of prim spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/primÅ')",
                ),
            ],
        )

    async def test_prim_has_ambiguous_children_different(self):
        asset_url = LayerId(identifier=get_url("Unicode/ambiguousChildrenDifferent.usda")).identifier
        await self.assertRuleAsync(
            asset=asset_url,
            rule=UnicodeNameChecker,
            asserts=[
                IsAWarning(
                    message="Prim 'primẛ̣' is ambiguous with sibling prim 'primẛ̣' under the following forms: ['NFC', 'NFD', 'NFKC', 'NFKD'].",
                    at=Sdf.Path("/primẛ̣"),
                ),
                IsAWarning(
                    message="Prim 'primṩ' is ambiguous with sibling prim 'primẛ̣' under the following forms: ['NFKC', 'NFKD'].",
                    at=Sdf.Path("/primẛ̣"),
                ),
                IsAWarning(
                    message="The name (primẛ̣) of prim spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/primẛ̣')",
                ),
                IsAWarning(
                    message="The name (primṩ) of prim spec is not NFC normalized.",
                    at=f"Sdf.Find('{asset_url}', '/primṩ')",
                ),
            ],
        )
