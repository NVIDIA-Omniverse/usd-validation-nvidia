# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from pathlib import Path
from tempfile import TemporaryDirectory

import usd_validation_nvidia.capabilities as cap
from common import AsyncioValidationTestCase, get_url
from pxr import Sdf, Usd, UsdGeom, UsdShade, UsdUtils
from usd_validation_nvidia import (
    BaseRuleChecker,
    DelegateContextManager,
    KindChecker,
    MissingReferenceChecker,
    NormalMapTextureChecker,
    PrimEncapsulationChecker,
    TextureChecker,
    TypeChecker,
    ValidationEngine,
)
from usd_validation_nvidia.tests import IsAFailure, IsAnError, IsAWarning


class ExtentsCheckerTest(AsyncioValidationTestCase):

    async def test_examples(self):
        await self.assertExamplesSuggestionsAsync(requirement=cap.Requirements.VG_002)


class MissingReferenceCheckerTest(AsyncioValidationTestCase):

    async def test_validate_uri_ok(self):
        await self.assertRuleAsync(
            asset=get_url("basicFailures.usda"),
            rule=MissingReferenceChecker,
            asserts=[IsAFailure(".*Found unresolvable external dependency.*", at=Sdf.Path("/fake"))],
        )

    async def test_validate_stage_ok(self):
        with DelegateContextManager():
            stage = Usd.Stage.Open(get_url("basicFailures.usda"))
        await self.assertRuleAsync(
            asset=stage,
            rule=MissingReferenceChecker,
            asserts=[IsAFailure(".*Found unresolvable external dependency.*", at=Sdf.Path("/fake"))],
        )

    async def test_diagnostic_missing_from_unresolved_paths_is_reported(self):
        checker = MissingReferenceChecker(False, False, True)
        checker._references_by_path["missing.usda"].append(Sdf.Path("/A"))
        checker.CheckUnresolvedPaths([])

        self.assertEqualIssues(
            [IsAFailure(r"Found unresolvable external dependency 'missing\.usda'\.")],
            list(checker.GetIssues()),
        )

    async def test_duplicate_missing_references_reported_once_per_dependency(self):
        with TemporaryDirectory() as temp_dir:
            stage_path = Path(temp_dir) / "root.usda"
            with DelegateContextManager():
                stage = Usd.Stage.CreateNew(str(stage_path))
                for prim_path, asset_path in (
                    ("/A", "./missing_a.usda"),
                    ("/B", "./missing_a.usda"),
                    ("/C", "./missing_b.usda"),
                ):
                    prim = stage.DefinePrim(prim_path)
                    prim.GetReferences().AddReference(asset_path)
                stage.GetRootLayer().Save()

            await self.assertRuleAsync(
                asset=str(stage_path),
                rule=MissingReferenceChecker,
                asserts=[
                    IsAFailure(
                        r".*Found unresolvable external dependency '.*missing_a\.usda'\.",
                        at=[Sdf.Path("/A"), Sdf.Path("/B")],
                    ),
                    IsAFailure(
                        r".*Found unresolvable external dependency '.*missing_b\.usda'\.",
                        at=Sdf.Path("/C"),
                    ),
                ],
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

    async def test_examples(self):
        await self.assertExamplesSuggestionsAsync(requirement=cap.Requirements.AA_003)


class StageMetadataCheckerTest(AsyncioValidationTestCase):

    async def test_examples(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_001)
        await self.assertExamplesAsync(requirement=cap.Requirements.UN_002)


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

    async def test_usdz_allows_exr_and_jpeg_textures(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texture_dir = root / "textures"
            texture_dir.mkdir()
            (texture_dir / "environment.exr").write_bytes(b"exr")
            (texture_dir / "albedo.jpeg").write_bytes(b"\xff\xd8\xff\xd9")

            stage_path = root / "asset.usda"
            stage = Usd.Stage.CreateNew(str(stage_path))
            root_prim = UsdGeom.Xform.Define(stage, "/World").GetPrim()
            stage.SetDefaultPrim(root_prim)
            for name, texture_path in (
                ("EnvironmentTexture", "./textures/environment.exr"),
                ("AlbedoTexture", "./textures/albedo.jpeg"),
            ):
                shader = UsdShade.Shader.Define(stage, f"/World/{name}")
                shader.CreateIdAttr("UsdUVTexture")
                shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture_path))
            stage.GetRootLayer().Save()

            usdz_path = root / "asset.usdz"
            self.assertTrue(UsdUtils.CreateNewUsdzPackage(str(stage_path), str(usdz_path)))

            await self.assertSuccessAsync(asset=str(usdz_path), rule=TextureChecker)


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

    async def test_warns_and_fixes_normal_map_texture_inputs(self):
        await self.assertRuleAsync(
            asset=get_url("normalMapFixable.usda"),
            rule=NormalMapTextureChecker,
            asserts=[
                IsAWarning(
                    message=".*inputs:sourceColorSpace value 'auto'.*should set it to 'raw'.*",
                    at=Sdf.Path("/World/material/NormalMap"),
                ),
                IsAWarning(
                    message=".*non-standard inputs:scale and inputs:bias values.*",
                    at=Sdf.Path("/World/material/NormalMap"),
                ),
            ],
        )
        await self.assertSuggestionAsync(asset=get_url("normalMapFixable.usda"), rule=NormalMapTextureChecker)


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
