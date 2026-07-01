# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import pathlib
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from common import get_url
from pxr import Ar, Sdf, Usd, UsdGeom

from usd_validation_nvidia import ComplianceChecker


class ComplianceCheckerTest(unittest.IsolatedAsyncioTestCase):
    def test_check_dependencies_makes_relative_asset_path_absolute(self):
        root = pathlib.Path.cwd()
        with TemporaryDirectory(dir=root) as directory:
            asset = pathlib.Path(directory).joinpath("asset.usda")
            root_layer = Sdf.Layer.CreateAnonymous("asset.usda")
            root_prim = Sdf.CreatePrimInLayer(root_layer, "/World")
            root_prim.specifier = Sdf.SpecifierDef
            root_prim.typeName = "Xform"
            root_layer.defaultPrim = "World"
            root_layer.Export(str(asset))

            relative_asset = str(asset.relative_to(root))

            with patch(
                "usd_validation_nvidia._compliance_checker.UsdUtils.ComputeAllDependencies",
                return_value=([], [], []),
            ) as compute_dependencies:
                ComplianceChecker._check_dependencies(relative_asset, Ar.GetResolver().GetCurrentContext())

            compute_dependencies.assert_called_once_with(Sdf.AssetPath(os.path.abspath(relative_asset)))

    def test_create_stage_edit_root_layer_in_memory(self):
        # Given
        stage: Usd.Stage = Usd.Stage.CreateInMemory()
        with Usd.EditContext(stage, Usd.EditTarget(stage.GetRootLayer())):
            UsdGeom.Xform.Define(stage, "/World")
            mesh = UsdGeom.Mesh.Define(stage, "/World/Test")
            mesh.GetFaceVertexCountsAttr().Set([4, 4, 4, 4, 4, 4])
            mesh.GetFaceVertexIndicesAttr().Set(
                [0, 1, 3, 2, 0, 4, 5, 1, 1, 5, 6, 3, 2, 3, 6, 7, 0, 2, 7, 4, 4, 7, 6, 5]
            )
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
            mesh.GetExtentAttr().Set([(-50, -50, -50), (50, 50, 50)])

        # When
        stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
        prim_copy = stage_copy.GetPrimAtPath("/World/Test")
        mesh_copy = UsdGeom.Mesh(prim_copy)

        # Then
        self.assertTrue(stage_copy.GetRootLayer().dirty)
        self.assertEqual(mesh.GetExtentAttr().Get(), mesh_copy.GetExtentAttr().Get())

    def test_create_stage_edit_root_layer_in_disk(self):
        # Given
        stage: Usd.Stage = Usd.Stage.Open(get_url("helloworld.usda"))
        with Usd.EditContext(stage, Usd.EditTarget(stage.GetRootLayer())):
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/box_0"))
            mesh.GetExtentAttr().Set([(0, 2, 3), (5, 7, 11)])

        try:
            # When
            stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
            prim_copy = stage_copy.GetPrimAtPath("/World/box_0")
            mesh_copy = UsdGeom.Mesh(prim_copy)

            # Then
            self.assertTrue(stage_copy.GetRootLayer().dirty)
            self.assertEqual(mesh_copy.GetExtentAttr().Get(), [(0, 2, 3), (5, 7, 11)])
        finally:
            stage.Reload()

    def test_create_stage_edit_session_layer_in_memory(self):
        # Given
        session: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage: Usd.Stage = Usd.Stage.CreateInMemory("StageWithSession", session)
        with Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(session)):
            UsdGeom.Xform.Define(stage, "/World")
            mesh = UsdGeom.Mesh.Define(stage, "/World/Test")
            mesh.GetFaceVertexCountsAttr().Set([4, 4, 4, 4, 4, 4])
            mesh.GetFaceVertexIndicesAttr().Set(
                [0, 1, 3, 2, 0, 4, 5, 1, 1, 5, 6, 3, 2, 3, 6, 7, 0, 2, 7, 4, 4, 7, 6, 5]
            )
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
            mesh.GetExtentAttr().Set([(-50, -50, -50), (50, 50, 50)])

        # When
        stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
        prim_copy = stage_copy.GetPrimAtPath("/World/Test")
        mesh_copy = UsdGeom.Mesh(prim_copy)

        # Then
        self.assertTrue(stage_copy.GetSessionLayer().dirty)
        self.assertEqual(mesh.GetExtentAttr().Get(), mesh_copy.GetExtentAttr().Get())

    def test_create_stage_edit_session_layer_in_disk(self):
        # Given
        session: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage: Usd.Stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(get_url("helloworld.usda")), session)
        with Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(session)):
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/box_0"))
            mesh.GetExtentAttr().Set([(0, 2, 3), (5, 7, 11)])

        try:
            # When
            stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
            prim_copy = stage_copy.GetPrimAtPath("/World/box_0")
            mesh_copy = UsdGeom.Mesh(prim_copy)

            # Then
            self.assertTrue(stage_copy.GetSessionLayer().dirty)
            self.assertEqual(mesh_copy.GetExtentAttr().Get(), [(0, 2, 3), (5, 7, 11)])
        finally:
            stage.Reload()

    def test_create_stage_edit_session_sublayer_in_memory(self):
        # Given
        stage: Usd.Stage = Usd.Stage.CreateInMemory()
        edit: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(edit.identifier)
        with Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(edit)):
            UsdGeom.Xform.Define(stage, "/World")
            mesh = UsdGeom.Mesh.Define(stage, "/World/Test")
            mesh.GetFaceVertexCountsAttr().Set([4, 4, 4, 4, 4, 4])
            mesh.GetFaceVertexIndicesAttr().Set(
                [0, 1, 3, 2, 0, 4, 5, 1, 1, 5, 6, 3, 2, 3, 6, 7, 0, 2, 7, 4, 4, 7, 6, 5]
            )
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
            mesh.GetExtentAttr().Set([(-50, -50, -50), (50, 50, 50)])

        # When
        stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
        prim_copy = stage_copy.GetPrimAtPath("/World/Test")
        mesh_copy = UsdGeom.Mesh(prim_copy)

        # Then
        self.assertTrue(stage_copy.GetSessionLayer().dirty)
        self.assertEqual(mesh.GetExtentAttr().Get(), mesh_copy.GetExtentAttr().Get())

    def test_create_stage_edit_session_sublayer_in_disk(self):
        # Given
        stage: Usd.Stage = Usd.Stage.Open(get_url("helloworld.usda"))
        edit: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        stage.GetSessionLayer().subLayerPaths.append(edit.identifier)
        with Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(edit)):
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/World/box_0"))
            mesh.GetExtentAttr().Set([(0, 2, 3), (5, 7, 11)])

        try:
            # When
            stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
            prim_copy = stage_copy.GetPrimAtPath("/World/box_0")
            mesh_copy = UsdGeom.Mesh(prim_copy)

            # Then
            self.assertTrue(stage_copy.GetSessionLayer().dirty)
            self.assertEqual(mesh_copy.GetExtentAttr().Get(), [(0, 2, 3), (5, 7, 11)])
        finally:
            stage.Reload()

    def test_create_stage_edit_spec(self):
        # Given
        stage: Usd.Stage = Usd.Stage.Open(get_url("complianceCheckerRoot.usda"))
        prim: Usd.Prim = stage.GetPrimAtPath("/World/Box/box_0")
        edit_target: Usd.EditTarget | None = None
        for spec in prim.GetPrimStack():
            layer: Sdf.Layer = spec.layer
            node_ref = prim.GetPrimIndex().GetNodeProvidingSpec(spec)
            edit_target = Usd.EditTarget(layer, node_ref)
        with Usd.EditContext(stage, edit_target):
            mesh = UsdGeom.Mesh(prim)
            mesh.GetExtentAttr().Set([(0, 2, 3), (5, 7, 11)])

        try:
            # When
            stage_copy: Usd.Stage = ComplianceChecker._create_stage(stage)
            prim_copy = stage_copy.GetPrimAtPath("/World/Box/box_0")
            layer_copy: Sdf.Layer | None = None
            for spec_copy in prim_copy.GetPrimStack():
                layer_copy = spec_copy.layer
            mesh_copy = UsdGeom.Mesh(prim_copy)

            # Then
            self.assertTrue(layer_copy.dirty)
            self.assertEqual(mesh_copy.GetExtentAttr().Get(), [(0, 2, 3), (5, 7, 11)])
        finally:
            stage.Reload()
