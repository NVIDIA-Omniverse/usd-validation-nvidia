# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import ANY

from common import AsyncioValidationTestCase, get_url
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

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
from usd_validation_nvidia.tests import IsAFailure, IsAnError, IsAWarning


def _create_portable_asset_paths_stage() -> Usd.Stage:
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths.append("sublayers\\materials.usda")

    prim = stage.DefinePrim("/Asset")
    prim.GetReferences().AddReference("references\\asset.usda")
    prim.GetPayloads().AddPayload("payloads\\asset.usda")
    prim.CreateAttribute("assetPath", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("textures\\diffuse.png"))

    return stage


def _create_normal_map_stage(*, source_color_space=None, bias=None, scale=None) -> Usd.Stage:
    stage = Usd.Stage.CreateInMemory()

    texture = UsdShade.Shader.Define(stage, "/Root/NormalTexture")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(get_url("textures/brick.jpg")))
    texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    if source_color_space is not None:
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(source_color_space)
    if bias is not None:
        texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(bias)
    if scale is not None:
        texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(scale)

    surface = UsdShade.Shader.Define(stage, "/Root/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(texture.ConnectableAPI(), "rgb")

    return stage


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

    async def test_fix_layer_payload_and_attribute_paths(self):
        await self.assertFailureAsync(asset=_create_portable_asset_paths_stage(), rule=PortableAssetPathChecker)
        await self.assertSuggestionAsync(
            asset=_create_portable_asset_paths_stage(),
            rule=PortableAssetPathChecker,
            predicate=None,
        )


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

    async def test_connectable_nesting_ok(self):
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/Material")
        shader = UsdShade.Shader.Define(stage, "/Material/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

        await self.assertSuccessAsync(asset=stage, rule=PrimEncapsulationChecker)

    async def test_connectable_nesting_nok(self):
        stage = Usd.Stage.CreateInMemory()

        UsdShade.Material.Define(stage, "/Material")
        UsdGeom.Scope.Define(stage, "/Material/Scope")
        shader_under_scope = UsdShade.Shader.Define(stage, "/Material/Scope/Shader")
        shader_under_scope.CreateIdAttr("UsdPreviewSurface")

        parent_shader = UsdShade.Shader.Define(stage, "/Shader")
        parent_shader.CreateIdAttr("UsdPreviewSurface")
        child_shader = UsdShade.Shader.Define(stage, "/Shader/Child")
        child_shader.CreateIdAttr("UsdUVTexture")

        await self.assertRuleAsync(
            asset=stage,
            rule=PrimEncapsulationChecker,
            asserts=[
                IsAFailure(
                    r"Connectable Shader </Material/Scope/Shader> can only have Connectable Container ancestors.*",
                    at=Sdf.Path("/Material/Scope/Shader"),
                ),
                IsAWarning(
                    r"Connectable Shader </Shader/Child> cannot reside under a non-Container Connectable Shader",
                    at=Sdf.Path("/Shader/Child"),
                ),
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
    async def test_stage_pass(self):
        await self.assertSuccessAsync(
            asset=_create_normal_map_stage(
                source_color_space="raw",
                bias=Gf.Vec4f(-1, -1, -1, 0),
                scale=Gf.Vec4f(2, 2, 2, 1),
            ),
            rule=NormalMapTextureChecker,
        )

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

    async def test_normal_map_missing_color_space_and_transform(self):
        await self.assertRuleAsync(
            asset=_create_normal_map_stage(),
            rule=NormalMapTextureChecker,
            asserts=[
                IsAWarning(r".*may need to set inputs:sourceColorSpace to 'raw'.*"),
                IsAWarning(r".*requires that inputs:scale be set to.*"),
            ],
        )

    async def test_normal_map_non_standard_transform(self):
        await self.assertRuleAsync(
            asset=_create_normal_map_stage(
                source_color_space="raw",
                bias=Gf.Vec4f(0, 0, 0, 0),
                scale=Gf.Vec4f(1, 1, 1, 1),
            ),
            rule=NormalMapTextureChecker,
            asserts=[
                IsAWarning(r".*reads an 8 bit Normal Map, but has non-standard inputs:scale.*"),
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
