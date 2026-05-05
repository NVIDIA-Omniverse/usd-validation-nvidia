# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
from pathlib import Path

from common import AsyncioValidationTestCase, get_url
from pxr import Usd

import nvidia_usd_validation.capabilities as cap
from nvidia_usd_validation import (
    AnchoredAssetPathsChecker,
    SupportedFileTypesChecker,
    UsdzUdimLimitationChecker,
    normalize_url,
)
from nvidia_usd_validation.tests import IsAFailure, IsAWarning

data_path = Path(os.path.abspath(__file__)).parent / "data"


class AnchoredAssetPathsCheckerTest(AsyncioValidationTestCase):
    maxDiff = None

    async def test_anchored_asset_paths(self):
        # Given
        anchored_layer_path = normalize_url(str(data_path / "anchoredAssetPath.usda"))
        absolute_layer_path = normalize_url(str(data_path / "absoluteAssetPath.usda"))
        relative_layer_path = normalize_url(str(data_path / "relativeAssetPath.usda"))
        material_layer_path = normalize_url(str(data_path / "materialUdim.usda"))
        # When / Then
        expected_failures = [
            IsAFailure(
                "Dependent Sublayer .* cannot be resolved.",
                at=anchored_layer_path,
                requirement=cap.Requirements.AA_001,
            ),  # Path not exists
            IsAFailure(
                'Dependent Sublayer .* should begin with "./" or "../".',
                at=anchored_layer_path,
                requirement=cap.Requirements.AA_001,
            ),  # absolute path
            IsAFailure(
                "Dependent Reference .* cannot be resolved.",
                at=anchored_layer_path,
                requirement=cap.Requirements.AA_001,
            ),  # not a real path texture
            IsAFailure(
                'Dependent Reference .* should begin with "./" or "../".',
                at=anchored_layer_path,
                requirement=cap.Requirements.AA_001,
            ),  # search path
            IsAFailure(
                'Dependent Sublayer .* should begin with "./" or "../".',
                at=absolute_layer_path,
                requirement=cap.Requirements.AA_001,
            ),  # absolute path
            IsAFailure(
                'Dependent Payload .* should begin with "./" or "../".', at=absolute_layer_path
            ),  # absolute payload path
        ]

        # In USD 25.02, UsdUtils.ComputeAllDependencies() starts to
        # report dependency assets from a dependent .usdz layers.
        if Usd.GetVersion() >= (0, 25, 2):
            expected_failures.extend(
                [
                    IsAFailure(
                        "Dependent Reference .* cannot be resolved.",
                        at=material_layer_path,
                        requirement=cap.Requirements.AA_001,
                    ),  # Udim texture path
                    IsAFailure(
                        "Dependent Reference .* cannot be resolved.",
                        at=relative_layer_path,
                        requirement=cap.Requirements.AA_001,
                    ),  # Udim texture path
                ]
            )

        elif Usd.GetVersion() < (0, 24, 5):
            expected_failures.insert(
                5,
                IsAFailure(
                    'Dependent Reference .* should begin with "./" or "../".', at=absolute_layer_path
                ),  # absolute path
            )

        await self.assertRuleAsync(
            asset=get_url("anchoredAssetPath.usda"),
            rule=AnchoredAssetPathsChecker,
            asserts=expected_failures,
        )

        # Raise a failure for in memory layer
        await self.assertRuleAsync(
            asset=Usd.Stage.CreateInMemory(),
            rule=AnchoredAssetPathsChecker,
            asserts=[IsAFailure("In-memory layer is not allowed in an Atomic Asset.")],
        )

    async def testMdlSearchPath(self):
        # Test that MDL files and search paths are allowed
        await self.assertRuleAsync(
            asset=get_url("mdlTest.usda"),
            rule=AnchoredAssetPathsChecker,
            asserts=[
                IsAWarning(
                    "MDL \(.mdl\) asset .* relies on a search path. Materials will not load outside of Omniverse, or may differ between Omniverse versions.",
                    at=normalize_url(get_url("mdlTest.usda")),
                    requirement=cap.Requirements.AA_001,
                )
            ],
        )


class SupportedFileTypesCheckerTest(AsyncioValidationTestCase):
    async def testSupportedFileTypesChecker(self):
        expected_failures = [
            # alembic, vdb, xml
            IsAFailure("Dependent file '.*' is not a supported file type.", requirement=cap.Requirements.AA_002),
            IsAFailure("Dependent file '.*' is not a supported file type.", requirement=cap.Requirements.AA_002),
            IsAFailure("Dependent file '.*' is not a supported file type.", requirement=cap.Requirements.AA_002),
        ]
        # A version between USD 24.05 and 23.11, UsdUtils.ComputeAllDependencies() starts to
        # report dependency layers from a dependent .usdz layers.
        # https://github.com/PixarAnimationStudios/OpenUSD/commit/dc01ba9c2583d6a556b6b0d77c0d5268f9fcac96
        if Usd.GetVersion() >= (0, 24, 5):
            expected_failures.append(
                IsAFailure(
                    "Dependent file '.*' is not a supported file type.",
                    requirement=cap.Requirements.AA_002,
                )
            )

        expected_failures.append(
            IsAFailure(
                "Dependent file 'textures/diffuse.xyz' is not a supported file type.",
                requirement=cap.Requirements.AA_002,
            )
        )

        await self.assertRuleAsync(
            asset=get_url("supportedFileTypes.usda"),
            rule=SupportedFileTypesChecker,
            asserts=expected_failures,
        )

        # Should not raise any failure for in-memory empty stage
        await self.assertRuleAsync(
            asset=Usd.Stage.CreateInMemory(),
            rule=SupportedFileTypesChecker,
            asserts=[],
        )

    async def testMdlFormat(self):
        # Test that MDL files and search paths are allowed
        await self.assertRuleAsync(
            asset=get_url("mdlTest.usda"),
            rule=SupportedFileTypesChecker,
            asserts=[
                IsAWarning(
                    "MDL \(.mdl\) materials may not render correctly outside of Omniverse. For better compatibility, consider using USDPreviewSurface or MaterialX / OpenPBR. Path: .*",
                    requirement=cap.Requirements.AA_002,
                ),
                IsAWarning(
                    "MDL \(.mdl\) materials may not render correctly outside of Omniverse. For better compatibility, consider using USDPreviewSurface or MaterialX / OpenPBR. Path: .*",
                    requirement=cap.Requirements.AA_002,
                ),
            ],
        )


class UsdzUdimLimitationCheckerTest(AsyncioValidationTestCase):
    async def testUsdzUdimLimitationChecker(self):
        await self.assertRuleAsync(
            asset=get_url("usdzWithUdimTexture.usdz"),
            rule=UsdzUdimLimitationChecker,
            asserts=[
                IsAFailure(
                    f"{cap.Requirements.AA_OV_001.message} UDIM texture: ./textures/diffuse.<UDIM>.png",
                    at="Prim </World/reference_material_udim/diffuseTexture>",
                    requirement=cap.Requirements.AA_OV_001,
                ),
            ],
        )

        # Should not raise any failure for in-memory empty stage
        await self.assertRuleAsync(
            asset=Usd.Stage.CreateInMemory(),
            rule=UsdzUdimLimitationChecker,
            asserts=[],
        )
