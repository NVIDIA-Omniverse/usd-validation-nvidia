# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import pathlib
import unittest
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from common import get_url
from nvidia_usd_validation import (
    AuthoringLayers,
    BaseRuleChecker,
    EditTargetId,
    EditTargetIdList,
    ExtentsChecker,
    FixResult,
    FixStatus,
    Identifier,
    Issue,
    IssueFixer,
    IssuePredicates,
    IssuesList,
    LayerId,
    MaterialPathChecker,
    Results,
    ResultsList,
    StageMetadataChecker,
    Suggestion,
    UsdMaterialBindingApi,
    ValidationEngine,
)
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt


class MyRuleChecker(BaseRuleChecker):
    """
    Check that all active prims are meshes for xforms
    """

    def CheckPrim(self, prim) -> None:
        if prim.GetTypeName() not in ("Mesh", "Xform") and prim.IsActive():
            self._AddFailedCheck(
                message=f"Prim <{prim.GetPath()}> has unsupported type '{prim.GetTypeName()}'.",
                at=prim,
                suggestion=Suggestion(
                    lambda _, _prim: _prim.SetActive(False),
                    "Disable Prim",
                ),
            )


class IssueFixerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        super().setUp()
        self.layer = Mock(spec=Sdf.Layer)
        self.layer.identifier = get_url("helloworld.usda")
        self.stage = Mock(spec=Usd.Stage)
        self.stage.GetRootLayer.return_value = self.layer
        self.edit_target_patch = patch("pxr.Usd.EditTarget")
        self.edit_target = self.edit_target_patch.start()
        self.edit_target.return_value.GetLayer.return_value = self.layer
        self.edit_context_patch = patch("pxr.Usd.EditContext")
        self.edit_context = self.edit_context_patch.start()
        self.issue = Mock(spec=Issue)
        self.issue.at = Mock(spec=Identifier)
        self.issue.default_fix_site = None
        self.issue.fix_sites_for = Mock(return_value=[])
        self.issue.suggestion.at = EditTargetIdList()
        self.issue.suggestions = (self.issue.suggestion,)

    async def asyncTearDown(self) -> None:
        super().tearDown()
        self.edit_target_patch.stop()
        self.edit_context_patch.stop()

    async def test_init_fails(self):
        # Given
        prim = Mock(spec=Usd.Prim)
        # When / Then
        with self.assertRaises(ValueError):
            IssueFixer(prim)

    async def test_apply_success(self):
        # Given / When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.SUCCESS))
        self.edit_target.asset_called_with(self.stage.GetRootLayer())
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_apply_with_explicit_suggestion(self):
        """IssueFixer.apply(issue, suggestion=s2) applies the specified suggestion, not the default"""
        s1 = Mock(spec=Suggestion)
        s1.at = EditTargetIdList()
        s2 = Mock(spec=Suggestion)
        s2.at = EditTargetIdList()
        self.issue.suggestion = s1
        self.issue.suggestions = (s1, s2)

        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue, suggestion=s2)

        self.assertEqual(status, FixResult(self.issue, FixStatus.SUCCESS))
        s1.assert_not_called()
        s2.assert_called_once()

    async def test_apply_default_suggestion_when_none_specified(self):
        """IssueFixer.apply(issue) uses issue.suggestion (first/default)"""
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)

        self.assertEqual(status, FixResult(self.issue, FixStatus.SUCCESS))
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)

    async def test_apply_with_invalid_suggestion_raises(self):
        """IssueFixer.apply(issue, suggestion=unknown) raises ValueError"""
        unknown = Mock(spec=Suggestion)
        unknown.message = "unknown fix"
        unknown.at = EditTargetIdList()
        self.issue.suggestions = (self.issue.suggestion,)

        fixer = IssueFixer(self.stage)
        with self.assertRaises(ValueError):
            fixer.apply(self.issue, suggestion=unknown)

    async def test_apply_with_incompatible_at_and_suggestion_raises(self):
        """apply(issue, at=X, suggestion=s) raises ValueError when at is not a valid site for s"""
        s1 = Mock(spec=Suggestion)
        s1.at = EditTargetIdList()
        s1.message = "fix A"
        self.issue.suggestion = s1
        self.issue.suggestions = (s1,)
        incompatible_at = EditTargetId(layer_id=LayerId(identifier="/wrong.usd"), path=Sdf.Path("/Prim"))
        # fix_sites_for returns a list that does NOT contain incompatible_at
        valid_site = EditTargetId(layer_id=LayerId(identifier="/correct.usd"), path=Sdf.Path("/Prim"))
        self.issue.fix_sites_for = Mock(return_value=[valid_site])

        fixer = IssueFixer(self.stage)
        with self.assertRaises(ValueError):
            fixer.apply(self.issue, at=incompatible_at, suggestion=s1)

    async def test_apply_with_compatible_at_and_suggestion_succeeds(self):
        """apply(issue, at=X, suggestion=s) succeeds when at is in fix_sites_for(s)"""
        s1 = Mock(spec=Suggestion)
        s1.at = EditTargetIdList()
        self.issue.suggestion = s1
        self.issue.suggestions = (s1,)
        # Use None as at — which triggers _to_edit_target(None, stage) → root layer
        self.issue.fix_sites_for = Mock(return_value=[None])

        fixer = IssueFixer(self.stage)
        # at=None is in fix_sites, no validation error
        status = fixer.apply(self.issue, suggestion=s1)
        self.assertEqual(status, FixResult(self.issue, FixStatus.SUCCESS))
        s1.assert_called_once()

    async def test_apply_constrained_suggestion_no_fix_sites(self):
        """apply returns NO_LOCATION when constrained suggestion has no matching fix sites"""
        s1 = Mock(spec=Suggestion)
        s1.at = EditTargetIdList([LayerId(identifier="/constrained.usd")])
        s1.message = "fix in constrained layer"
        self.issue.suggestion = s1
        self.issue.suggestions = (s1,)
        self.issue.fix_sites_for = Mock(return_value=[])

        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue, suggestion=s1)
        self.assertEqual(status, FixResult(self.issue, FixStatus.NO_LOCATION))

    async def test_apply_no_location(self):
        # Given
        self.issue.at = None
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.NO_LOCATION))
        self.edit_target.assert_not_called()
        self.issue.suggestion.assert_not_called()
        self.stage.Save.assert_called_with()

    async def test_apply_no_suggestion(self):
        # Given
        self.issue.suggestion = None
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.NO_SUGGESTION))
        self.edit_target.assert_not_called()
        self.stage.Save.assert_called_with()

    async def test_apply_location_error(self):
        # Given
        exception = ValueError()
        self.issue.at.restore.side_effect = exception
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.INVALID_LOCATION, exception))
        self.edit_target.assert_not_called()
        self.issue.suggestion.assert_not_called()
        self.stage.Save.assert_called_with()

    async def test_apply_at_error(self):
        # Given
        exception = ValueError()
        at: EditTargetId = Mock(spec=EditTargetId)
        at.layer_id = LayerId(identifier=get_url("helloworld.usda"))
        at.path = Sdf.Path("/World")
        at.restore.side_effect = exception
        # Given / When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue, at)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.INVALID_LOCATION, exception))
        self.edit_target.assert_not_called()
        self.issue.suggestion.assert_not_called()
        self.stage.Save.assert_called_with()

    async def test_apply_failure(self):
        # Given
        exception = ValueError()
        self.issue.suggestion.side_effect = exception
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.FAILURE, exception))
        self.edit_target.asset_called_with(self.stage.GetRootLayer())
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_apply_layer_success(self):
        # Given / When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue, self.layer)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.SUCCESS))
        self.edit_target.asset_called_with(self.layer)
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_apply_layer_failure(self):
        # Given
        exception = ValueError()
        self.issue.suggestion.side_effect = exception
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.apply(self.issue, self.layer)
        fixer.save()
        # Then
        self.assertEqual(status, FixResult(self.issue, FixStatus.FAILURE, exception))
        self.edit_target.asset_called_with(self.layer)
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_fix_success(self):
        # Given / When
        fixer = IssueFixer(self.stage)
        status = fixer.fix([self.issue])
        fixer.save()
        # Then
        self.assertSequenceEqual(status, [FixResult(self.issue, FixStatus.SUCCESS)])
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_fix_failure(self):
        # Given
        exception = ValueError()
        self.issue.suggestion.side_effect = exception
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.fix([self.issue])
        fixer.save()
        # Then
        self.assertSequenceEqual(status, [FixResult(self.issue, FixStatus.FAILURE, exception)])
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_called_with()

    async def test_fix_io_error(self):
        # Given
        self.layer.identifier = "notfound.usda"
        # When
        fixer = IssueFixer(self.stage)
        status = fixer.fix([self.issue])
        with self.assertRaises(IOError):
            fixer.save()
        # Then
        self.assertSequenceEqual(status, [FixResult(self.issue, FixStatus.SUCCESS)])
        self.issue.suggestion.assert_called_with(self.stage, self.issue.at.restore.return_value)
        self.stage.Save.assert_not_called()

    async def test_fix_at(self):
        # Given
        stage = Usd.Stage.Open(get_url("helloworld.usda"))
        session_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(session_layer.identifier)
        self.edit_target.return_value.GetLayer.return_value = session_layer
        try:
            # When
            fixer = IssueFixer(stage)
            status = fixer.fix_at([self.issue], session_layer)
            with self.assertRaises(IOError):
                fixer.save()
            # Then
            self.assertSequenceEqual(status, [FixResult(self.issue, FixStatus.SUCCESS)])
            self.issue.suggestion.assert_called_with(stage, self.issue.at.restore.return_value)
            self.stage.Save.assert_not_called()
        finally:
            stage.GetSessionLayer().subLayerPaths.remove(session_layer.identifier)

    async def test_fix_stale_noderef(self):
        class CustomRule1(BaseRuleChecker):
            def CheckPrim(self, prim):
                self._AddFailedCheck(
                    message="Removing prim",
                    at=prim,  # obj
                    suggestion=Suggestion(
                        callable=lambda stage, prim: stage.RemovePrim(prim.GetPath()),
                        message="Remove Prim",
                        at=prim.GetPrimStack(),  # at for _to_edit_target
                    ),
                )

        class CustomRule2(BaseRuleChecker):
            def CheckPrim(self, prim):
                self._AddFailedCheck(
                    message="Editing prim",
                    at=prim,  # obj
                    suggestion=Suggestion(
                        callable=lambda _, prim: prim.SetInstanceable(True),
                        message="Editing Prim",
                        at=prim.GetPrimStack(),  # at for _to_edit_target
                    ),
                )

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Mesh.Define(stage, "/Mesh")

        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(CustomRule1)
        engine.enable_rule(CustomRule2)
        results = await engine.validate_async(stage)
        issues = results.issues()
        self.assertEqual(len(issues), 2)

        # Ensure deterministic order: sort by rule name so CustomRule1 (removal) runs first
        ordered_issues = sorted(issues, key=lambda i: getattr(i.rule, "__name__", ""))

        fixer = IssueFixer(stage)
        fixer.apply(ordered_issues[0])
        fix_result1 = fixer.apply(ordered_issues[1])

        self.assertEqual(fix_result1.status, FixStatus.INVALID_LOCATION)
        self.assertIsInstance(fix_result1.exception, ValueError)


class _ExtentsChecker(BaseRuleChecker):
    def CheckPrim(self, prim: Usd.Prim) -> None:
        boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)
        if not boundable:
            return
        attribute: Usd.Attribute = boundable.GetExtentAttr()
        if not attribute.HasValue():
            self._AddFailedCheck("Prim does not have any extent value", at=prim)


class _LayerPrimSpecChecker(BaseRuleChecker):
    """
    A rule checker that implements CheckLayer and creates a fix suggestion
    targeting an Sdf.PrimSpec.
    """

    def CheckLayer(self, layer: Sdf.Layer) -> None:
        prim_spec = layer.GetPrimAtPath("/World")
        if prim_spec and prim_spec.specifier == Sdf.SpecifierDef:
            self._AddFailedCheck(
                message="Prim specifier should be over",
                at=prim_spec,
                suggestion=Suggestion(
                    callable=lambda _, prim_spec: setattr(prim_spec, "specifier", Sdf.SpecifierOver),
                    message="Change specifier to over",
                    at=prim_spec,
                ),
            )


class AutoFixTest(unittest.IsolatedAsyncioTestCase):
    """
    Showcases of auto fix.
    """

    @contextmanager
    def rollback(self, path) -> pathlib.Path:
        file = pathlib.Path(path)
        old_content = file.read_text()
        try:
            yield file
        finally:
            file.write_text(old_content)

    async def test_commit_fix_url(self):
        url: str = get_url("autofixPrev.usda")
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(MyRuleChecker)

        result = engine.validate(url)
        issues = result.issues(IssuePredicates.And(IssuePredicates.IsFailure(), IssuePredicates.IsRule(MyRuleChecker)))

        with self.rollback(url) as path:
            fixer = IssueFixer(url)
            fixer.fix(issues)
            fixer.save()
            self.assertEqual(path.read_text(), pathlib.Path(get_url("autofixNext.usda")).read_text())

    async def test_anonymous_layers_batch_mode(self) -> None:
        """
        OM-94661: On Batch Mode, there should not be contribution from anonymous layers, i.e. ComplianceChecker
        session layer.
        """
        # Given
        test_case: str = get_url()
        # When
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(StageMetadataChecker)
        results: ResultsList = await engine.validate_async(test_case)
        issues: IssuesList = results.issues()
        # Then
        for issue in issues.filter_by(IssuePredicates.HasLocation()):
            for target_id in issue.at.get_spec_ids():
                path: pathlib.Path = pathlib.Path(target_id.layer_id.identifier)
                self.assertTrue(path.exists())

    async def test_anonymous_layers_stage_mode(self) -> None:
        """
        OM-103404: On Stage Mode, we should be able to get correct layer location and be able to fix it.
        """
        # Given
        stage: Usd.Stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        session_layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(session_layer.identifier)
        mesh = UsdGeom.Mesh.Define(stage, "/World/Test")
        mesh.GetFaceVertexCountsAttr().Set([4, 4, 4, 4, 4, 4])
        mesh.GetFaceVertexIndicesAttr().Set([0, 1, 3, 2, 0, 4, 5, 1, 1, 5, 6, 3, 2, 3, 6, 7, 0, 2, 7, 4, 4, 7, 6, 5])
        mesh.GetPointsAttr().Set(
            [
                (-50, -50, -50),
                (50, -50, -50),
                (-50, -50, 50),
                (50, -50, 50),
                (-50, 50, -50),
                (50, 50, -50),
                (50, 50, 50),
                (-50, 50, 50),
            ]
        )
        self.assertFalse(mesh.GetExtentAttr().HasValue())
        # When
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(_ExtentsChecker)
        results: Results = engine.validate(stage)
        issues: IssuesList = results.issues()
        for issue in issues:
            self.assertIsNotNone(issue.default_fix_site)

    async def test_fix_layer_prim_spec_ok(self) -> None:
        """
        OMPE-61445: Fixing an issue from CheckLayer with at=Sdf.PrimSpec works.
        """
        # Given
        stage: Usd.Stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")

        # When
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(_LayerPrimSpecChecker)
        results: Results = engine.validate(stage)
        issues: IssuesList = results.issues()
        fixer = IssueFixer(stage)
        fix_results = fixer.fix(issues)

        # Then
        self.assertEqual(len(issues), 1)
        self.assertEqual(fix_results[0].status, FixStatus.SUCCESS)


class UtilsTest(unittest.IsolatedAsyncioTestCase):
    def test_authoring_layer(self):
        stage: Usd.Stage = Usd.Stage.Open(get_url("materialLayerKnownReference.usda"))
        prim: Usd.Prim = stage.GetPrimAtPath("/World/Looks/MatX/Shader")
        prop: Usd.Property = prim.GetProperty("info:mdl:sourceAsset")

        result: list[Sdf.Layer] = AuthoringLayers(prop)

        self.assertTrue(result)
        self.assertTrue(result[0].identifier.endswith("knownMaterial.usda"))


class VariantTest(unittest.IsolatedAsyncioTestCase):

    async def test_variants(self):
        variants: pathlib.Path = pathlib.Path(get_url("materialVariantsFail.usda"))
        correct: pathlib.Path = pathlib.Path(get_url("Materials/knownMaterial.usda"))
        incorrect: pathlib.Path = pathlib.Path(get_url("Materials/incorrectMaterialSublayer.usda"))
        missing_dot: pathlib.Path = pathlib.Path(get_url("Materials/missingDotMaterial.usda"))
        material_mdl: pathlib.Path = pathlib.Path(get_url("Materials/material.mdl"))
        # Copy assets to edit
        with TemporaryDirectory() as directory:
            temp_variant = pathlib.Path(directory).joinpath("materialVariantsFail.usda")
            temp_variant.write_text(variants.read_text())
            pathlib.Path(directory).joinpath("Materials/").mkdir()
            pathlib.Path(directory).joinpath("Materials/material.mdl").write_text(material_mdl.read_text())
            temp_correct = pathlib.Path(directory).joinpath("Materials/knownMaterial.usda")
            temp_correct.write_text(correct.read_text())
            temp_incorrect = pathlib.Path(directory).joinpath("Materials/incorrectMaterialSublayer.usda")
            temp_incorrect.write_text(incorrect.read_text())
            temp_missing_dot = pathlib.Path(directory).joinpath("Materials/missingDotMaterial.usda")
            temp_missing_dot.write_text(missing_dot.read_text())

            engine: ValidationEngine = ValidationEngine(init_rules=False)
            engine.enable_rule(MaterialPathChecker)
            result = engine.validate(str(temp_variant))
            issues = result.issues()

            fixer: IssueFixer = IssueFixer(str(temp_variant))
            fixer.fix(issues)
            fixer.save()
            # USDA should not be modified
            self.assertEqual(variants.read_text(), temp_variant.read_text())
            # Correct Layer should not be modified
            self.assertEqual(correct.read_text(), temp_correct.read_text())
            # Incorrect layers should be modified
            self.assertIn("uniform asset info:mdl:sourceAsset = @./material.mdl@", temp_incorrect.read_text())
            self.assertIn("uniform asset info:mdl:sourceAsset = @./material.mdl@", temp_missing_dot.read_text())

    async def test_nested_variants(self):
        variant_reference: pathlib.Path = pathlib.Path(get_url("nestedVariantsReference.usda"))
        variants: pathlib.Path = pathlib.Path(get_url("nestedVariants.usda"))
        # Copy assets to edit
        with TemporaryDirectory() as directory:
            temp_variant_reference = pathlib.Path(directory).joinpath("nestedVariantsReference.usda")
            temp_variant_reference.write_text(variant_reference.read_text())

            temp_variants = pathlib.Path(directory).joinpath("nestedVariants.usda")
            temp_variants.write_text(variants.read_text())

            engine: ValidationEngine = ValidationEngine(init_rules=False)
            engine.enable_rule(ExtentsChecker)
            result = engine.validate(str(temp_variant_reference))
            issues = result.issues()

            fixer: IssueFixer = IssueFixer(str(temp_variant_reference))
            fixer.fix(issues)
            fixer.save()
            # USDA should not be modified
            self.assertEqual(variant_reference.read_text(), temp_variant_reference.read_text())

            # Incorrect layers should be modified
            stage: Usd.Stage = Usd.Stage.Open(str(temp_variants))
            extend = stage.GetObjectAtPath("/World/quad.extent").Get(0)
            self.assertEqual(extend, Vt.Vec3fArray(2, (Gf.Vec3f(-500.0, 0.0, -500.0), Gf.Vec3f(500.0, 0.0, 500.0))))
            extend = stage.GetObjectAtPath("/World/box.extent").Get(0)
            self.assertEqual(extend, Vt.Vec3fArray(2, (Gf.Vec3f(-50.0, -50.0, -50.0), Gf.Vec3f(50.0, 50.0, 50.0))))

    async def test_fix_at_anonymous(self):
        cache = Usd.StageCache()
        with Usd.StageCacheContext(cache):
            # Create in-memory stage with two prims
            stage = Usd.Stage.CreateInMemory()

            # Create first prim in root layer
            prim1 = stage.DefinePrim("/test1")
            prim1.CreateRelationship("material:binding")

            # Create second prim in session layer
            stage.SetEditTarget(stage.GetSessionLayer())
            prim2 = stage.DefinePrim("/test2")
            prim2.CreateRelationship("material:binding")

            # Run validation
            engine = ValidationEngine(init_rules=False)
            engine.enable_rule(UsdMaterialBindingApi)
            result = engine.validate(stage)
            issues = result.issues()

            # Should have 2 issues - one for each prim missing the API
            self.assertEqual(len(issues), 2)

            # Fix the issues
            fixer = IssueFixer(stage)
            fix_results = fixer.fix(issues)

            # Verify fixes were successful
            self.assertEqual(fix_results[0].status, FixStatus.SUCCESS)
            self.assertEqual(fix_results[1].status, FixStatus.SUCCESS)
            self.assertTrue(prim1.HasAPI(UsdShade.MaterialBindingAPI))
            self.assertTrue(prim2.HasAPI(UsdShade.MaterialBindingAPI))
