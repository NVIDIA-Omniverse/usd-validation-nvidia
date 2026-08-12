# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from common import AsyncioValidationTestCase, get_url
from pxr import Sdf, Usd, UsdGeom, UsdShade

from usd_validation_nvidia import (
    IssuePredicates,
    SkelBindingAPIAppliedChecker,
    UsdDanglingMaterialBinding,
    UsdGeomSubsetChecker,
    UsdGeomSubsetFamiliesChecker,
    UsdGeomSubsetParentIsImageableChecker,
    UsdLuxSchemaChecker,
)
from usd_validation_nvidia.tests import IsAFailure


class UsdDanglingMaterialBindingChecker(AsyncioValidationTestCase):
    async def test_api(self):
        await self.assertRuleAsync(
            asset=get_url("usdDanglingMaterialBindingFail.usda"),
            rule=UsdDanglingMaterialBinding,
            asserts=[
                IsAFailure(
                    "Prim 'Mesh' has a material binding to '/Material' but that location does not exist",
                    at=Sdf.Path("/World/Mesh"),
                ),
            ],
        )

    async def test_pass(self):
        await self.assertRuleAsync(
            asset=get_url("usdDanglingMaterialBindingPass.usda"),
            rule=UsdDanglingMaterialBinding,
            asserts=[],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=get_url("usdDanglingMaterialBindingFail.usda"),
            rule=UsdDanglingMaterialBinding,
            predicate=IssuePredicates.ContainsMessage("Prim 'Mesh' has a material binding to '/Material'"),
        )


class UsdGeomSubsetCheckerTest(AsyncioValidationTestCase):
    async def test_attributes(self):
        await self.assertRuleAsync(
            asset=get_url("usdGeomSubset.usda"),
            rule=UsdGeomSubsetChecker,
            asserts=[
                IsAFailure(
                    "GeomSubset 'subset' has a material binding but no valid family name attribute.",
                    at=Sdf.Path("/World/Cube/subset"),
                ),
                IsAFailure(
                    "GeomSubset 'subset2' has a material binding but no valid family name attribute.",
                    at=Sdf.Path("/World/Cube2/subset2"),
                ),
            ],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=get_url("usdGeomSubset.usda"),
            rule=UsdGeomSubsetChecker,
            predicate=IssuePredicates.ContainsMessage("GeomSubset"),
        )


class UsdGeomSubsetFamiliesCheckerTest(AsyncioValidationTestCase):
    async def test_invalid_family(self):
        stage = Usd.Stage.CreateInMemory()
        mesh = UsdGeom.Mesh.Define(stage, "/World/Mesh")
        mesh.CreateFaceVertexCountsAttr([3])
        UsdGeom.Subset.SetFamilyType(mesh, UsdShade.Tokens.materialBind, UsdGeom.Tokens.partition)

        subset = UsdGeom.Subset.Define(stage, "/World/Mesh/subset")
        subset.CreateFamilyNameAttr().Set(UsdShade.Tokens.materialBind)
        subset.CreateElementTypeAttr().Set(UsdGeom.Tokens.face)
        subset.CreateIndicesAttr().Set([0, 0])

        await self.assertRuleAsync(
            asset=stage,
            rule=UsdGeomSubsetFamiliesChecker,
            asserts=[
                IsAFailure(
                    r"Imageable prim </World/Mesh> has invalid subset family 'materialBind': .*",
                    at=Sdf.Path("/World/Mesh"),
                ),
            ],
        )

    async def test_valid_family(self):
        stage = Usd.Stage.CreateInMemory()
        mesh = UsdGeom.Mesh.Define(stage, "/World/Mesh")
        mesh.CreateFaceVertexCountsAttr([3])
        UsdGeom.Subset.SetFamilyType(mesh, UsdShade.Tokens.materialBind, UsdGeom.Tokens.partition)

        subset = UsdGeom.Subset.Define(stage, "/World/Mesh/subset")
        subset.CreateFamilyNameAttr().Set(UsdShade.Tokens.materialBind)
        subset.CreateElementTypeAttr().Set(UsdGeom.Tokens.face)
        subset.CreateIndicesAttr().Set([0])

        await self.assertSuccessAsync(
            asset=stage,
            rule=UsdGeomSubsetFamiliesChecker,
        )


class UsdGeomSubsetParentIsImageableCheckerTest(AsyncioValidationTestCase):
    async def test_invalid_parent(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/World")
        UsdGeom.Subset.Define(stage, "/World/subset")

        await self.assertRuleAsync(
            asset=stage,
            rule=UsdGeomSubsetParentIsImageableChecker,
            asserts=[
                IsAFailure(
                    "GeomSubset </World/subset> has direct parent prim </World> that is not Imageable.",
                    at=Sdf.Path("/World/subset"),
                ),
            ],
        )

    async def test_valid_parent(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/World/Mesh")
        UsdGeom.Subset.Define(stage, "/World/Mesh/subset")

        await self.assertSuccessAsync(
            asset=stage,
            rule=UsdGeomSubsetParentIsImageableChecker,
        )


class UsdLuxSchemaCheckerTest(AsyncioValidationTestCase):
    async def test_unprefixed_attributes(self):
        await self.assertRuleAsync(
            asset=get_url("usdLuxSchema.usda"),
            rule=UsdLuxSchemaChecker,
            asserts=[
                IsAFailure(
                    "UsdLux attribute color has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.color"),
                ),
                IsAFailure(
                    "UsdLux attribute diffuse has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.diffuse"),
                ),
                IsAFailure(
                    "UsdLux attribute enableColorTemperature has been renamed in USD 21.02+ and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.enableColorTemperature"),
                ),
                # Failure("UsdLux attribute angle has been renamed in USD 21.02 and should be prefixed with 'inputs:'.", at="Attribute (angle) Prim </World/CylinderLight>"),
                IsAFailure(
                    "UsdLux attribute exposure has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.exposure"),
                ),
                IsAFailure(
                    "UsdLux attribute intensity has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.intensity"),
                ),
                IsAFailure(
                    "UsdLux attribute length has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.length"),
                ),
                IsAFailure(
                    "UsdLux attribute normalize has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.normalize"),
                ),
                IsAFailure(
                    "UsdLux attribute radius has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.radius"),
                ),
                IsAFailure(
                    "UsdLux attribute shaping:cone:angle has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:cone:angle"),
                ),
                IsAFailure(
                    "UsdLux attribute shaping:cone:softness has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:cone:softness"),
                ),
                IsAFailure(
                    "UsdLux attribute shaping:focus has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:focus"),
                ),
                IsAFailure(
                    "UsdLux attribute shaping:focusTint has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:focusTint"),
                ),
                # Failure("UsdLux attribute shaping:ies:file has been renamed in USD 21.02 and should be prefixed with 'inputs:'.", at="Attribute (shaping:ies:file) Prim </World/CylinderLight>"),
                IsAFailure(
                    "UsdLux attribute shaping:ies:angleScale has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:ies:angleScale"),
                ),
                IsAFailure(
                    "UsdLux attribute shaping:ies:normalize has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.shaping:ies:normalize"),
                ),
                IsAFailure(
                    "UsdLux attribute specular has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                    at=Sdf.Path("/World/CylinderLight.specular"),
                ),
            ],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=get_url("usdLuxSchema.usda"),
            rule=UsdLuxSchemaChecker,
            predicate=IssuePredicates.ContainsMessage("UsdLux attribute"),
        )

    async def test_usd_2108_no_errors(self):
        await self.assertRuleAsync(asset=get_url("usdLuxSchema2108.usda"), rule=UsdLuxSchemaChecker, asserts=[])


class SkelBindingAPIAppliedCheckerTest(AsyncioValidationTestCase):
    async def test_pass(self):
        await self.assertRuleAsync(
            asset=get_url("usdSkelBindingApiPass.usda"),
            rule=SkelBindingAPIAppliedChecker,
            asserts=[],
        )

    async def test_fail(self):
        await self.assertRuleAsync(
            asset=get_url("usdSkelBindingApiFail.usda"),
            rule=SkelBindingAPIAppliedChecker,
            asserts=[
                IsAFailure(
                    r"Found a UsdSkelBinding property \(skel:.*\), but no SkelBindingAPI applied on the prim\.",
                    at=Sdf.Path("/Root"),
                ),
            ],
        )

    async def test_suggestion(self):
        await self.assertSuggestionAsync(
            asset=get_url("usdSkelBindingApiFail.usda"),
            rule=SkelBindingAPIAppliedChecker,
            predicate=None,
        )
