# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import ANY

from common import AsyncioValidationTestCase, get_url
from pxr import Sdf, Usd, UsdGeom

import usd_validation_nvidia.capabilities as cap
from usd_validation_nvidia import (
    BaseRuleChecker,
    ExtentsChecker,
    KindChecker,
    MissingReferenceChecker,
    NormalMapTextureChecker,
    PortableAssetPathChecker,
    PrimEncapsulationChecker,
    StageMetadataChecker,
    TextureChecker,
    TypeChecker,
    ValidationEngine,
)
from usd_validation_nvidia.tests import IsAFailure, IsAnError


class ExtentsCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        # When / Then
        await self.assertRuleAsync(
            asset=get_url("extent.usda"),
            rule=ExtentsChecker,
            asserts=[
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/ParentTransform/CubeNoExtent")),
                IsAFailure("Prim has incorrect extent value.*", at=Sdf.Path("/World/CubeIncorrectExtent")),
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/deforming_mesh_no_extent")),
                IsAFailure(
                    r"Incorrect extent value for prim at multiple times \(i.e. 1.0, 2.0\).*",
                    at=Sdf.Path("/World/deforming_mesh_incorrect_extent_samples"),
                ),
                IsAFailure("Prim does not have any extent value.*", at=Sdf.Path("/World/curve_0")),
                IsAFailure(r"Incorrect extent value for prim at time 2.0.*", at=Sdf.Path("/World/points_0")),
            ],
        )
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=ExtentsChecker,
            asserts=[],
        )

    async def test_autofix(self):
        await self.assertSuggestionAsync(asset=get_url("extent.usda"), rule=ExtentsChecker, predicate=None)


class MissingReferenceCheckerTest(AsyncioValidationTestCase):

    async def test_validate_uri_ok(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=MissingReferenceChecker,
            asserts=[IsAFailure(".*Could not open asset.*", at=Sdf.Path("/fake"))],
        )

    async def test_validate_stage_ok(self):
        stage = Usd.Stage.Open(get_url("basicFailures.usda"))
        await self.assertRuleAsync(
            asset=stage,
            rule=MissingReferenceChecker,
            asserts=[IsAFailure(".*Could not open asset.*", at=Sdf.Path("/fake"))],
        )

    async def test_extract_from_commentary(self):
        self.assertEqual(
            MissingReferenceChecker._extract_from_commentary(
                "In </Hello/World>: Could not open asset @asset.usda@ for reference introduced by "
                "@layer.usda@</Prim>. (instantiating stage on stage @stage.usda@ <0000000>)"
            ),
            (
                "Could not open asset @asset.usda@ for reference introduced by @layer.usda@</Prim>.",
                Sdf.Path("/Hello/World"),
                Sdf.AssetPath("asset.usda"),
            ),
        )
        self.assertEqual(
            MissingReferenceChecker._extract_from_commentary(
                "In </Hello/World>: Could not open asset @asset.usda@ for payload introduced by @layer.usda@</Prim>. "
                "(instantiating stage on stage @stage.usda@ <0000000>)"
            ),
            (
                "Could not open asset @asset.usda@ for payload introduced by @layer.usda@</Prim>.",
                Sdf.Path("/Hello/World"),
                Sdf.AssetPath("asset.usda"),
            ),
        )
        self.assertEqual(
            MissingReferenceChecker._extract_from_commentary(
                "Found unresolvable external dependency 'material.mdl'.",
            ),
            (
                "Found unresolvable external dependency 'material.mdl'.",
                None,
                None,
            ),
        )


class PortableAssetPathCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.AA_003)

    async def test_fix(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/RefPrim")
        prim.GetReferences().AddReference("\\directory\\asset.usda")

        await self.assertSuggestionAsync(asset=stage, rule=PortableAssetPathChecker, predicate=None)


class StageMetadataCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        await self.assertRuleAsync(
            asset=stage,
            rule=StageMetadataChecker,
            asserts=[
                IsAFailure(".*upAxis.*"),
                IsAFailure(".*metersPerUnit.*"),
                IsAFailure(".*invalid defaultPrim.*"),
            ],
        )
        await self.assertRequirementAsync(
            asset=stage,
            requirement=cap.Requirements.UN_001,
            asserts=[
                IsAFailure(ANY, requirement=cap.Requirements.UN_001),
            ],
        )
        await self.assertRequirementAsync(
            asset=stage,
            requirement=cap.Requirements.UN_002,
            asserts=[
                IsAFailure(ANY, requirement=cap.Requirements.UN_002),
            ],
        )


class PrimEncapsulationCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=PrimEncapsulationChecker,
            asserts=[
                IsAFailure(".*has an ancestor prim that is also a Gprim.*"),
            ],
        )


class TextureCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=TextureChecker,
            asserts=[
                IsAFailure(".*has unknown file format.*"),
            ],
        )


class KindCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=KindChecker,
            asserts=[
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/Sphere/NestedSphere"),
                ),
                IsAFailure('Invalid Kind "fake".*Must be one of', at=Sdf.Path("/Root/BadSphere")),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/MissingKind/LeafSphere"),
                ),
                IsAFailure(
                    'Invalid Kind "assembly".*Model prims can only be parented under.*',
                    at=Sdf.Path("/NotAModel/StillNotAModel"),
                ),
                IsAFailure('Invalid Kind "model".*Must be one of.*', at=Sdf.Path("/NotAModel/StillNotAModel/BaseKind")),
                IsAFailure(
                    'Invalid Kind "group".*Model prims can only be parented under.*',
                    at=Sdf.Path("/NotAModel/Subcomponent/AlsoNotAModel"),
                ),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/NotAModel/Subcomponent/BadComponent"),
                ),
            ],
        )
        await self.assertRuleAsync(
            asset=get_url("kindChecker.usda"),
            rule=KindChecker,
            asserts=[],
        )

    async def test_fix_without_suggestion(self):
        await self.assertRuleAsync(
            asset=get_url("kindCheckerFix.usda"),
            rule=KindChecker,
            asserts=[
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/EmptyKindAncestor/EmptyKindParent/node"),
                ),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/EmptyKindAncestor/EmptyKindParent/node/child"),
                ),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/EmptyKindAncestor/node"),
                ),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/Root/EmptyKindAncestor/node/parent/child"),
                ),
                IsAFailure(
                    'Invalid Kind "component".*Model prims can only be parented under.*',
                    at=Sdf.Path("/ComponentKindRoot/ComponentKindParent"),
                ),
            ],
        )

    async def test_fix_with_suggestion(self):
        await self.assertSuggestionAsync(asset=get_url("kindCheckerFix.usda"), rule=KindChecker, predicate=None)


class TypeCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("untyped.usda"),
            rule=TypeChecker,
            asserts=[
                IsAFailure(".*Missing type.*"),
            ],
        )


class CheckZipFileErrorRule(BaseRuleChecker):
    def CheckZipFile(self, zipFile, packagePath):
        raise ValueError("Error CheckZipFile.")


class NormalMapTextureCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("cleanNormalMapReader.usda"),
            rule=NormalMapTextureChecker,
            asserts=[],
        )

    async def test_normal_map_not_authored(self):
        await self.assertRuleAsync(
            asset=get_url("normalMapNotAuthored.usda"),
            rule=NormalMapTextureChecker,
            asserts=[],
        )

    async def test_normal_map_authored_empty(self):
        await self.assertRuleAsync(
            asset=get_url("normalMapAuthoredEmpty.usda"),
            rule=NormalMapTextureChecker,
            asserts=[
                IsAFailure(
                    message="UsdUVTexture prim </Root/Looks/Material/NormalTexture> has invalid or unresolvable inputs:file of @@",
                    at="Prim </Root/Looks/Material/NormalTexture>",
                )
            ],
        )


class CheckZipFileTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("usdzPass.usdz"),
            rule=CheckZipFileErrorRule,
            asserts=[IsAnError("Uncaught error: Error CheckZipFile.")],
        )

    async def test_validate_with_callbacks(self):
        """Test OMPE-11167 - ensure BaseRuleChecker.CheckZipFile() is run when asset_progress_fn is provided."""
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(CheckZipFileErrorRule)
        url = get_url("usdzPass.usdz")
        results = []

        await engine.validate_with_callbacks(
            url,
            asset_validated_fn=lambda result: results.append(result),
            asset_progress_fn=lambda *args, **kwargs: None,
        )
        self.assertEqual(results[0].asset, url, "The actual and expected URL are different.")
        self.assertEqual(IsAnError("Uncaught error: Error CheckZipFile."), results[0].issues()[0])
