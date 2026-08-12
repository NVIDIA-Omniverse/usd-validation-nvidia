# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import asyncio
import glob
import os
import pathlib
import tempfile
import unittest
from asyncio import get_running_loop
from contextlib import suppress
from dataclasses import FrozenInstanceError
from enum import Enum
from threading import current_thread, main_thread
from unittest.mock import ANY, Mock

from common import get_url
from pxr import Ar, Sdf, Usd, UsdGeom

from usd_validation_nvidia import (
    ArticulationChecker,
    AssetLocatedCallback,
    AssetProgress,
    AssetProgressCallback,
    AssetValidatedCallback,
    BaseRuleChecker,
    ByteAlignmentChecker,
    ColliderChecker,
    CompressionChecker,
    DanglingOverPrimChecker,
    DefaultPrimChecker,
    DelegateContextManager,
    ExtentsChecker,
    IndexedPrimvarChecker,
    Issue,
    IssueGroupsBy,
    IssuePredicates,
    IssueSeverity,
    IssuesList,
    KindChecker,
    LayerSpecChecker,
    ManifoldChecker,
    MassChecker,
    MaterialOldMdlSchemaChecker,
    MaterialOutOfScopeChecker,
    MaterialPathChecker,
    MaterialUsdPreviewSurfaceChecker,
    MissingReferenceChecker,
    NormalMapTextureChecker,
    NormalsExistChecker,
    NormalsValidChecker,
    NormalsWindingsChecker,
    ParameterType,
    PhysicsJointChecker,
    PrimEncapsulationChecker,
    Results,
    ResultsList,
    RigidBodyChecker,
    ShaderImplementationSourceChecker,
    SkelBindingAPIAppliedChecker,
    StageMetadataChecker,
    SubdivisionSchemeChecker,
    TextureChecker,
    TypeChecker,
    UnicodeNameChecker,
    UnusedMeshTopologyChecker,
    UnusedPrimvarChecker,
    UsdAsciiPerformanceChecker,
    UsdDanglingMaterialBinding,
    UsdGeomSubsetChecker,
    UsdGeomSubsetFamiliesChecker,
    UsdGeomSubsetParentIsImageableChecker,
    UsdLuxSchemaChecker,
    UsdMaterialBindingApi,
    UsdzPackageValidator,
    UserParameter,
    ValidateTopologyChecker,
    ValidationArgsExec,
    ValidationEngine,
    WeldChecker,
    ZeroAreaFaceChecker,
    is_importable,
    register_requirements,
    skip_if,
    skip_unless,
    unregister_requirements,
)
from usd_validation_nvidia.capabilities import Capabilities
from usd_validation_nvidia.capabilities import Capability as CapabilityDTO
from usd_validation_nvidia.capabilities import Feature as FeatureDTO
from usd_validation_nvidia.capabilities import Features
from usd_validation_nvidia.capabilities import Profile as ProfileDTO
from usd_validation_nvidia.capabilities import Requirement as RequirementDTO
from usd_validation_nvidia.capabilities import RequirementRef as RequirementRefDTO
from usd_validation_nvidia.capabilities import Requirements
from usd_validation_nvidia.tests import (
    AsyncioValidationTestCaseMixin,
    IsAFailure,
    IsAnError,
    IsAnInfo,
    IsAWarning,
    ValidationTestCaseMixin,
)


class EmptyRule(BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim):
        pass


class InitErrorRule(BaseRuleChecker):
    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool) -> None:
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        raise ValueError("Unexpected error __init__.")


class CheckPrimErrorRule(BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim):
        raise ValueError("Uncaught error CheckPrim.")


class MyRuleChecker(BaseRuleChecker):
    """
    Check that all prims are meshes for xforms
    """

    def CheckPrim(self, prim) -> None:
        if prim.GetTypeName() not in ("Mesh", "Xform"):
            self._AddFailedCheck(f"Prim <{prim.GetPath()}> has unsupported type '{prim.GetTypeName()}'.")


class Parameter(Enum):
    """
    Test parameters
    """

    TOLERANCE = ("tolerance", ParameterType.FLOAT, 0.001, None)

    def __init__(
        self,
        display_name: str,
        type: ParameterType,
        assigned_value: int | bool | float | str | None,
        enum_values: tuple[str, ...] | None,
    ):
        self.display_name = display_name
        self.type = type
        self.assigned_value = assigned_value
        self.enum_values = enum_values


class Requirement(Enum):
    """
    Test requirements
    """

    R1 = ("R1", "R1", "Message 1", "/r1", ("tag1", "tag2"), "1.0.0", ())
    R2 = ("R2", "R2", "Message 2", "/r2", ("tag2", "tag3"), "1.0.0", ())
    R3 = ("R3", "R3", "Message 3", "/r3", ("tag3", "tag4"), "1.0.0", ())
    R4 = ("R4", "R4", "Message 4", "/r4", ("tag4", "tag5"), "1.0.0", ())
    R5 = ("R5", "R5", "Message 5", "/r5", ("tag5", "tag6"), "1.0.0", ())
    R6 = ("R6", "R6", "Message 6", "/r6", ("tag6", "tag7"), "1.0.0", ())
    R7 = ("R7", "R7", "Message 7", "/r7", ("tag7", "tag8"), "1.0.0", ())
    R8 = ("R8", "R8", "Message 8", "/r8", ("tag8", "tag9"), "1.0.0", ())
    R9 = ("R9", "R9", "Message 9", "/r9", ("tag9", "tag10"), "1.0.0", (Parameter.TOLERANCE,))
    R10 = ("R10", "R10", "Message 10", "/r10", ("tag10", "tag11"), "1.0.0", (Parameter.TOLERANCE,))
    R11 = ("R11", "R11", "Message 11", "/r11", ("tag11", "tag12"), "1.0.0", (Parameter.TOLERANCE,))

    def __init__(
        self,
        code: str,
        display_name: str,
        message: str,
        path: str,
        tags: tuple[str, ...],
        version: str,
        parameters: tuple[Parameter, ...],
    ):
        self.code = code
        self.display_name = display_name
        self.message = message
        self.path = path
        self.tags = tags
        self.version = version
        self.parameters = parameters
        self.compatibility = None
        self.validator = None
        self.examples = ()


class ValidationEngineTest(unittest.IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin, ValidationTestCaseMixin):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        get_running_loop().set_debug(False)

    async def test_init_rules(self):
        engine = ValidationEngine(init_rules=True)
        self.assertTrue(engine.init_rules)
        self.assertTrue(engine.initialized_rules)
        self.assertTrue(engine.rules)

    async def test_processes_are_passed_to_compliance_checker(self):
        engine = ValidationEngine(init_rules=False, processes=4)
        checker = engine._create_compliance_checker()
        self.assertEqual(engine.processes, 4)
        self.assertEqual(checker.processes, 4)

    def test_constructor_options_are_read_only(self):
        engine = ValidationEngine(init_rules=False, variants=False, instance_prototypes=False, processes=4)

        with self.assertRaises(FrozenInstanceError):
            engine.init_rules = True
        with self.assertRaises(FrozenInstanceError):
            engine.variants = True
        with self.assertRaises(FrozenInstanceError):
            engine.instance_prototypes = True
        with self.assertRaises(FrozenInstanceError):
            engine.processes = 0

    async def test_no_instance_prototypes_skips_instance_proxy_traversal(self):
        class InstanceProxyRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                if prim.IsInstanceProxy():
                    self._AddInfo(str(prim.GetPath()), at=prim)

        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Prototype", "Xform")
        UsdGeom.Mesh.Define(stage, "/World/Prototype/Mesh")
        for name in ("A", "B"):
            instance = stage.DefinePrim(f"/World/{name}", "Xform")
            instance.GetReferences().AddInternalReference("/World/Prototype")
            instance.SetInstanceable(True)

        default_engine = ValidationEngine(init_rules=False)
        default_engine.enable_rule(InstanceProxyRule)
        default_results = default_engine.validate(stage)
        default_paths = [issue.message for issue in default_results.issues(IssuePredicates.IsInfo())]
        self.assertEqual(default_paths, ["/World/A/Mesh", "/World/B/Mesh"])

        filtered_engine = ValidationEngine(init_rules=False, instance_prototypes=False)
        filtered_engine.enable_rule(InstanceProxyRule)
        filtered_results = filtered_engine.validate(stage)
        filtered_paths = [issue.message for issue in filtered_results.issues(IssuePredicates.IsInfo())]
        self.assertEqual(filtered_paths, [])

    async def test_emtpy_rules(self):
        self.assertIssues(
            asset=get_url("curves.usda"),
            asserts=[
                IsAnError(message=".*No rules or requirements have been enabled.*"),
            ],
        )
        await self.assertIssuesAsync(
            asset=get_url("curves.usda"),
            asserts=[
                IsAnError(message=".*No rules or requirements have been enabled.*"),
            ],
        )

    async def test_empty_rules_with_callbacks(self):
        test_file = get_url("curves.usda")
        engine = ValidationEngine(init_rules=False)
        gather_assets = Mock(spec=AssetLocatedCallback)
        gather_progress = Mock(spec=AssetProgressCallback)
        assert_results = Mock(spec=AssetValidatedCallback)
        await engine.validate_with_callbacks(
            test_file,
            asset_located_fn=gather_assets,
            asset_progress_fn=gather_progress,
            asset_validated_fn=assert_results,
        )
        gather_assets.assert_called_with(test_file)
        gather_progress.assert_called_with(AssetProgress(asset=test_file, progress=1.0, results=ANY))
        assert_results.assert_called()
        async_result = assert_results.call_args[0][0]
        issues = async_result.issues()
        self.assertEqual(len(issues), 1)
        self.assertTrue("No rules or requirements have been enabled." in issues[0].message)

    async def testValidLayer(self):
        self.assertSuccess(asset=get_url("helloworld.usda"), rule=StageMetadataChecker)
        await self.assertSuccessAsync(asset=get_url("helloworld.usda"), rule=StageMetadataChecker)

    @staticmethod
    def _create_mdl_resolver_context(temp_dir: str) -> Ar.DefaultResolverContext:
        mdl_file_path = pathlib.Path(temp_dir) / "OmniPBR.mdl"
        mdl_file_path.write_text("// THIS IS OmniPBR.mdl!")
        return Ar.DefaultResolverContext([temp_dir])

    def test_validate_asset_path_resolver_context_ok(self):
        url = get_url("materialInScope.usda")

        with tempfile.TemporaryDirectory() as temp_dir:
            resolver_context = self._create_mdl_resolver_context(temp_dir)

            with Ar.ResolverContextBinder(resolver_context):
                self.assertSuccess(asset=url, rule=MaterialPathChecker)

    async def test_validate_async_asset_path_resolver_context_ok(self):
        url = get_url("materialInScope.usda")

        with tempfile.TemporaryDirectory() as temp_dir:
            resolver_context = self._create_mdl_resolver_context(temp_dir)

            with Ar.ResolverContextBinder(resolver_context):
                await self.assertSuccessAsync(asset=url, rule=MaterialPathChecker)

    def test_validate_stage_resolver_context_ok(self):
        url = get_url("materialInScope.usda")

        with tempfile.TemporaryDirectory() as temp_dir:
            resolver_context = self._create_mdl_resolver_context(temp_dir)
            stage = Usd.Stage.Open(url, resolver_context)

            self.assertSuccess(asset=stage, rule=MaterialPathChecker)

    async def test_validate_async_stage_resolver_context_ok(self):
        url = get_url("materialInScope.usda")

        with tempfile.TemporaryDirectory() as temp_dir:
            resolver_context = self._create_mdl_resolver_context(temp_dir)
            stage = Usd.Stage.Open(url, resolver_context)

            await self.assertSuccessAsync(asset=stage, rule=MaterialPathChecker)

    async def testExpectedFailure(self):
        self.assertRule(
            asset=get_url("curves.usda"),
            rule=StageMetadataChecker,
            asserts=[IsAFailure(message=ANY, rule=StageMetadataChecker)],
        )
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=StageMetadataChecker,
            asserts=[
                IsAFailure(message=ANY, rule=StageMetadataChecker),
            ],
        )

    async def testNonexistantFile(self):
        self.assertRule(
            asset=get_url("doesNotExist.usd"),
            rule=StageMetadataChecker,
            asserts=[IsAnError(message="Accessing.*failed.*")],
        )
        await self.assertRuleAsync(
            asset=get_url("doesNotExist.usd"),
            rule=StageMetadataChecker,
            asserts=[
                IsAnError(message="Accessing.*failed.*"),
            ],
        )

    async def testNonUsdFile(self):
        self.assertRule(
            asset=get_url(pathlib.Path("Materials", "Fieldstone.mdl")),
            rule=StageMetadataChecker,
            asserts=[
                IsAnError(message=".*is not a readable USD file and has no registered format handler.*"),
            ],
        )

    async def testConsistentResults(self):
        await self.assertRuleAsync(
            asset=get_url("helloworld.usda"),
            rule=StageMetadataChecker,
            asserts=[],
        )
        await self.assertRuleAsync(
            asset=get_url("helloworld.usda"),
            rule=StageMetadataChecker,
            asserts=[],
        )

    async def testEnableRule(self):
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=MyRuleChecker,
            asserts=[
                IsAFailure(message=ANY, rule=MyRuleChecker),
            ],
        )

    async def testEnableRequirement(self):
        await self.assertRequirementAsync(
            asset=get_url("Geometry/geometryFail.usda"),
            requirement=Requirements.VG_019,
            asserts=[
                IsAWarning(message=ANY, requirement=Requirements.VG_019),
                IsAWarning(message=ANY, requirement=Requirements.VG_019),
            ],
        )

    async def test_requirement_not_implemented_ok(self):
        stage = Usd.Stage.CreateInMemory()
        requirement = RequirementDTO(
            code="REQ.01",
            version="1.0.0",
        )

        await self.assertFailureAsync(
            asset=stage,
            requirement=requirement,
        )

    async def test_enable_single_requirement(self):
        @register_requirements(Requirement.R1, Requirement.R2)
        class MyRuleChecker(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(requirement=Requirement.R1)
                self._AddFailedCheck(requirement=Requirement.R2)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        await self.assertRequirementAsync(
            asset=stage,
            requirement=Requirement.R1,
            asserts=[
                IsAFailure(message=ANY, requirement=Requirement.R1),
            ],
        )

    async def test_enable_rule_and_requirement(self):
        @register_requirements(Requirement.R3, Requirement.R4)
        class MyRuleChecker(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(requirement=Requirement.R3)
                self._AddFailedCheck(requirement=Requirement.R4)

        class MyRuleChecker1(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(message="Another message")

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        engine = ValidationEngine(init_rules=False)
        engine.enable_requirement(Requirement.R3)
        engine.enable_rule(MyRuleChecker1)
        results = await engine.validate_async(stage)
        self.assertEqual(len(results.issues()), 2)

    async def test_enable_overlapping_rule_and_requirement(self):
        @register_requirements(Requirement.R5, Requirement.R6)
        class MyRuleChecker(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(requirement=Requirement.R5)
                self._AddFailedCheck(requirement=Requirement.R6)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(MyRuleChecker)
        engine.enable_requirement(Requirement.R5)
        results = await engine.validate_async(stage)
        self.assertEqual(len(results.issues()), 2)

    async def test_enable_disable_requirement(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_requirement(Requirement.R5)
        engine.disable_requirement(Requirement.R5)
        self.assertEqual(len(engine.requirements), 0)

    async def test_enable_disable_capability(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_capability(Capabilities.GEOMETRY)
        engine.disable_capability(Capabilities.GEOMETRY)
        self.assertEqual(len(engine.requirements), 0)

    async def test_enable_disable_capability_requirement(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_capability(Capabilities.GEOMETRY)
        engine.disable_requirement(Requirements.VG_025_V1_0_0)
        self.assertTrue(engine.requirements)
        self.assertNotIn(Requirements.VG_025_V1_0_0, engine.requirements)

    async def test_enable_disable_feature(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_feature(Features.MINIMAL_PLACEABLE_VISUAL)
        engine.disable_feature(Features.MINIMAL_PLACEABLE_VISUAL)
        self.assertEqual(len(engine.requirements), 0)

    async def test_enable_disable_feature_requirement(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_feature(Features.MINIMAL_PLACEABLE_VISUAL)
        engine.disable_requirement(Requirements.VG_025_V1_0_0)
        self.assertTrue(engine.requirements)
        self.assertNotIn(Requirements.VG_025_V1_0_0, engine.requirements)

    async def test_feature_not_implemented_ok(self):
        stage = Usd.Stage.CreateInMemory()
        feature = FeatureDTO(
            id="FET_00",
            version="1.0.0",
            path="",
            requirements=[
                RequirementDTO(
                    code="REQ.01",
                    version="1.0.0",
                )
            ],
        )

        await self.assertFailureAsync(
            asset=stage,
            feature=feature,
        )

    async def test_feature_requirement_ref_not_implemented_reports_requirement(self):
        implemented = RequirementDTO(code="REQ.IMPLEMENTED", version="1.0.0")
        dependency_ref = RequirementRefDTO(code="REQ.DEPENDENCY", version="1.0.0")

        @register_requirements(implemented)
        class FeatureRequirementRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None:
                self._AddFailedCheck("Implemented rule ran", requirement=implemented)

        try:
            stage = Usd.Stage.CreateInMemory()
            feature = FeatureDTO(
                id="FET_REQUIREMENT_REF_MISSING",
                version="1.0.0",
                path="",
                requirements=[implemented, dependency_ref],
            )
            await self.assertIssuesAsync(
                asset=stage,
                feature=feature,
                asserts=[
                    IsAFailure(message="Implemented rule ran", rule=FeatureRequirementRule, requirement=implemented),
                    IsAnError(message="Requirement (REQ.DEPENDENCY, 1.0.0) has not been implemented"),
                ],
            )
        finally:
            unregister_requirements(FeatureRequirementRule)

    async def test_feature_requirement_ref_runs_resolved_requirement_rule(self):
        implemented = RequirementDTO(code="REQ.IMPLEMENTED", version="1.0.0")
        dependency = RequirementDTO(code="REQ.DEPENDENCY", version="1.0.0")
        dependency_ref = RequirementRefDTO(code=dependency.code, version=dependency.version)

        @register_requirements(implemented)
        class ImplementedRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None:
                self._AddFailedCheck("Implemented rule ran", requirement=implemented)

        @register_requirements(dependency)
        class DependencyRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None:
                self._AddFailedCheck("Dependency rule ran", requirement=dependency)

        try:
            stage = Usd.Stage.CreateInMemory()
            feature = FeatureDTO(
                id="FET_REQUIREMENT_REF_RESOLVED",
                version="1.0.0",
                path="",
                requirements=[implemented, dependency_ref],
            )
            await self.assertIssuesAsync(
                asset=stage,
                feature=feature,
                asserts=[
                    IsAFailure(message="Implemented rule ran", rule=ImplementedRule, requirement=implemented),
                    IsAFailure(message="Dependency rule ran", rule=DependencyRule, requirement=dependency),
                ],
            )
        finally:
            unregister_requirements(ImplementedRule)
            unregister_requirements(DependencyRule)

    async def test_feature_dependency_not_implemented_reports_requirement(self):
        implemented = RequirementDTO(code="REQ.IMPLEMENTED", version="1.0.0")
        dependency = RequirementDTO(code="REQ.DEPENDENCY", version="1.0.0")
        dependency_feature = FeatureDTO(
            id="FET_DEPENDENCY_SOURCE",
            version="1.0.0",
            path="",
            requirements=[dependency],
        )

        @register_requirements(implemented)
        class FeatureDependencyRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None: ...

        try:
            stage = Usd.Stage.CreateInMemory()
            feature = FeatureDTO(
                id="FET_DEPENDENCY",
                version="1.0.0",
                path="",
                requirements=[implemented],
                dependencies=[dependency_feature],
            )
            await self.assertIssuesAsync(
                asset=stage,
                feature=feature,
                asserts=[
                    IsAnError(
                        message="Requirement (REQ.DEPENDENCY, 1.0.0) has not been implemented",
                        requirement=dependency,
                    )
                ],
            )
        finally:
            unregister_requirements(FeatureDependencyRule)

    def _create_mock_profile(self, capabilities=None):
        mock_profile = Mock()
        mock_profile.features = []
        mock_profile.capabilities = capabilities or [Capabilities.GEOMETRY]
        return mock_profile

    async def test_enable_profile(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(self._create_mock_profile())
        self.assertEqual(len(engine.enabled_profiles), 1)
        self.assertTrue(engine.requirements)

    async def test_profile_not_implemented_ok(self):
        asset = Usd.Stage.CreateInMemory()
        profile = ProfileDTO(
            id="MY_PROFILE",
            version="1.0.0",
            path="",
            capabilities=[],
            features=[
                FeatureDTO(
                    id="MyFeature",
                    version="1.0.0",
                    path="",
                    requirements=[
                        RequirementDTO(
                            code="MY_REQUIREMENT",
                            version="1.0.0",
                        )
                    ],
                )
            ],
        )
        await self.assertFailureAsync(
            asset=asset,
            profile=profile,
        )

    async def test_enable_disable_profile(self):
        engine = ValidationEngine(init_rules=False)
        mock_profile = self._create_mock_profile()
        engine.enable_profile(mock_profile)
        engine.disable_profile(mock_profile)
        self.assertEqual(len(engine.requirements), 0)

    async def test_enable_disable_profile_requirement(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(self._create_mock_profile())
        engine.disable_requirement(Requirements.VG_025_V1_0_0)
        self.assertTrue(engine.requirements)
        self.assertNotIn(Requirements.VG_025_V1_0_0, engine.requirements)

    async def test_stamp_writes_metadata(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/Root", "Xform")
        stage.SetDefaultPrim(stage.GetPrimAtPath("/Root"))
        mock_profile = Mock()
        mock_profile.id = "Test-Profile"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = []
        mock_profile.features = []
        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        engine.enable_rule(EmptyRule)
        results = engine.validate(stage)
        engine.stamp_asset(stage, results)
        metadata = stage.GetRootLayer().customLayerData
        self.assertIn("asset_validator", metadata)
        validation = metadata["asset_validator"]["validation"]
        self.assertEqual(validation["profiles"], {"Test-Profile": {"profile_version": "1.0.0"}})
        self.assertIn("timestamp", validation)
        self.assertIn("validator_version", validation)

    async def test_stamp_skipped_on_failure(self):
        stage = Usd.Stage.CreateInMemory()
        mock_profile = Mock()
        mock_profile.id = "Test-Profile"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = [Capabilities.GEOMETRY]
        mock_profile.features = []
        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        engine.enable_rule(StageMetadataChecker)
        results = engine.validate(stage)
        engine.stamp_asset(stage, results)
        metadata = stage.GetRootLayer().customLayerData
        self.assertNotIn("asset_validator", metadata)

    async def test_stamp_skipped_without_profile(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Robot/body")
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        results = engine.validate(stage)
        engine.stamp_asset(stage, results)
        metadata = stage.GetRootLayer().customLayerData
        self.assertNotIn("asset_validator", metadata)

    async def test_stamp_custom_key(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/Root", "Xform")
        stage.SetDefaultPrim(stage.GetPrimAtPath("/Root"))
        mock_profile = Mock()
        mock_profile.id = "Test-Profile"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = []
        mock_profile.features = []
        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        engine.enable_rule(EmptyRule)
        results = engine.validate(stage)
        engine.stamp_asset(stage, results, key="SimReady_Metadata")
        metadata = stage.GetRootLayer().customLayerData
        self.assertNotIn("asset_validator", metadata)
        self.assertIn("SimReady_Metadata", metadata)
        self.assertEqual(
            metadata["SimReady_Metadata"]["validation"]["profiles"],
            {"Test-Profile": {"profile_version": "1.0.0"}},
        )

    async def test_stamp_save_on_file(self):
        with tempfile.NamedTemporaryFile(suffix=".usda", delete=False) as f:
            tmp_path = f.name
        try:
            stage = Usd.Stage.CreateNew(tmp_path)
            stage.DefinePrim("/Root", "Xform")
            stage.SetDefaultPrim(stage.GetPrimAtPath("/Root"))
            stage.Save()
            del stage
            mock_profile = Mock()
            mock_profile.id = "Test-Profile"
            mock_profile.version = "1.0.0"
            mock_profile.capabilities = []
            mock_profile.features = []
            engine = ValidationEngine(init_rules=False)
            engine.enable_profile(mock_profile)
            engine.enable_rule(EmptyRule)
            results = engine.validate(tmp_path)
            layer = engine.stamp_asset(tmp_path, results)
            self.assertIsNotNone(layer)
            layer.Save()
            reopened = Usd.Stage.Open(tmp_path)
            metadata = reopened.GetRootLayer().customLayerData
            self.assertIn("asset_validator", metadata)
            self.assertEqual(
                metadata["asset_validator"]["validation"]["profiles"],
                {"Test-Profile": {"profile_version": "1.0.0"}},
            )
        finally:
            os.unlink(tmp_path)

    async def test_unregistered_requirement(self):
        @register_requirements(Requirement.R7)
        class RuleChecker(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(requirement=Requirement.R7)
                self._AddFailedCheck(requirement=Requirement.R8)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh1")

        await self.assertRequirementAsync(
            asset=stage,
            requirement=Requirement.R7,
            asserts=[
                IsAFailure(message=ANY),
                IsAnError(message=ANY),
            ],
        )
        await self.assertRequirementAsync(
            asset=stage,
            requirement=Requirement.R8,
            asserts=[
                IsAnError(message=ANY),
            ],
        )

    async def test_report_unregistered_requirement(self):
        class RuleChecker(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                self._AddFailedCheck(requirement=Requirement.R1)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")
        await self.assertRuleAsync(
            asset=stage,
            rule=RuleChecker,
            asserts=[
                IsAnError(message=".*Rule RuleChecker is not registered to requirement R1.*"),
            ],
        )

    async def test_engine_passes_parameters_to_rules(self):
        @register_requirements(Requirement.R9)
        class ParameterizedRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                tolerance = self.parameters["tolerance"]
                self._AddFailedCheck(f"Parameter value: {tolerance.assigned_value}", requirement=Requirement.R9)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        engine = ValidationEngine(init_rules=False)
        engine.enable_requirement(Requirement.R9)

        self.assertIn("tolerance", engine.parameters)
        self.assertEqual(engine.parameters["tolerance"].assigned_value, 0.001)

        results = await engine.validate_async(stage)
        issues = results.issues()
        self.assertEqual(len(issues), 1)
        self.assertIn("0.001", issues[0].message)

    async def test_engine_override_value(self):
        """Test that engine.add_parameter() with UserParameter updates the parameter value and rules receive the new value."""

        @register_requirements(Requirement.R10)
        class ParameterizedRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim):
                tolerance = self.parameters["tolerance"]
                self._AddFailedCheck(f"Parameter value: {tolerance.assigned_value}", requirement=Requirement.R10)

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        engine = ValidationEngine(init_rules=False)
        engine.enable_requirement(Requirement.R10)

        # Validate with initial parameter value
        results = await engine.validate_async(stage)
        issues = results.issues()
        self.assertEqual(len(issues), 1)
        self.assertIn("0.001", issues[0].message)

        # Update parameter using add() with UserParameter
        base_param = engine.parameters["tolerance"]
        user_param = UserParameter(parameter=base_param, assigned_value=0.005)
        engine.add_parameter(user_param)

        # Verify rules receive updated value
        results = await engine.validate_async(stage)
        issues = results.issues()
        self.assertEqual(len(issues), 1)
        self.assertIn("0.005", issues[0].message)

    async def test_engine_override_value_nonexistent(self):
        """Test that accessing non-existent parameter raises KeyError."""
        engine = ValidationEngine(init_rules=False)
        engine.enable_requirement(Requirement.R10)

        with self.assertRaises(KeyError):
            # Trying to get a parameter that doesn't exist
            engine.parameters["nonexistent"]

    async def test_enable_disable_rule_updates_parameters(self):
        @register_requirements(Requirement.R11)
        class ParameterizedRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim): ...

        engine = ValidationEngine(init_rules=False)
        self.assertNotIn("tolerance", engine.parameters)
        engine.enable_rule(ParameterizedRule)
        self.assertIn("tolerance", engine.parameters)
        engine.disable_rule(ParameterizedRule)
        self.assertNotIn("tolerance", engine.parameters)

    async def test_enable_capability(self):
        stage = Usd.Stage.CreateInMemory()
        mesh_prim = UsdGeom.Mesh.Define(stage, "/Mesh")
        mesh_prim.CreateSubdivisionSchemeAttr().Set("none")
        mesh_prim.CreateFaceVertexCountsAttr().Set([3])
        mesh_prim.CreateFaceVertexIndicesAttr().Set([0, 1, 2])
        mesh_prim.CreatePointsAttr().Set([(0, 0, 0), (1, 0, 0), (2, 0, 0)])

        await self.assertFailureAsync(
            asset=stage,
            capability=Capabilities.GEOMETRY,
        )

    async def test_capability_not_implemented_ok(self):
        stage = Usd.Stage.CreateInMemory()

        capability = CapabilityDTO(
            id="MY_CAPABILITY",
            version="1.0.0",
            path="",
            requirements=[
                RequirementDTO(
                    code="Requirement",
                    version="1.0.0",
                )
            ],
        )

        await self.assertFailureAsync(
            asset=stage,
            capability=capability,
        )

    async def test_disable_rule_init_false(self):
        test_file = get_url("curves.usda")
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(EmptyRule)
        engine.enable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 1)

        # Disable rules that cause failures and validate again
        engine.disable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(len(result.issues()), 0)

        # We are able to enable and disable the rules again
        engine.enable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 1)
        engine.disable_rule(StageMetadataChecker)
        result = engine.validate(test_file)
        self.assertEqual(result.asset, test_file)
        self.assertEqual(len(result.issues()), 0)

    async def test_disable_rule_init_true(self):
        engine = ValidationEngine(init_rules=True)
        self.assertIn(StageMetadataChecker, engine.rules)

        engine.disable_rule(StageMetadataChecker)
        self.assertNotIn(StageMetadataChecker, engine.rules)

    async def testMinimalRules(self):
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=MyRuleChecker,
            asserts=[
                IsAFailure(message=ANY, rule=MyRuleChecker),
            ],
        )

    async def test_rule_cannot_load(self):
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=InitErrorRule,
            asserts=[
                IsAnError(message=".*Failed to initialize rule.*", rule=InitErrorRule),
                IsAnError(message="No rules or requirements have been enabled."),
            ],
        )

    async def test_rule_uncaught_exception(self):
        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=CheckPrimErrorRule,
            asserts=[
                IsAnError(message=".*Uncaught error.*", rule=CheckPrimErrorRule),
                IsAnError(message=".*Uncaught error.*", rule=CheckPrimErrorRule),
            ],
        )

    async def test_rule_condition_skip_reports_info(self):
        @skip_unless(
            is_importable("_usd_validation_nvidia_missing_schema_for_test"),
            reason="Missing test rule support.",
        )
        class RuleConditionSkippedRule(BaseRuleChecker):
            def CheckStage(self, stage: Usd.Stage) -> None:
                self._AddFailedCheck("Skipped rule should not run.")

        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=RuleConditionSkippedRule,
            asserts=[
                IsAnInfo(message="Skipping rule RuleConditionSkippedRule: Missing test rule support."),
                IsAnError(message="No rules or requirements have been enabled."),
            ],
        )

    async def test_rule_condition_skip_if_false_runs_rule(self):
        @skip_if(False, reason="Should not skip.")
        class RuntimeSupportedRule(BaseRuleChecker):
            def CheckStage(self, stage: Usd.Stage) -> None:
                self._AddInfo("Rule ran.")

        await self.assertRuleAsync(
            asset=get_url("curves.usda"),
            rule=RuntimeSupportedRule,
            asserts=[
                IsAnInfo(message="Rule ran."),
            ],
        )

    async def testValidateAsync(self):
        self.assertFailure(
            asset=get_url("doesNotExist.usd"),
            rule=StageMetadataChecker,
        )
        await self.assertFailureAsync(
            asset=get_url("doesNotExist.usd"),
            rule=StageMetadataChecker,
        )
        self.assertSuccess(
            asset=get_url("helloworld.usda"),
            rule=StageMetadataChecker,
        )
        await self.assertSuccessAsync(
            asset=get_url("helloworld.usda"),
            rule=StageMetadataChecker,
        )
        self.assertFailure(
            asset=get_url("curves.usda"),
            rule=StageMetadataChecker,
        )
        await self.assertFailureAsync(
            asset=get_url("curves.usda"),
            rule=StageMetadataChecker,
        )

    async def test_validate_with_callbacks(self):
        test_file = get_url("helloworld.usda")

        gather_assets = Mock(spec=AssetLocatedCallback)
        assert_results = Mock(spec=AssetValidatedCallback)

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        task = engine.validate_with_callbacks(
            test_file,
            asset_located_fn=gather_assets,
            asset_validated_fn=assert_results,
        )
        await task

        gather_assets.assert_called_with(test_file)
        assert_results.assert_called()
        (async_result,), _ = assert_results.call_args
        blocking_result = engine.validate(async_result.asset)
        self.assertEqual(blocking_result, async_result)
        self.assertEqual(task.result(), ResultsList(results=[async_result]))

    async def test_validate_with_progress(self):
        test_file = get_url("helloworld.usda")

        assert_progress = Mock(spec=AssetProgressCallback)

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        await engine.validate_with_callbacks(
            test_file,
            asset_progress_fn=assert_progress,
        )

        assert_progress.assert_called_with(AssetProgress(asset=test_file, progress=1.0, results=ANY))

    async def testNonexistantFileWithCallbacks(self):
        test_file = get_url("doesNotExist.usd")

        gather_assets = Mock(spec=AssetLocatedCallback)
        assert_results = Mock(spec=AssetValidatedCallback)

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        await engine.validate_with_callbacks(
            test_file,
            asset_located_fn=gather_assets,
            asset_validated_fn=assert_results,
        )

        gather_assets.assert_called_with(test_file)
        assert_results.assert_called()
        (async_result,), _ = assert_results.call_args
        blocking_result = engine.validate(async_result.asset)
        self.assertEqual(blocking_result, async_result)

    async def testValidateFolderSynchronously(self):
        self.assertRaisesRegex(
            RuntimeError,
            ".*Synchronous validation of folders/containers is not available.*",
            ValidationEngine().validate,
            get_url(),
        )

    async def testValidateFolderAsync(self):
        test_dir = get_url()
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        results = await engine.validate_async(test_dir)
        # Filter out some version specific assets
        exclusions = ["Unicode"]
        if Usd.GetVersion() >= (0, 24, 11):
            exclusions.append("sdfRelationshipSpec")
        results = [result for result in results if not any(exclusion in result.asset for exclusion in exclusions)]
        all_assets = set(
            pathlib.Path(x)
            for x in glob.glob(get_url("**/*.usd*"), recursive=True)
            if not any(exclusion in x for exclusion in exclusions)
        )
        self.assertEqual(
            set(pathlib.Path(x.asset) for x in results),
            all_assets,
        )
        for result in results:
            asset_result = engine.validate(result.asset)
            self.assertEqual(
                result.issues(IssuePredicates.IsError()),
                asset_result.issues(IssuePredicates.IsError()),
                f"{result.asset} errors did not match",
            )
            self.assertEqual(
                result.issues(IssuePredicates.IsWarning()),
                asset_result.issues(IssuePredicates.IsWarning()),
                f"{result.asset} warnings did not match",
            )
            self.assertEqual(
                len(result.issues(IssuePredicates.IsFailure())), len(asset_result.issues(IssuePredicates.IsFailure()))
            )
            for lh, rh in zip(
                result.issues(IssuePredicates.IsFailure()), asset_result.issues(IssuePredicates.IsFailure())
            ):
                # Some failures produce indeterminate messages (eg anon session layers). Rather than strictly
                # asserting the messages match across validation runs, we just assert that the failures come
                # from the same rules in the same order.
                self.assertEqual(lh.rule, rh.rule, f"{result.asset} failures did not match")

    async def testValidateFolderWithCallbacks(self):
        test_dir = get_url()

        gather_assets = Mock(spec=AssetLocatedCallback)
        assert_results = Mock(spec=AssetValidatedCallback)

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        await engine.validate_with_callbacks(
            test_dir,
            asset_located_fn=gather_assets,
            asset_validated_fn=assert_results,
        )

        gathered_assets = set()

        # Filter out some version specific assets
        exclusions = ["Unicode"]
        if Usd.GetVersion() >= (0, 24, 11):
            exclusions.append("sdfRelationshipSpec")
        for call in gather_assets.call_args_list:
            (asset,), _ = call
            if not any(exclusion in asset for exclusion in exclusions):
                gathered_assets.add(pathlib.Path(asset))
        self.assertEqual(
            gathered_assets,
            set(
                pathlib.Path(x)
                for x in glob.glob(get_url("**/*.usd*"), recursive=True)
                if not any(exclusion in x for exclusion in exclusions)
            ),
        )

        for call in assert_results.call_args_list:
            (async_result,), _ = call
            if any(exclusion in async_result.asset for exclusion in exclusions):
                continue
            blocking_result = engine.validate(async_result.asset)
            self.assertEqual(
                blocking_result.issues(IssuePredicates.IsError()),
                async_result.issues(IssuePredicates.IsError()),
                f"{async_result.asset} errors did not match",
            )
            self.assertEqual(
                blocking_result.issues(IssuePredicates.IsWarning()),
                async_result.issues(IssuePredicates.IsWarning()),
                f"{async_result.asset} warnings did not match",
            )
            self.assertEqual(
                len(blocking_result.issues(IssuePredicates.IsFailure())),
                len(async_result.issues(IssuePredicates.IsFailure())),
            )
            for lh, rh in zip(
                blocking_result.issues(IssuePredicates.IsFailure()), async_result.issues(IssuePredicates.IsFailure())
            ):
                # Some failures produce indeterminate messages (eg anon session layers). Rather than strictly
                # asserting the messages match across validation runs, we just assert that the failures come
                # from the same rules in the same order.
                self.assertEqual(lh.rule, rh.rule, f"{async_result.asset} failures did not match")

    async def testLiveStageSynchronously(self):
        self.assertSuccess(asset=Usd.Stage.Open(get_url("helloworld.usda")), rule=StageMetadataChecker)
        self.assertSuccess(asset=get_url("helloworld.usda"), rule=StageMetadataChecker)

        self.assertFailure(asset=Usd.Stage.Open(get_url("curves.usda")), rule=StageMetadataChecker)
        self.assertFailure(asset=get_url("curves.usda"), rule=StageMetadataChecker)

    async def testLiveStageAsync(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        for file_name in (
            "helloworld.usda",
            "curves.usda",
        ):
            test_file = get_url(file_name)
            stage = Usd.Stage.Open(test_file)
            layers = [x.identifier for x in stage.GetLayerStack()]
            target = stage.GetEditTarget()
            sync_result = engine.validate(test_file)
            live_results = await engine.validate_async(stage)
            self.assertEqual(len(live_results), 1)
            # the live results will have a stage description rather than the file itself
            self.assertNotEqual(sync_result.asset, live_results[0].asset)
            self.assertEqual(sync_result.issues(), live_results[0].issues())
            # makes sure the stage's edit target and layer stack are preserved
            # we should probably test that composition is unchanged, but we can
            # leave that until it comes up as an issue.
            self.assertEqual(stage.GetEditTarget(), target)
            self.assertEqual(len(stage.GetLayerStack()), len(layers))
            for i in range(len(layers)):
                self.assertEqual(stage.GetLayerStack()[i].identifier, layers[i])

    async def testLiveStageAsyncWithCallbacks(self):
        test_file = get_url("helloworld.usda")
        stage = Usd.Stage.Open(test_file)

        gather_assets = Mock(spec=AssetLocatedCallback)
        assert_results = Mock(spec=AssetValidatedCallback)

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        await engine.validate_with_callbacks(
            stage,
            asset_located_fn=gather_assets,
            asset_validated_fn=assert_results,
        )

        gather_assets.assert_called_with(stage)
        assert_results.assert_called()
        (async_result,), _ = assert_results.call_args
        self.assertEqual(async_result.asset, engine.describe(stage))
        blocking_result = engine.validate(test_file)
        # the live results will have a stage description rather than the file itself
        self.assertNotEqual(blocking_result.asset, async_result.asset)
        self.assertEqual(blocking_result.issues(), async_result.issues())

    async def testFilteredValidation(self):
        test_file = get_url("basicFailures.usda")
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(MissingReferenceChecker)
        with DelegateContextManager():
            stage = Usd.Stage.Open(test_file)
        full_result = engine.validate(stage)

        mask = Usd.StagePopulationMask()
        mask.Add("/fake")
        mask.Add("/Root/Sphere")
        mask.Add("/NotAModel/StillNotAModel/BaseKind")
        mask.Add("/Root/Looks/Surface")
        with DelegateContextManager():
            stage.SetPopulationMask(mask)
        masked_result = engine.validate(stage)

        self.assertEqual(full_result.asset, masked_result.asset)
        self.assertEqual(full_result.issues(IssuePredicates.IsError()), masked_result.issues(IssuePredicates.IsError()))
        self.assertEqual(
            full_result.issues(IssuePredicates.IsWarning()), masked_result.issues(IssuePredicates.IsWarning())
        )
        self.assertEqual(
            full_result.issues(IssuePredicates.IsFailure()), masked_result.issues(IssuePredicates.IsFailure())
        )

    async def testValidationIssuesList(self):
        test_dir: str = get_url()
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        results: ResultsList = await engine.validate_async(test_dir)
        number_results: int = len(results)
        number_issues: int = sum(len(result) for result in results)
        issues: IssuesList = results.issues()

        # Group by asset
        groups: list[IssuesList] = issues.group_by(IssueGroupsBy.asset())
        self.assertEqual(len(groups), number_results)
        self.assertEqual(sum(len(group) for group in groups), number_issues)

        # Group by rule
        groups: list[IssuesList] = issues.group_by(IssueGroupsBy.rule())
        rules = list(map(lambda obj: obj.name, groups))
        self.assertTrue(StageMetadataChecker in rules)
        self.assertEqual(sum(len(group) for group in groups), number_issues)

        # Group by message
        groups: list[IssuesList] = issues.group_by(IssueGroupsBy.message())
        messages = list(map(lambda obj: obj.name, groups))
        self.assertTrue(r"Stage has missing or invalid defaultPrim." in messages)
        self.assertEqual(sum(len(group) for group in groups), number_issues)

    async def test_validation_at_anonymous(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/test")
        stage.SetEditTarget(stage.GetSessionLayer())
        stage.DefinePrim("/test2")

        await self.assertRuleAsync(
            asset=stage,
            rule=TypeChecker,
            asserts=[
                IsAFailure(message=ANY, rule=TypeChecker, at=Sdf.Path("/test")),
                IsAFailure(message=ANY, rule=TypeChecker, at=Sdf.Path("/test2")),
            ],
        )

    async def test_validation_parsing_error_progress_complete(self):
        with tempfile.NamedTemporaryFile(suffix=".usda", delete=False) as tmp:
            tmp.write(b"This is not valid USD syntax!")
            tmp_path = tmp.name

        try:
            engine = ValidationEngine(init_rules=False)
            engine.enable_rule(StageMetadataChecker)

            gather_assets = Mock(spec=AssetLocatedCallback)
            assert_progress = Mock(spec=AssetProgressCallback)
            assert_results = Mock(spec=AssetValidatedCallback)
            await engine.validate_with_callbacks(
                tmp_path,
                asset_located_fn=gather_assets,
                asset_progress_fn=assert_progress,
                asset_validated_fn=assert_results,
            )

            gather_assets.assert_called_with(tmp_path)
            assert_progress.assert_called_with(AssetProgress(asset=tmp_path, progress=1.0, results=ANY))
            assert_results.assert_called()
            async_result = assert_results.call_args[0][0]
            issues = async_result.issues()
            self.assertEqual(len(issues), 1)
            self.assertTrue("Failed to Open" in issues[0].message)
        finally:
            os.unlink(tmp_path)

    async def test_validation_init_rules_ok(self):
        expected_rules = [
            ExtentsChecker,
            KindChecker,
            MissingReferenceChecker,
            NormalMapTextureChecker,
            PrimEncapsulationChecker,
            StageMetadataChecker,
            TextureChecker,
            TypeChecker,
            IndexedPrimvarChecker,
            ManifoldChecker,
            NormalsExistChecker,
            NormalsValidChecker,
            NormalsWindingsChecker,
            SubdivisionSchemeChecker,
            UnusedMeshTopologyChecker,
            UnusedPrimvarChecker,
            ValidateTopologyChecker,
            WeldChecker,
            ZeroAreaFaceChecker,
            LayerSpecChecker,
            UsdAsciiPerformanceChecker,
            DanglingOverPrimChecker,
            DefaultPrimChecker,
            MaterialOldMdlSchemaChecker,
            MaterialOutOfScopeChecker,
            MaterialPathChecker,
            MaterialUsdPreviewSurfaceChecker,
            ShaderImplementationSourceChecker,
            UsdDanglingMaterialBinding,
            UsdMaterialBindingApi,
            SkelBindingAPIAppliedChecker,
            UnicodeNameChecker,
            UsdGeomSubsetChecker,
            UsdGeomSubsetFamiliesChecker,
            UsdGeomSubsetParentIsImageableChecker,
            UsdLuxSchemaChecker,
            ArticulationChecker,
            ColliderChecker,
            MassChecker,
            PhysicsJointChecker,
            RigidBodyChecker,
        ]
        if UsdzPackageValidator.is_implemented():
            expected_rules.append(UsdzPackageValidator)
        else:
            expected_rules.append(ByteAlignmentChecker)
            expected_rules.append(CompressionChecker)

        engine = ValidationEngine(init_rules=True)
        self.assertCountEqual(
            engine.initialized_rules,
            expected_rules,
        )

    async def test_stats_accumulate_across_assets(self):
        # Given: an engine validating the same asset twice
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)

        # When
        await engine.validate_async(get_url("curves.usda"))
        total_time_after_first = engine.stats.total_time()
        await engine.validate_async(get_url("curves.usda"))
        total_time_after_second = engine.stats.total_time()

        # Then: rule timing must accumulate — not reset between assets
        self.assertGreater(total_time_after_first, 0)
        self.assertGreater(total_time_after_second, total_time_after_first)


class SyncRuleSyncValidationTest(unittest.TestCase, ValidationTestCaseMixin):
    """
    OMPE-76581: For backwards compatibility, ValidationEngine.validate() should run on the main thread
    and not have a running event loop.
    """

    def test_validate_no_running_loop_prim_ok(self):
        class _TestRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim) -> None:
                with suppress(RuntimeError):
                    get_running_loop()
                    raise AssertionError("Expected no running event loop, but one was found!")

        self.assertSuccess(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
        )

    def test_validate_main_thread_prim_ok(self):
        class _TestRule(BaseRuleChecker):
            def CheckPrim(self, prim: Usd.Prim) -> None:
                if current_thread() != main_thread():
                    raise AssertionError("Expected to be on the main thread, but was not!")

        self.assertSuccess(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
        )

    def test_validate_no_running_loop_stage_ok(self):
        class _TestRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None:
                with suppress(RuntimeError):
                    get_running_loop()
                    raise AssertionError("Expected no running event loop, but one was found!")

        self.assertSuccess(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
        )

    def test_validate_main_thread_stage_ok(self):
        class _TestRule(BaseRuleChecker):
            def CheckStage(self, usd_stage: Usd.Stage) -> None:
                if current_thread() != main_thread():
                    raise AssertionError("Expected to be on the main thread, but was not!")

        self.assertSuccess(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
        )


class AsyncRuleAsyncValidationTest(
    unittest.IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin, ValidationTestCaseMixin
):

    async def test_validate_async_prim_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckPrim(self, prim: Usd.Prim) -> None:
                if prim.GetPath() == "/World":
                    await asyncio.sleep(0)
                    self._AddInfo("Test info", at=prim)

        await self.assertRuleAsync(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info", at=Sdf.Path("/World")),
            ],
        )

    async def test_validate_prim_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckPrim(self, prim: Usd.Prim) -> None:
                if prim.GetPath() == "/World":
                    await asyncio.sleep(0)
                    self._AddInfo("Test info", at=prim)

        self.assertRule(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info", at=Sdf.Path("/World")),
            ],
        )

    async def test_validate_async_stage_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckStage(self, usd_stage: Usd.Stage) -> None:
                await asyncio.sleep(0)
                self._AddInfo("Test info")

        await self.assertRuleAsync(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info"),
            ],
        )

    async def test_validate_stage_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckStage(self, usd_stage: Usd.Stage) -> None:
                await asyncio.sleep(0)
                self._AddInfo("Test info")

        self.assertRule(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info"),
            ],
        )


class AsyncRuleSyncValidationTest(unittest.TestCase, ValidationTestCaseMixin):

    def test_validate_prim_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckPrim(self, prim: Usd.Prim) -> None:
                if prim.GetPath() == "/World":
                    await asyncio.sleep(0)
                    self._AddInfo("Test info", at=prim)

        self.assertRule(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info", at=Sdf.Path("/World")),
            ],
        )

    def test_validate_stage_ok(self):
        class _TestRule(BaseRuleChecker):
            async def CheckStage(self, usd_stage: Usd.Stage) -> None:
                await asyncio.sleep(0)
                self._AddInfo("Test info")

        self.assertRule(
            asset=get_url("helloworld.usda"),
            rule=_TestRule,
            asserts=[
                IsAnInfo(message="Test info"),
            ],
        )


class ValidationContextTest(unittest.TestCase):
    """Tests for the tree-structured validation context (OMPE-88048)."""

    def test_validation_context_empty_without_profiles_or_features(self):
        engine = ValidationEngine(init_rules=False)
        results = ResultsList([Results(asset="test.usd", issues=[])])
        context = engine.build_context(results)
        self.assertIsNone(context)

    def test_validation_context_feature_pass(self):
        mock_req = Mock()
        mock_req.code = "VG.001"
        mock_req.version = "1.0.0"
        mock_feature = Mock()
        mock_feature.id = "FET001"
        mock_feature.version = "1.0.0"
        mock_feature.requirements = [mock_req]

        engine = ValidationEngine(init_rules=False)
        engine.enable_feature(mock_feature)
        results = ResultsList([Results(asset="test.usd", issues=[])])
        context = engine.build_context(results)

        self.assertIsNotNone(context)
        self.assertEqual(len(context.features), 1)
        self.assertEqual(context.features[0].feature.id, "FET001")
        self.assertEqual(context.features[0].status, "PASS")
        self.assertEqual(context.features[0].requirements[0].status, "PASS")

    def test_validation_context_feature_fail(self):
        mock_req = Mock()
        mock_req.code = "RB.001"
        mock_req.version = "1.0.0"
        mock_feature = Mock()
        mock_feature.id = "FET003"
        mock_feature.version = "0.1.0"
        mock_feature.requirements = [mock_req]

        engine = ValidationEngine(init_rules=False)
        engine.enable_feature(mock_feature)
        results = ResultsList(
            [
                Results(
                    asset="test.usd",
                    issues=[Issue(severity=IssueSeverity.FAILURE, message="rigid body fail", requirement=mock_req)],
                )
            ]
        )
        context = engine.build_context(results)

        self.assertEqual(context.features[0].status, "FAIL")
        self.assertEqual(context.features[0].requirements[0].status, "FAIL")

    def test_validation_context_profile_with_mixed_features(self):
        req_pass = Mock()
        req_pass.code = "VG.001"
        req_pass.version = "1.0.0"
        cap_pass = Mock()
        cap_pass.id = "geometry"
        cap_pass.version = "1.0.0"
        cap_pass.requirements = [req_pass]

        req_fail = Mock()
        req_fail.code = "RB.MB.001"
        req_fail.version = "1.0.0"
        cap_fail = Mock()
        cap_fail.id = "physics"
        cap_fail.version = "1.0.0"
        cap_fail.requirements = [req_fail]

        mock_profile = Mock()
        mock_profile.id = "Robot-Body-Isaac"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = [cap_pass, cap_fail]
        mock_profile.features = []

        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        results = ResultsList(
            [
                Results(
                    asset="test.usd",
                    issues=[Issue(severity=IssueSeverity.FAILURE, message="multi body fail", requirement=req_fail)],
                )
            ]
        )
        context = engine.build_context(results)

        self.assertIsNotNone(context)
        self.assertEqual(len(context.profiles), 1)
        profile = context.profiles[0]
        self.assertEqual(profile.profile.id, "Robot-Body-Isaac")
        self.assertEqual(profile.status, "FAIL")
        self.assertEqual(profile.features[0].feature.id, "geometry")
        self.assertEqual(profile.features[0].status, "PASS")
        self.assertEqual(profile.features[1].feature.id, "physics")
        self.assertEqual(profile.features[1].status, "FAIL")

    def test_validation_context_profile_features_do_not_include_capabilities(self):
        feature_req = RequirementDTO(code="FET.001", version="1.0.0")
        feature = FeatureDTO(
            id="feature",
            version="1.0.0",
            path="",
            requirements=[feature_req],
        )
        capability_req = RequirementDTO(code="CAP.001", version="1.0.0")
        capability = CapabilityDTO(
            id="capability",
            version="1.0.0",
            path="",
            requirements=[capability_req],
        )
        profile = ProfileDTO(
            id="Test-Profile",
            version="1.0.0",
            path="",
            features=[feature],
            capabilities=[capability],
        )

        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(profile)
        context = engine.build_context(ResultsList([Results(asset="test.usd", issues=[])]))

        self.assertEqual([status.feature.id for status in context.profiles[0].features], ["feature"])

    def test_log_validation_context_simready_format(self):
        req_pass = Mock()
        req_pass.code = "VG.001"
        req_pass.version = "1.0.0"
        cap_pass = Mock()
        cap_pass.id = "FET001_BASE_NEUTRAL"
        cap_pass.version = "1.0.0"
        cap_pass.requirements = [req_pass]

        req_fail = Mock()
        req_fail.code = "RB.MB.001"
        req_fail.version = "1.0.0"
        cap_fail = Mock()
        cap_fail.id = "FET004_BASE_NEUTRAL"
        cap_fail.version = "0.1.0"
        cap_fail.requirements = [req_fail]

        mock_profile = Mock()
        mock_profile.id = "Prop-Robotics-Neutral"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = [cap_pass, cap_fail]
        mock_profile.features = []

        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        results = ResultsList(
            [
                Results(
                    asset="test.usd",
                    issues=[Issue(severity=IssueSeverity.FAILURE, message="multi body fail", requirement=req_fail)],
                )
            ]
        )

        context = engine.build_context(results)
        with self.assertLogs(level="INFO") as cm:
            ValidationArgsExec._log_validation_context(context)

        log_output = os.linesep.join(cm.output)
        self.assertIn("Failed requirements ['RB.MB.001'] preclude feature FET004_BASE_NEUTRAL", log_output)
        self.assertIn("Profile: Prop-Robotics-Neutral (1.0.0)", log_output)
        self.assertIn("FET001_BASE_NEUTRAL (1.0.0)", log_output)
        self.assertIn("Features:", log_output)
        self.assertNotIn("FET004_BASE_NEUTRAL", log_output.split("Features:")[1])

    def test_validation_context_failed_requirements(self):
        req_a = Mock()
        req_a.code = "VG.001"
        req_a.version = "1.0.0"
        req_b = Mock()
        req_b.code = "RB.001"
        req_b.version = "1.0.0"
        cap = Mock()
        cap.id = "cap"
        cap.version = "1.0.0"
        cap.requirements = [req_a, req_b]
        mock_profile = Mock()
        mock_profile.id = "Test-Profile"
        mock_profile.version = "1.0.0"
        mock_profile.capabilities = [cap]
        mock_profile.features = []

        engine = ValidationEngine(init_rules=False)
        engine.enable_profile(mock_profile)
        results = ResultsList(
            [
                Results(
                    asset="test.usd",
                    issues=[
                        Issue(severity=IssueSeverity.FAILURE, message="a", requirement=req_a),
                        Issue(severity=IssueSeverity.FAILURE, message="b", requirement=req_b),
                    ],
                )
            ]
        )
        context = engine.build_context(results)

        failed = context.failed_requirements
        self.assertIn(req_a, failed)
        self.assertIn(req_b, failed)
        self.assertEqual(len(failed), 2)

    def test_validation_context_single_result(self):
        """build_context accepts a single Results directly via dispatch."""
        mock_req = Mock()
        mock_req.code = "RB.001"
        mock_req.version = "1.0.0"
        mock_feature = Mock()
        mock_feature.id = "FET003"
        mock_feature.version = "0.1.0"
        mock_feature.requirements = [mock_req]

        engine = ValidationEngine(init_rules=False)
        engine.enable_feature(mock_feature)
        result = Results(
            asset="test.usd",
            issues=[Issue(severity=IssueSeverity.FAILURE, message="fail", requirement=mock_req)],
        )
        context = engine.build_context(result)
        self.assertEqual(context.features[0].status, "FAIL")
