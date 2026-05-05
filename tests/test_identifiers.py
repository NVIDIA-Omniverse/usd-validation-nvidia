# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from dataclasses import replace
from unittest.mock import ANY

from common import get_url
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from nvidia_usd_validation import (
    AttributeId,
    EditTargetId,
    EditTargetIdList,
    FormatDependency,
    FormatDependencyId,
    LayerId,
    LocalUriResolver,
    PrimId,
    PrimvarId,
    SchemaBaseId,
    StageId,
    normalize_url,
    to_identifier,
)


class LayerIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.layer = Sdf.Layer.FindOrOpen(self.url)

    async def test_from_ok(self):
        # When
        layer_id = LayerId.from_(self.layer)

        # Then
        self.assertIsInstance(layer_id, LayerId)
        self.assertEqual(layer_id.identifier, normalize_url(self.url))

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.layer), LayerId.from_(self.layer))

    async def test_restore_ok(self):
        # Given
        layer_id = LayerId.from_(self.layer)

        # When
        restored = layer_id.restore(None)

        # Then
        self.assertEqual(self.layer, restored)


class StageIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(self.url)

    async def test_from_ok(self):
        # When
        stage_id = StageId.from_(self.stage)

        # Then
        self.assertIsInstance(stage_id, StageId)
        self.assertEqual(stage_id.root_layer, LayerId(self.url))

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.stage), StageId.from_(self.stage))

    async def test_restore_ok(self):
        # Given
        stage_id = StageId.from_(self.stage)

        # When
        restored = stage_id.restore(self.stage)

        # Then
        self.assertEqual(self.stage, restored)


class EditTargetIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.layer = Sdf.Layer.FindOrOpen(self.url)
        self.prim_spec = self.layer.GetPrimAtPath("/World/cube")
        self.property_spec = self.layer.GetPropertyAtPath("/World/cube.size")

    async def test_from_layer_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.layer)

        # Then
        self.assertIsInstance(edit_target_id, EditTargetId)
        self.assertEqual(edit_target_id.layer_id, LayerId(self.url))
        self.assertIsNone(edit_target_id.path)

    async def test_from_prim_spec_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.prim_spec)

        # Then
        self.assertIsInstance(edit_target_id, EditTargetId)
        self.assertEqual(edit_target_id.layer_id, LayerId(self.url))
        self.assertEqual(edit_target_id.path, Sdf.Path("/World/cube"))

    async def test_from_property_spec_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.property_spec)

        # Then
        self.assertIsInstance(edit_target_id, EditTargetId)
        self.assertEqual(edit_target_id.layer_id, LayerId(self.url))
        self.assertEqual(edit_target_id.path, Sdf.Path("/World/cube.size"))

    async def test_restore_layer_ok(self):
        # Given
        edit_target_id = EditTargetId.from_(self.layer)

        # When
        restored = edit_target_id.restore(None)

        # Then
        self.assertEqual(self.layer, restored)

    async def test_restore_prim_spec_ok(self):
        # Given
        edit_target_id = EditTargetId.from_(self.prim_spec)

        # When
        restored = edit_target_id.restore(None)

        # Then
        self.assertEqual(self.prim_spec, restored)

    async def test_restore_property_spec_ok(self):
        # Given
        edit_target_id = EditTargetId.from_(self.property_spec)

        # When
        restored = edit_target_id.restore(None)

        # Then
        self.assertEqual(self.property_spec, restored)


class EditTargetIdListTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.layer = Sdf.Layer.FindOrOpen(self.url)
        self.prim_spec = self.layer.GetPrimAtPath("/World/cube")
        self.property_spec = self.layer.GetPropertyAtPath("/World/cube.size")
        self.stage = Usd.Stage.Open(self.url)
        self.prim = self.stage.GetPrimAtPath("/World/cube")
        self.property = self.prim.GetAttribute("size")

    async def test_from_layer_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.layer)
        edit_target_id_list = EditTargetIdList.from_(self.layer)

        # Then
        self.assertEqual(len(edit_target_id_list), 1)
        self.assertEqual(edit_target_id_list[0], edit_target_id)

    async def test_from_prim_spec_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.prim_spec)
        edit_target_id_list = EditTargetIdList.from_(self.prim_spec)

        # Then
        self.assertEqual(len(edit_target_id_list), 1)
        self.assertEqual(edit_target_id_list[0], edit_target_id)

    async def test_from_property_spec_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.property_spec)
        edit_target_id_list = EditTargetIdList.from_(self.property_spec)

        # Then
        self.assertEqual(len(edit_target_id_list), 1)
        self.assertEqual(edit_target_id_list[0], edit_target_id)

    async def test_from_prim_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.prim_spec)
        edit_target_id_list = EditTargetIdList.from_(self.prim)

        # Then
        self.assertGreaterEqual(len(edit_target_id_list), 1)
        self.assertEqual(edit_target_id_list[0], replace(edit_target_id, composed=ANY))
        self.assertIsNotNone(edit_target_id_list[0].composed)

    async def test_from_property_ok(self):
        # When
        edit_target_id = EditTargetId.from_(self.property_spec)
        edit_target_id_list = EditTargetIdList.from_(self.property)

        # Then
        self.assertGreaterEqual(len(edit_target_id_list), 1)
        self.assertEqual(edit_target_id_list[0], replace(edit_target_id, composed=ANY))
        self.assertIsNotNone(edit_target_id_list[0].composed)


class PrimIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(self.url)
        self.prim = self.stage.GetPrimAtPath("/World/cube")

    async def test_from_ok(self):
        # When
        prim_id = PrimId.from_(self.prim)

        # Then
        self.assertIsInstance(prim_id, PrimId)
        self.assertEqual(prim_id.stage_id, StageId(root_layer=LayerId(self.url)))
        self.assertEqual(prim_id.path, Sdf.Path("/World/cube"))

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.prim), PrimId.from_(self.prim))

    async def test_restore_ok(self):
        # Given
        prim_id = PrimId.from_(self.prim)

        # When
        restored = prim_id.restore(self.stage)

        # Then
        self.assertEqual(self.prim, restored)

    async def test_variant_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        prim = stage.GetPrimAtPath("/Root/World/cube")

        # When
        prim_id = PrimId.from_(prim)

        # Then
        self.assertEqual(prim_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/cube"))

    async def test_nested_variant_ok(self):
        # Given
        url = get_url("nestedVariantsReference.usda")
        stage = Usd.Stage.Open(url)
        stage.GetPrimAtPath("/Root").GetVariantSet("RootVariant").SetVariantSelection("variant1")
        prim = stage.GetPrimAtPath("/Root/World/box")

        # When
        prim_id = PrimId.from_(prim)

        # Then
        self.assertEqual(
            prim_id.variant_selection_path,
            Sdf.Path("/Root{RootVariant=variant1}World{QuadVariant=incorrect}{BoxVariant=incorrect}box"),
        )

        # Change variant selection
        world_prim = stage.GetPrimAtPath("/Root/World")
        world_prim.GetVariantSet("QuadVariant").SetVariantSelection("correct")

        # When
        prim_id = PrimId.from_(prim)

        # Then
        self.assertEqual(
            prim_id.variant_selection_path,
            Sdf.Path("/Root{RootVariant=variant1}World{QuadVariant=correct}{BoxVariant=incorrect}box"),
        )


class AttributeIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(self.url)
        self.prim = self.stage.GetPrimAtPath("/World/cube")
        self.attr = self.prim.GetAttribute("size")

    async def test_from_ok(self):
        # When
        attr_id = AttributeId.from_(self.attr)

        # Then
        self.assertIsInstance(attr_id, AttributeId)
        self.assertEqual(attr_id.prim_id.path, Sdf.Path("/World/cube"))
        self.assertEqual(attr_id.path, Sdf.Path("/World/cube.size"))
        self.assertEqual(attr_id.name, "size")

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.attr), AttributeId.from_(self.attr))

    async def test_restore_ok(self):
        # Given
        attr_id = AttributeId.from_(self.attr)

        # When
        restored = attr_id.restore(self.stage)

        # Then
        self.assertEqual(self.attr, restored)

    async def test_variant_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        prim = stage.GetPrimAtPath("/Root/World/cube")
        attr = prim.GetAttribute("size")

        # When
        attr_id = AttributeId.from_(attr)

        # Then
        self.assertEqual(attr, attr_id.restore(stage))
        self.assertEqual(attr_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/cube.size"))

    async def test_nested_variant_restore_ok(self):
        # Given
        url = get_url("nestedVariantsReference.usda")
        stage = Usd.Stage.Open(url)
        stage.GetPrimAtPath("/Root").GetVariantSet("RootVariant").SetVariantSelection("correct")
        property_ = stage.GetObjectAtPath("/Root/World/box.purpose")

        # When
        prop_id = AttributeId.from_(property_)

        # Then
        self.assertEqual(
            prop_id.variant_selection_path,
            Sdf.Path("/Root{RootVariant=correct}World/box.purpose"),
        )

        # Change variant selection
        stage.GetPrimAtPath("/Root").GetVariantSet("RootVariant").SetVariantSelection("empty")
        # Invalid object
        self.assertFalse(stage.GetObjectAtPath("/Root/World/box.purpose").IsValid())

        # When
        prop_id.restore_variant_selection(stage)

        # Then
        self.assertTrue(stage.GetObjectAtPath("/Root/World/box.purpose").IsValid())


class PrimvarIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(self.url)
        self.prim = self.stage.GetPrimAtPath("/World/box_0")
        self.api = UsdGeom.PrimvarsAPI(self.prim)
        self.primvar = self.api.GetPrimvar("displayColor")

    async def test_from_ok(self):
        # When
        primvar_id = PrimvarId.from_(self.primvar)

        # Then
        self.assertIsInstance(primvar_id, PrimvarId)
        self.assertEqual(primvar_id.prim_id.path, Sdf.Path("/World/box_0"))
        self.assertEqual(primvar_id.path, Sdf.Path("/World/box_0.primvars:displayColor"))
        self.assertEqual(primvar_id.name, "primvars:displayColor")

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.primvar), PrimvarId.from_(self.primvar))

    async def test_restore_ok(self):
        # Given
        primvar_id = PrimvarId.from_(self.primvar)

        # When
        restored = primvar_id.restore(self.stage)

        # Then
        self.assertEqual(self.primvar, restored)

    async def test_variant_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        prim = stage.GetPrimAtPath("/Root/World/box_0")
        api = UsdGeom.PrimvarsAPI(prim)
        primvar = api.GetPrimvar("displayColor")

        # When
        primvar_id = PrimvarId.from_(primvar)

        # Then
        self.assertEqual(primvar, primvar_id.restore(stage))
        self.assertEqual(
            primvar_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/box_0.primvars:displayColor")
        )


class SchemaBaseIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(self.url)
        self.mesh = UsdGeom.Mesh.Get(self.stage, "/World/quad")
        self.collision_api = UsdPhysics.CollisionAPI.Get(self.stage, "/World/quad")

    async def test_from_typed_ok(self):
        # When
        schema_base_id = SchemaBaseId.from_(self.mesh)

        # Then
        self.assertIsInstance(schema_base_id, SchemaBaseId)
        self.assertEqual(schema_base_id.prim_id.path, Sdf.Path("/World/quad"))
        self.assertEqual(schema_base_id.schema_class, UsdGeom.Mesh)
        self.assertEqual(schema_base_id.instance_name, "")

    async def test_from_applied_ok(self):
        # When
        schema_base_id = SchemaBaseId.from_(self.collision_api)

        # Then
        self.assertIsInstance(schema_base_id, SchemaBaseId)
        self.assertEqual(schema_base_id.prim_id.path, Sdf.Path("/World/quad"))
        self.assertEqual(schema_base_id.schema_class, UsdPhysics.CollisionAPI)
        self.assertEqual(schema_base_id.instance_name, "")

    async def test_from_multiple_applied_ok(self):
        # Given
        collection_api = Usd.CollectionAPI.Apply(self.mesh.GetPrim(), "instance")

        # When
        schema_base_id = SchemaBaseId.from_(collection_api)

        # Then
        self.assertIsInstance(schema_base_id, SchemaBaseId)
        self.assertEqual(schema_base_id.prim_id.path, Sdf.Path("/World/quad"))
        self.assertEqual(schema_base_id.schema_class, Usd.CollectionAPI)
        self.assertEqual(schema_base_id.instance_name, "instance")

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.mesh), SchemaBaseId.from_(self.mesh))

    async def test_restore_typed_ok(self):
        # Given
        schema_base_id = SchemaBaseId.from_(self.mesh)

        # When
        restored = schema_base_id.restore(self.stage)

        # Then
        self.assertIsInstance(restored, UsdGeom.Mesh)
        self.assertEqual(self.mesh.GetPrim(), restored.GetPrim())

    async def test_restore_applied_ok(self):
        # Given
        schema_base_id = SchemaBaseId.from_(self.collision_api)

        # When
        restored = schema_base_id.restore(self.stage)

        # Then
        self.assertIsInstance(restored, UsdPhysics.CollisionAPI)
        self.assertEqual(self.collision_api.GetPrim(), restored.GetPrim())

    async def test_restore_multiple_applied_ok(self):
        # Given
        collection_api = Usd.CollectionAPI.Apply(self.mesh.GetPrim(), "instance")
        schema_base_id = SchemaBaseId.from_(collection_api)

        # When
        restored = schema_base_id.restore(self.stage)

        # Then
        self.assertIsInstance(restored, Usd.CollectionAPI)
        self.assertEqual(collection_api.GetPrim(), restored.GetPrim())
        self.assertTrue(restored.IsMultipleApplyAPISchema())
        self.assertEqual(restored.GetName(), "instance")

    async def test_variant_typed_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        mesh = UsdGeom.Mesh.Get(stage, "/Root/World/quad")

        # When
        schema_base_id = SchemaBaseId.from_(mesh)

        # Then
        restored = schema_base_id.restore(stage)
        self.assertIsInstance(restored, UsdGeom.Mesh)
        self.assertEqual(mesh.GetPrim(), restored.GetPrim())
        self.assertEqual(schema_base_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/quad"))

    async def test_variant_applied_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        collision_api = UsdPhysics.CollisionAPI.Get(stage, "/Root/World/quad")

        # When
        schema_base_id = SchemaBaseId.from_(collision_api)

        # Then
        restored = schema_base_id.restore(stage)
        self.assertIsInstance(restored, UsdPhysics.CollisionAPI)
        self.assertEqual(collision_api.GetPrim(), restored.GetPrim())
        self.assertEqual(schema_base_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/quad"))

    async def test_variant_multiple_applied_ok(self):
        # Given
        url = get_url("helloworldVariants.usda")
        stage = Usd.Stage.Open(url)
        mesh = UsdGeom.Mesh.Get(stage, "/Root/World/quad")
        collection_api = Usd.CollectionAPI.Apply(mesh.GetPrim(), "instance")

        # When
        schema_base_id = SchemaBaseId.from_(collection_api)

        # Then
        restored = schema_base_id.restore(stage)
        self.assertIsInstance(restored, Usd.CollectionAPI)
        self.assertEqual(collection_api.GetPrim(), restored.GetPrim())
        self.assertTrue(restored.IsMultipleApplyAPISchema())
        self.assertEqual(restored.GetName(), "instance")
        self.assertEqual(schema_base_id.variant_selection_path, Sdf.Path("/Root{Main=variant1}World/quad"))


class FormatDependencyIdTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dependency = FormatDependency(
            path="/a/dep.stubfmt",
            uri_resolver=LocalUriResolver(),
            root_asset_path="/a/root.stubfmt",
        )

    async def test_from_ok(self):
        # When
        dep_id = FormatDependencyId.from_(self.dependency)

        # Then
        self.assertIsInstance(dep_id, FormatDependencyId)
        self.assertEqual(dep_id.path, "/a/dep.stubfmt")
        self.assertEqual(dep_id.root_asset_path, "/a/root.stubfmt")

    async def test_to_identifier_ok(self):
        # When/Then
        self.assertEqual(to_identifier(self.dependency), FormatDependencyId.from_(self.dependency))

    async def test_get_spec_ids_returns_empty(self):
        dep_id = FormatDependencyId.from_(self.dependency)
        self.assertEqual(dep_id.get_spec_ids(), [])


class ToIdentifierListDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        url = get_url("helloworld.usda")
        self.stage = Usd.Stage.Open(url)
        self.prim1 = self.stage.GetPrimAtPath("/World")
        self.prim2 = self.stage.GetPrimAtPath("/World/cube")

    async def test_list_normalized_to_tuple_of_identifiers(self):
        # When
        result = to_identifier([self.prim1, self.prim2])
        # Then
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], PrimId)
        self.assertIsInstance(result[1], PrimId)

    async def test_empty_list_normalized_to_empty_tuple(self):
        # When
        result = to_identifier([])
        # Then
        self.assertEqual(result, ())

    async def test_tuple_input_normalized_to_tuple_of_identifiers(self):
        # When
        result = to_identifier((self.prim1, self.prim2))
        # Then
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], PrimId)
        self.assertIsInstance(result[1], PrimId)
