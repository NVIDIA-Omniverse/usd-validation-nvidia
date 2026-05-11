# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import pathlib
import shutil
import typing
import unittest
import unittest.mock
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any

from common import AsyncioValidationTestCase, get_url, is_package_installed
from pxr import Gf, Sdf, Sdr, Usd, UsdGeom, UsdShade

import usd_validation_nvidia.capabilities as cap
import usd_validation_nvidia._material_checker as material_checker
from usd_validation_nvidia import (
    FixStatus,
    IssueFixer,
    IssuePredicates,
    MaterialOldMdlSchemaChecker,
    MaterialOutOfScopeChecker,
    MaterialPathChecker,
    MaterialUsdPreviewSurfaceChecker,
    ShaderImplementationSourceChecker,
    UsdDanglingMaterialBinding,
    UsdMaterialBindingApi,
    ValidationEngine,
    get_sdf_type_for_shader_property,
    register_requirements,
)
from usd_validation_nvidia.tests import IsAFailure, IsAWarning
from usd_validation_nvidia._material_checker import _InputValue as SourceInputValue


class MaterialOutOfScopeCheckerTest(AsyncioValidationTestCase):
    async def test_pass_no_payload(self):
        await self.assertRuleAsync(
            asset=get_url("usdMaterialBindingApiPass.usda"),
            rule=MaterialOutOfScopeChecker,
            asserts=[],
        )

    async def test_pass_with_payload(self):
        await self.assertRuleAsync(
            asset=get_url("materialInScope.usda"),
            rule=MaterialOutOfScopeChecker,
            asserts=[],
        )

    async def test_fail(self):
        await self.assertRuleAsync(
            asset=get_url("materialOutOfScope.usda"),
            rule=MaterialOutOfScopeChecker,
            asserts=[
                IsAFailure(
                    r"The relationship target from </Root/Mesh\.material:binding> in layer "
                    r"@.*materialOutOfScopeRef\.usda@ refers to a path outside the scope of the payload\."
                )
            ],
        )


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


class UsdMaterialBindingApiChecker(AsyncioValidationTestCase):
    async def test_api(self):
        await self.assertRuleAsync(
            asset=get_url("usdMaterialBindingApiFail.usda"),
            rule=UsdMaterialBindingApi,
            asserts=[
                IsAFailure(
                    "Prim 'Mesh' has a material binding but does not have the MaterialBindingApi.",
                    at=Sdf.Path("/World/Mesh"),
                ),
            ],
        )

    async def test_pass(self):
        await self.assertRuleAsync(
            asset=get_url("usdMaterialBindingApiPass.usda"),
            rule=UsdMaterialBindingApi,
            asserts=[],
        )

    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=get_url("usdMaterialBindingApiFail.usda"),
            rule=UsdMaterialBindingApi,
            predicate=IssuePredicates.ContainsMessage("MaterialBindingApi"),
        )


class MaterialPathCheckerTest(AsyncioValidationTestCase):
    async def test_relative_known_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/knownMaterial.usda"),
            rule=MaterialPathChecker,
            asserts=[],
        )

    async def test_relative_unknown_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/unknownMaterial.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure(
                    "The relative path ./unknown.mdl does not exist.",
                    at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset"),
                ),
            ],
        )

    async def test_missing_dot_slash_relative_known_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/incorrectMaterial.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure(
                    "Relative path material.mdl should be corrected to ./material.mdl.",
                    at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset"),
                ),
            ],
        )

    async def test_missing_dot_relative_known_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/missingDotMaterial.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure(
                    "Relative path /material.mdl should be corrected to ./material.mdl.",
                    at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset"),
                ),
            ],
        )

    # References
    async def test_reference_relative_known_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/layerKnownReference.usda"),
            rule=MaterialPathChecker,
            asserts=[],
        )

    async def test_reference_relative_unknown_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/layerUnknownReference.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure(
                    "The relative path ./unknown.mdl does not exist.",
                    at=Sdf.Path("/World/Looks/MatX/Shader.info:mdl:sourceAsset"),
                )
            ],
        )

    async def test_reference_relative_missing_dot_relative_known_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/layerIncorrectReference.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure(
                    "Relative path material.mdl should be corrected to ./material.mdl.",
                    at=Sdf.Path("/World/Looks/MatX/Shader.info:mdl:sourceAsset"),
                )
            ],
        )

    async def test_absolute_known_path(self):
        src_mdl: str = get_url("Materials/material.mdl")
        src_asset: str = get_url("Materials/absoluteMaterial.usda")
        content: str = pathlib.Path(src_asset).read_text()
        self.assertIn("replace.mdl", content)
        with TemporaryDirectory() as tmp:
            dst_mdl: str = os.path.join(tmp, "material.mdl")
            shutil.copy(src_mdl, dst_mdl)
            dst_asset: str = os.path.join(tmp, "absoluteMaterial.usda")
            pathlib.Path(dst_asset).write_text(content.replace("replace.mdl", dst_mdl))  # NOSONAR

            await self.assertRuleAsync(
                asset=dst_asset,
                rule=MaterialPathChecker,
                asserts=[],
            )

    async def test_fix_path(self):
        await self.assertSuggestionAsync(
            asset=get_url("Materials/incorrectMaterial.usda"),
            rule=MaterialPathChecker,
            predicate=IssuePredicates.ContainsMessage("should be corrected to"),
        )

    async def test_fix_path_reference(self):
        await self.assertSuggestionAsync(
            asset=get_url("Materials/layerIncorrectReference.usda"),
            rule=MaterialPathChecker,
            predicate=IssuePredicates.ContainsMessage("should be corrected to"),
        )

    async def test_fix_path_reference_path(self):
        with TemporaryDirectory() as tmp:
            shutil.copy(get_url("Materials/material.mdl"), os.path.join(tmp, "material.mdl"))
            shutil.copy(
                get_url("Materials/layerIncorrectReference.usda"),
                os.path.join(tmp, "layerIncorrectReference.usda"),
            )
            shutil.copy(get_url("Materials/incorrectMaterial.usda"), os.path.join(tmp, "incorrectMaterial.usda"))

            engine = ValidationEngine(init_rules=False)
            engine.enable_rule(MaterialPathChecker)

            result = engine.validate(os.path.join(tmp, "layerIncorrectReference.usda"))
            issues = result.issues()
            self.assertTrue(issues)

            # Perform fixing
            fixer = IssueFixer(os.path.join(tmp, "layerIncorrectReference.usda"))
            results = fixer.fix(issues)
            for result in results:
                self.assertEqual(result.status, FixStatus.SUCCESS, msg=result.exception)

            result = engine.validate(os.path.join(tmp, "layerIncorrectReference.usda"))
            issues = result.issues()
            self.assertFalse(issues)

    async def test_missing_mdl_path(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/missingMaterial.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAFailure("MDL file path must be present.", at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset"))
            ],
        )

    async def test_material_path_without_mdl_extension(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/wrongMaterialExtension.usda"),
            rule=MaterialPathChecker,
            asserts=[
                IsAWarning(
                    "It should have MDL (.mdl) file specified.",
                    at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset"),
                ),
                IsAFailure("The path abc does not exist", at=Sdf.Path("/Looks/MatX/Shader.info:mdl:sourceAsset")),
            ],
        )


class ShaderImplementationSourceCheckerTest(AsyncioValidationTestCase):
    async def test_success(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/shaderImplPass.usda"),
            rule=ShaderImplementationSourceChecker,
            asserts=[],
        )

    async def test_fails(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/shaderImplFail.usda"),
            rule=ShaderImplementationSourceChecker,
            asserts=[
                IsAFailure(
                    "The Shader has an invalid 'info:implementationSource'",
                    at=Sdf.Path("/Looks/Material/EmptySourceImpl"),
                ),
                IsAFailure(
                    "The Shader has an invalid 'info:implementationSource'",
                    at=Sdf.Path("/Looks/Material/IllegalSourceImpl"),
                ),
                IsAFailure(
                    "The Shader has an invalid 'info:id'",
                    at=Sdf.Path("/Looks/Material/NoShaderId"),
                ),
                IsAFailure(
                    "The Shader has an invalid 'info:id'",
                    at=Sdf.Path("/Looks/Material/EmptyShaderId"),
                ),
                IsAWarning(
                    "The Shader has multiple source implementation attributes",
                    at=Sdf.Path("/Looks/Material/AmbiguousShaderId"),
                ),
                IsAWarning(
                    "The Shader has multiple source implementation attributes",
                    at=Sdf.Path("/Looks/Material/AmbiguousShaderSourceAsset"),
                ),
                IsAWarning(
                    "The Shader has multiple source implementation attributes",
                    at=Sdf.Path("/Looks/Material/AmbiguousShaderCode"),
                ),
            ],
        )


class _FakeSdrProperty:
    def __init__(self, *, default_value=None, connectable=True, options=None):
        self._default_value = default_value
        self._connectable = connectable
        self._options = options or []

    def GetDefaultValue(self):
        return self._default_value

    def GetOptions(self):
        return self._options

    def IsConnectable(self):
        return self._connectable


class MaterialOldMdlSchemaCheckerTest(unittest.TestCase):
    def setUp(self):
        self.checker = MaterialOldMdlSchemaChecker(
            verbose=True,
            consumerLevelChecks=True,
            assetLevelChecks=True,
        )

    def test_update_deprecated_mdl_schema_warns_for_non_shader(self):
        stage = Usd.Stage.CreateInMemory()
        xform = UsdGeom.Xform.Define(stage, "/Xform")

        with unittest.mock.patch.object(self.checker, "_AddWarning") as add_warning:
            self.assertFalse(self.checker.update_deprecated_mdl_schema(stage, xform.GetPrim()))
            add_warning.assert_called_once()

    def test_update_deprecated_mdl_schema_warns_for_missing_data(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")

        with unittest.mock.patch.object(self.checker, "_AddWarning") as add_warning:
            self.assertFalse(self.checker.update_deprecated_mdl_schema(stage, shader.GetPrim()))
            add_warning.assert_called_once()

    def test_update_deprecated_mdl_schema_writes_mdl_source_asset(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        shader.GetPrim().CreateAttribute("module", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("module.mdl"))
        shader.GetPrim().CreateAttribute("name", Sdf.ValueTypeNames.Token).Set("Material")

        self.assertTrue(self.checker.update_deprecated_mdl_schema(stage, shader.GetPrim()))
        self.assertEqual(shader.GetSourceAsset("mdl").path, "module.mdl")
        self.assertEqual(shader.GetSourceAssetSubIdentifier("mdl"), "Material")

    def test_check_prim_adds_fix_for_old_mdl_schema(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        shader.GetImplementationSourceAttr().Set("mdlMaterial")

        with unittest.mock.patch.object(self.checker, "_AddFailedCheck") as add_failed:
            self.checker.CheckPrim(shader.GetPrim())
            add_failed.assert_called_once()


@dataclass
class _InputValue:
    """Stores value of the underlying Usd.Attribute for a UsdShade.Input object.
    holds both static and time-sampled values.
    """

    value: Any
    time_samples: list[Any]

    @classmethod
    def create_from_input(cls, usd_shade_input: UsdShade.Input):
        """Get the value from the usd_shade_input.
        If the attr has time-sampled values store a list of tuples: [(time, value), ]
        """
        value = None
        time_samples = None

        attr = usd_shade_input.GetAttr()
        if attr and attr.HasAuthoredValue():
            value = attr.Get()

            if attr.GetNumTimeSamples():
                time_samples = []
                for sample_time in attr.GetTimeSamples():
                    time_samples.append((sample_time, attr.Get(sample_time)))

        return _InputValue(value, time_samples)


@register_requirements(cap.Requirements.VM_PS_001, override=True)
class CustomizedMaterialUsdPreviewSurfaceChecker(MaterialUsdPreviewSurfaceChecker):

    # inputs to skip/not process for whatever reason.
    INPUTS_TO_SKIP: typing.ClassVar[list[str]] = [
        # Omniverse specific items to skip
        "excludeFromWhiteMode",
        "enable_opacity",
        "enable_specular_transmission",
        # other items to skip
        UsdShade.Tokens.sdrMetadata,
    ]

    def _should_input_be_filtered(self, shade_input: UsdShade.Input) -> bool:
        base_name = shade_input.GetBaseName()

        return base_name in self.INPUTS_TO_SKIP

    def _input_value_and_connections_transform(
        self, shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> tuple[bool, Sdf.ValueTypeName, Any, list[UsdShade.ConnectionSourceInfo]]:
        base_name = shade_input.GetBaseName()
        input_value = _InputValue.create_from_input(shade_input)
        type_name = shade_input.GetTypeName()
        connections = shade_input.GetConnectedSources()
        transformed = False

        sdf_type = get_sdf_type_for_shader_property(sdr_property)

        if (
            (base_name in ["metallic", "roughness"])
            and (sdf_type == Sdf.ValueTypeNames.Float)
            and (type_name == Sdf.ValueTypeNames.Color3f)
        ):
            (input_value, connections) = self.convert_color3f_to_float(input_value, connections)
            type_name = Sdf.ValueTypeNames.Float
            transformed = True

        return transformed, type_name, input_value, connections


class MaterialUsdPreviewSurfaceCheckerTest(AsyncioValidationTestCase):
    def test_input_value_captures_static_and_time_sampled_values(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        shade_input = shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        shade_input.Set(0.25)
        shade_input.GetAttr().Set(0.5, 1.0)

        input_value = SourceInputValue.create_from_input(shade_input)

        self.assertEqual(input_value.value, 0.25)
        self.assertEqual(input_value.time_samples, [(1.0, 0.5)])

    def test_write_usd_shade_input_value_updates_static_and_time_sampled_values(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        shade_input = shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        shade_input.Set(0.25)
        shade_input.GetAttr().Set(0.5, 1.0)

        MaterialUsdPreviewSurfaceChecker.write_usd_shade_input_value(
            shade_input,
            SourceInputValue(value=0.75, time_samples=[(1.0, 0.1), (2.0, 0.2)]),
        )

        self.assertEqual(shade_input.GetAttr().Get(), 0.75)
        self.assertAlmostEqual(shade_input.GetAttr().Get(1.0), 0.1)
        self.assertAlmostEqual(shade_input.GetAttr().Get(2.0), 0.2)

    def test_convert_color3f_to_float_updates_values_and_rgb_connections(self):
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        texture = UsdShade.Shader.Define(stage, "/Texture")
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        shade_input = shader.CreateInput("metallic", Sdf.ValueTypeNames.Color3f)
        shade_input.ConnectToSource(texture.ConnectableAPI(), "rgb")
        connections = list(shade_input.GetConnectedSources())

        input_value = SourceInputValue(
            value=Gf.Vec3f(0.1, 0.2, 0.3),
            time_samples=[(1.0, Gf.Vec3f(0.4, 0.5, 0.6))],
        )

        converted_value, converted_connections = MaterialUsdPreviewSurfaceChecker.convert_color3f_to_float(
            input_value,
            connections,
        )

        self.assertAlmostEqual(converted_value.value, 0.1)
        self.assertEqual(converted_value.time_samples[0][0], 1.0)
        self.assertAlmostEqual(converted_value.time_samples[0][1], 0.4)
        self.assertEqual(converted_connections[0][0].sourceName, "r")
        self.assertEqual(converted_connections[0][0].typeName, Sdf.ValueTypeNames.Float)

    def test_validation_helpers_report_metadata_connectability_value_and_connection_failures(self):
        checker = MaterialUsdPreviewSurfaceChecker(
            verbose=True,
            consumerLevelChecks=True,
            assetLevelChecks=True,
        )
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        token_input = shader.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token)
        token_input.Set("bad")
        token_input.GetAttr().SetMetadata("allowedTokens", ["bad"])
        token_input.SetConnectability(UsdShade.Tokens.interfaceOnly)
        source = UsdShade.Shader.Define(stage, "/Source")
        source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        token_input.ConnectToSource(source.ConnectableAPI(), "out")

        with unittest.mock.patch.object(
            material_checker,
            "get_sdf_type_for_shader_property",
            return_value=Sdf.ValueTypeNames.Token,
        ):
            property_with_options = _FakeSdrProperty(connectable=True, options=[("raw", ""), ("sRGB", "")])
            non_connectable_property = _FakeSdrProperty(connectable=False)
            input_value = SourceInputValue.create_from_input(token_input)

            self.assertIsNotNone(checker._validate_usd_shade_input_metadata(token_input, property_with_options))
            self.assertIsNotNone(
                checker._validate_usd_shade_input_connectability(token_input, property_with_options)
            )
            self.assertIsNotNone(
                checker._validate_usd_shade_input_value(token_input, input_value, non_connectable_property)
            )
            self.assertIsNotNone(
                checker._validate_usd_shade_input_connections(token_input, non_connectable_property)
            )
            self.assertIsNotNone(checker._validate_usd_shade_input_invalid_connection(token_input))

    def test_update_usd_shade_input_restores_default_type(self):
        checker = MaterialUsdPreviewSurfaceChecker(
            verbose=True,
            consumerLevelChecks=True,
            assetLevelChecks=True,
        )
        stage = Usd.Stage.CreateInMemory()
        shader = UsdShade.Shader.Define(stage, "/Shader")
        shade_input = shader.CreateInput("roughness", Sdf.ValueTypeNames.Color3f)

        with unittest.mock.patch.object(
            material_checker,
            "get_sdf_type_for_shader_property",
            return_value=Sdf.ValueTypeNames.Float,
        ):
            checker.update_usd_shade_input(
                shade_input,
                _FakeSdrProperty(default_value=0.5, connectable=True),
            )

        self.assertEqual(shade_input.GetTypeName(), Sdf.ValueTypeNames.Float)

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_api(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/usdPreviewSurfaceFail.usda"),
            rule=CustomizedMaterialUsdPreviewSurfaceChecker,
            asserts=[
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:diffuseColor: Expected type: 'color3f' actual type: 'float3'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:metallic: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:roughness: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/PreviewSurfaceTexture.inputs:specular: Has a connection; however this parameter is not defined in the specification.",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/diffuseColorTex.inputs:sourceColorSpace: Attribute token value: 'bad' is not present in the list of allowed tokens: '['raw', 'sRGB', 'auto']'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/diffuseColorTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/metallicTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/roughnessTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_cube/normalTex.outputs:rgb: Expected type: 'float3' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_cube"),
                ),
            ],
        )

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_pass(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/usdPreviewSurfacePass.usda"),
            rule=MaterialUsdPreviewSurfaceChecker,
            asserts=[],
        )

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_warns_when_shader_defs_missing(self):
        # Simulate a runtime where ``shaderDefs.usda`` is unavailable: the Sdr Registry
        # returns no ``Usd*`` shader nodes, so the checker has no shaders to validate
        # against and would otherwise silently pass.
        original = list(MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders)
        MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders.clear()
        # The checker uses ``GetShaderNodeNames`` on USD 25.08+ and ``GetNodeNames`` before
        # that; patch whichever this runtime exposes so the cache stays empty.
        registry_method = (
            "GetShaderNodeNames" if hasattr(Sdr.Registry, "GetShaderNodeNames") else "GetNodeNames"
        )
        try:
            with unittest.mock.patch.object(Sdr.Registry, registry_method, return_value=[]):
                await self.assertRuleAsync(
                    asset=get_url("Materials/usdPreviewSurfacePass.usda"),
                    rule=MaterialUsdPreviewSurfaceChecker,
                    asserts=[
                        IsAWarning(
                            "No UsdPreviewSurface shader definitions are registered with the Sdr Registry, "
                            "so this rule cannot validate any shaders. This typically means the "
                            "'shaderDefs.usda' shader resource is unavailable in the current USD runtime.",
                        ),
                    ],
                )
        finally:
            MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders[:] = original

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_autofix_suggestions(self):
        await self.assertSuggestionAsync(
            asset=get_url("Materials/usdPreviewSurfaceFail.usda"),
            rule=CustomizedMaterialUsdPreviewSurfaceChecker,
            predicate=None,
        )

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_time_sampled(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/usdPreviewSurfaceTimeSampledFail.usda"),
            rule=CustomizedMaterialUsdPreviewSurfaceChecker,
            asserts=[
                IsAFailure(
                    "/World/Looks/mtl_sphere/Shader.inputs:metallic: Expected type: 'float' actual type: 'color3f'",
                    at=Sdf.Path("/World/Looks/mtl_sphere"),
                ),
                IsAFailure(
                    "/World/Looks/mtl_sphere/roughnessTex.inputs:wrapT: Attribute contains time sampled value(s) that "
                    "are not present in the list of allowed tokens: ['black', 'clamp', 'repeat', 'mirror', "
                    "'useMetadata']",
                    at=Sdf.Path("/World/Looks/mtl_sphere"),
                ),
            ],
        )

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_fix_time_sampled(self):
        await self.assertRuleAsync(
            asset=get_url("Materials/usdPreviewSurfaceTimeSampledPass.usda"),
            rule=CustomizedMaterialUsdPreviewSurfaceChecker,
            asserts=[],
        )

    @unittest.skipIf(is_package_installed("usd-core"), "Tests disabled for usd-core")
    async def test_interface_only_connections(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        root = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(root)

        mat_path = "/World/Looks/TexturedMaterial"
        material = UsdShade.Material.Define(stage, mat_path)

        # UsdPreviewSurface shader
        shader = UsdShade.Shader.Define(stage, f"{mat_path}/PreviewSurface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
        shader.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
        shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

        # UsdUVTexture shader
        texture = UsdShade.Shader.Define(stage, f"{mat_path}/DiffuseTexture")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("./diffuse.png"))
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

        # Connect texture output -> shader diffuseColor
        shader.GetInput("diffuseColor").ConnectToSource(texture.ConnectableAPI(), "rgb")

        # Promote texture file input as a material interface input
        mat_file_input = material.CreateInput("DiffuseTexture", Sdf.ValueTypeNames.Asset)
        mat_file_input.Set(Sdf.AssetPath("./diffuse.png"))
        texture.GetInput("file").ConnectToSource(mat_file_input)

        # Promote opacityThreshold as a material interface input
        mat_opacity_input = material.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float)
        mat_opacity_input.Set(0.5)
        shader.GetInput("opacityThreshold").ConnectToSource(mat_opacity_input)

        await self.assertRuleAsync(
            asset=stage,
            rule=CustomizedMaterialUsdPreviewSurfaceChecker,
            asserts=[],
        )
