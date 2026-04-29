# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from functools import singledispatch, singledispatchmethod
from typing import Any, Generic, TypeVar

from pxr import Sdf, Usd, UsdGeom

from ._asset_format import FormatDependency
from ._deprecate import deprecated
from ._url_utils import normalize_url

__all__ = [
    "ANON_VALIDATOR_LAYER_NAME",
    "AtType",
    "AttributeId",
    "EditTargetId",
    "EditTargetIdList",
    "FormatDependencyId",
    "Identifier",
    "LayerId",
    "PrimId",
    "PrimvarId",
    "PropertyId",
    "SchemaBaseId",
    "SpecId",
    "SpecIdList",
    "StageId",
    "VariantIdMixin",
    "to_identifier",
    "to_identifiers",
]

AtType = TypeVar(
    "AtType",
    Sdf.Layer,
    Usd.Stage,
    Usd.Prim,
    Usd.Property,
    Usd.Attribute,
    Usd.Relationship,
    Usd.SchemaBase,
    UsdGeom.Primvar,
    Sdf.PrimSpec,
    Sdf.PropertySpec,
    FormatDependency,
)
"""
Location of an issue or a fix.

Can be any of:
  - :py:class:`pxr.Sdf.Layer`
  - :py:class:`pxr.Usd.Stage`
  - :py:class:`pxr.Usd.Prim`
  - :py:class:`pxr.Usd.Property`
  - :py:class:`pxr.Usd.Attribute`
  - :py:class:`pxr.Usd.Relationship`
  - :py:class:`pxr.Usd.SchemaBase`
  - :py:class:`pxr.UsdGeom.Primvar`
  - :py:class:`pxr.Sdf.PrimSpec`
  - :py:class:`pxr.Sdf.PropertySpec`
  - :py:class:`~nvidia_usd_validation.FormatDependency`
"""

ANON_VALIDATOR_LAYER_NAME = "AssetValidator"
"""str: Internal layer name to use with anonymous layers."""


@dataclass(frozen=True)
class Identifier(Generic[AtType]):
    """
    An Identifier is a stateful representation of an Usd object (i.e. Usd.Prim). A identifier can convert back to a
    live Usd object.
    """

    @classmethod
    def from_(cls, obj: AtType) -> Identifier[AtType]:
        """
        Args:
            obj (AtType): An Usd Object.

        Returns:
            A stateful representation of an Usd object.
        """
        raise NotImplementedError()

    def restore(self, stage: Usd.Stage) -> AtType:
        """
        Convert this stateful identifier to a live object.

        Args:
            stage (Usd.Stage): The stage to use to restore the object.

        Returns:
            An Usd object.
        """
        raise NotImplementedError()

    @deprecated("For testing use Sdf.Path")
    def as_str(self) -> str:
        raise NotImplementedError()

    @deprecated("Use get_spec_ids instead")
    def get_layer_ids(self) -> list[LayerId]:
        return [spec_id.layer_id for spec_id in self.get_spec_ids()]

    def get_spec_ids(self) -> list[SpecId]:
        """
        Returns:
            The list of all possible prim specs i.e., path and layer ids associated to this identifier.
        """
        return []


@dataclass(frozen=True)
class LayerId(Identifier[Sdf.Layer]):
    """
    A unique identifier to layer, i.e. identifier.

    Attributes:
        identifier (str): The unique identifier of this layer.
    """

    identifier: str

    def __post_init__(self):
        object.__setattr__(self, "identifier", normalize_url(self.identifier))

    @classmethod
    def from_(cls, layer: Sdf.Layer) -> LayerId:
        return LayerId(
            identifier=layer.identifier,
        )

    def restore(self, stage: Usd.Stage) -> Sdf.Layer:
        return Sdf.Layer.FindOrOpen(self.identifier)

    def get_spec_ids(self) -> list[SpecId]:
        return [SpecId(layer_id=self)]

    def as_str(self):
        return self.identifier

    @property
    def _internal(self) -> bool:
        return (
            Sdf.Layer.IsAnonymousLayerIdentifier(self.identifier)
            and Sdf.Layer.GetDisplayNameFromIdentifier(self.identifier) == ANON_VALIDATOR_LAYER_NAME
        )


@dataclass(frozen=True)
class StageId(Identifier[Usd.Stage]):
    """
    A unique identifier to stage, i.e. identifier.

    Attributes:
        root_layer (LayerId): Identifier representing the root layer.
    """

    root_layer: LayerId

    @classmethod
    def from_(cls, stage: Usd.Stage) -> StageId:
        return StageId(
            root_layer=LayerId.from_(stage.GetRootLayer()),
        )

    @property
    @deprecated("Use root_layer instead")
    def identifier(self) -> str:
        return self.root_layer.identifier

    @property
    def stage_id(self) -> StageId:
        return self

    def restore(self, stage: Usd.Stage) -> Usd.Stage:
        if LayerId.from_(stage.GetRootLayer()) != self.root_layer:
            raise ValueError("The supplied stage do not corresponds to current stage.")
        return stage

    def as_str(self) -> str:
        return f"Stage <{self.root_layer.identifier}>"

    def get_spec_ids(self) -> list[SpecId]:
        return self.root_layer.get_spec_ids()


class VariantIdMixin:
    """
    Mixin class for handling variant selection paths for USD prims.

    This class provides utility methods to retrieve and restore variant selections
    for USD prims, making it easier to work with variant hierarchies.
    """

    @property
    def variant_selection_path(self) -> Sdf.Path:
        return Sdf.Path.emptyPath

    @staticmethod
    def get_variant_selection_path(prim: Usd.Prim) -> Sdf.Path:
        """
        Return a Sdf.Path with variant selection encoded.

        For Example:
            Sdf.Path("/World/asset{variantA=aaa}child{variantB=bbb}{variantC=ccc}group/mesh.extent")
        """

        paths = []
        # Traverse the hierarchy to get variant selections
        while prim and prim.GetPath() != Sdf.Path.absoluteRootPath:
            path = Sdf.Path(prim.GetName())

            # Get the variant sets for the current prim
            variant_sets = prim.GetVariantSets()
            # Append each variant set and its selected variant
            for variant_set_name in variant_sets.GetNames():
                variant_set = variant_sets.GetVariantSet(variant_set_name)
                selected_variant = variant_set.GetVariantSelection()
                if selected_variant:
                    path = path.AppendVariantSelection(variant_set_name, selected_variant)

            paths.append(path)
            prim = prim.GetParent()

        variant_selection_path = Sdf.Path.absoluteRootPath
        for path in reversed(paths):
            variant_selection_path = variant_selection_path.AppendPath(path)

        return variant_selection_path

    def restore_variant_selection(self, stage: Usd.Stage):
        all_variant_selections: list[tuple[Sdf.Path, list[tuple[str, str]]]] = []
        selected_variants: list[tuple[str, str]] = []
        # Retrieve all parent variant selections from self.variant_selection_path
        for path in self.variant_selection_path.GetAncestorsRange():
            if path.IsPrimVariantSelectionPath():
                selected_variants.append(path.GetVariantSelection())
            else:
                if selected_variants:
                    all_variant_selections.append((path.StripAllVariantSelections().GetPrimPath(), selected_variants))
                selected_variants = []

        for prim_path, variants in reversed(all_variant_selections):
            for variant_name, selected_variant in variants:
                stage.GetPrimAtPath(prim_path).GetVariantSet(variant_name).SetVariantSelection(selected_variant)


@dataclass(frozen=True)
class PrimId(Identifier[Usd.Prim], VariantIdMixin):
    """
    A unique identifier of a prim, i.e. a combination of Stage definition and a list of Specs.

    Attributes:
        stage_id (StageId): An identifier to the stage this prim exists.
        path (Sdf.Path): The path to this prim.
        spec_ids (EditTargetIdList): The list of specifications as found in the stage.
        variant_selection_path (Sdf.Path): The variant selection path for this prim.
    """

    stage_id: StageId
    path: Sdf.Path
    spec_ids: SpecIdList = field(default_factory=lambda: EditTargetIdList())
    variant_selection_path: Sdf.Path = Sdf.Path.emptyPath

    @classmethod
    def from_(cls, prim: Usd.Prim) -> PrimId:
        return PrimId(
            stage_id=StageId.from_(prim.GetStage()),
            path=prim.GetPrimPath(),
            spec_ids=EditTargetIdList.from_(prim),
            variant_selection_path=cls.get_variant_selection_path(prim),
        )

    def restore(self, stage: Usd.Stage) -> Usd.Prim:
        stage = self.stage_id.restore(stage)
        return stage.GetPrimAtPath(self.path)

    def as_str(self) -> str:
        return f"Prim <{self.path}>"

    def get_spec_ids(self) -> list[SpecId]:
        return list(self.spec_ids)

    def __str__(self):
        """Custom str as path is calculated."""
        return f"PrimId(stage_id={self.stage_id}, path={self.path})"


@dataclass(frozen=True)
class PropertyId(Identifier[Usd.Attribute], VariantIdMixin):
    """
    A unique identifier of a property, i.e. a combination of prim definition and property path.

    Attributes:
        prim_id (PrimId): An identifier to the prim containing this property.
        path (Sdf.Path): The path to this property.
    """

    prim_id: PrimId
    path: Sdf.Path

    @property
    def variant_selection_path(self):
        return self.prim_id.variant_selection_path.AppendElementString(self.path.elementString)

    @classmethod
    def from_(cls, prop: Usd.Property) -> PropertyId:
        return PropertyId(prim_id=PrimId.from_(prop.GetPrim()), path=prop.GetPath())

    def restore(self, stage: Usd.Stage) -> Usd.Property:
        prim = self.prim_id.restore(stage)
        return prim.GetProperty(self.name)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def stage_id(self) -> StageId:
        return self.prim_id.stage_id

    def as_str(self) -> str:
        return f"Attribute ({self.name}) {self.prim_id.as_str()}"

    def get_spec_ids(self) -> list[SpecId]:
        return [
            replace(node_id, path=node_id.path.AppendProperty(self.name)) for node_id in self.prim_id.get_spec_ids()
        ]


@dataclass(frozen=True)
class AttributeId(PropertyId):
    """
    A unique identifier of an attribute, i.e. a combination of prim definition and attribute name.
    """

    @classmethod
    def from_(cls, attr: Usd.Attribute) -> AttributeId:
        return AttributeId(prim_id=PrimId.from_(attr.GetPrim()), path=attr.GetPath())


@dataclass(frozen=True)
class RelationshipId(PropertyId):
    """
    A unique identifier of a relationship, i.e. a combination of prim definition and relationship name.
    """

    @classmethod
    def from_(cls, rel: Usd.Relationship) -> RelationshipId:
        return RelationshipId(prim_id=PrimId.from_(rel.GetPrim()), path=rel.GetPath())


@dataclass(frozen=True)
class PrimvarId(AttributeId, Identifier[UsdGeom.Primvar]):
    """Alias for primvars."""

    @classmethod
    def from_(cls, primvar: UsdGeom.Primvar) -> PrimvarId:
        attribute_id = super().from_(primvar.GetAttr())
        return PrimvarId(
            prim_id=attribute_id.prim_id,
            path=attribute_id.path,
        )

    def restore(self, stage: Usd.Stage) -> UsdGeom.Primvar:
        return UsdGeom.Primvar(super().restore(stage))


@dataclass(frozen=True)
class SchemaBaseId(Identifier[Usd.SchemaBase], VariantIdMixin):
    """
    A unique identifier of a UsdSchemaBase, i.e. a combination of prim definition and its real type class.

    Attributes:
        prim_id (PrimId): An identifier to the prim this schema is applied or typed to.
        schema_class (Any): The real type class that's inherited from UsdSchemaBase.
    """

    prim_id: PrimId
    schema_class: Any
    instance_name: str | None  # Only valid when it's multi apply schema.

    @property
    def variant_selection_path(self):
        return self.prim_id.variant_selection_path

    @classmethod
    def from_(cls, instance: Usd.SchemaBase) -> SchemaBaseId:
        return SchemaBaseId(
            prim_id=PrimId.from_(instance.GetPrim()),
            schema_class=type(instance),
            instance_name=instance.GetName() if instance.IsMultipleApplyAPISchema() else "",
        )

    @property
    def path(self) -> Sdf.Path:
        return self.prim_id.path

    def restore(self, stage: Usd.Stage) -> Any:
        prim = self.prim_id.restore(stage)
        return self.schema_class(prim, self.instance_name) if self.instance_name else self.schema_class(prim)

    def get_spec_ids(self) -> list[SpecId]:
        return self.prim_id.get_spec_ids()

    def as_str(self) -> str:
        return self.prim_id.as_str()


@dataclass(frozen=True)
class EditTargetId(Identifier[Sdf.Layer | Sdf.Spec]):
    """
    A unique identifier to a edit targets (i.e. layer or spec).

    Attributes:
        layer_id (LayerId): The layer where this identifier exists.
        path (Sdf.Path | None): The path to this specification. If None, the edit target is the layer.
        composed (PrimId | PropertyId | None): Optional. A reference to the composed prim or property if this edit target is a composition arc.
    """

    layer_id: LayerId
    path: Sdf.Path | None = None
    composed: PrimId | PropertyId | None = None

    @singledispatchmethod
    @classmethod
    def from_(cls, obj: Sdf.Layer | Sdf.Spec) -> EditTargetId:
        raise NotImplementedError(f"Unknown type {type(obj)}")

    @from_.register(Sdf.Layer)
    @classmethod
    def _(cls, layer: Sdf.Layer) -> EditTargetId:
        return EditTargetId(
            layer_id=LayerId.from_(layer),
            path=None,
        )

    @from_.register(Sdf.Spec)
    @classmethod
    def _(cls, spec: Sdf.Spec) -> EditTargetId:
        return EditTargetId(
            layer_id=LayerId.from_(spec.layer),
            path=spec.path,
        )

    def restore(self, stage: Usd.Stage) -> Sdf.Layer | Sdf.Spec | None:
        layer: Sdf.Layer = self.layer_id.restore(stage)  # Hold ref.
        if not layer:
            return None
        if not self.path:
            return layer
        spec: Sdf.Spec = layer.GetObjectAtPath(self.path)
        if not spec:
            return None
        return spec

    def get_spec_ids(self) -> list[EditTargetId]:
        return [self]

    def as_str(self) -> str:
        if self.path is None:
            return f"Sdf.Find('{self.layer_id.identifier}')"
        else:
            return f"Sdf.Find('{self.layer_id.identifier}', '{self.path}')"

    @property
    def _internal(self) -> bool:
        return self.layer_id._internal


SpecId = EditTargetId
"""
Deprecated. Use EditTargetId instead.
"""


@dataclass(frozen=True)
class EditTargetIdList(Sequence[EditTargetId]):
    """
    A list of edit target ids.
    """

    _values: list[EditTargetId] = field(default_factory=list, hash=False)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, item: int) -> EditTargetId:
        return self._values[item]

    @property
    @deprecated("Use as a list instead")
    def spec_ids(self) -> list[SpecId]:
        return self._values

    @singledispatchmethod
    @classmethod
    def from_(cls, obj) -> EditTargetIdList:
        raise NotImplementedError(f"Unknown type {type(obj)}")

    @from_.register(type(None))
    @classmethod
    def _(cls, obj: None) -> EditTargetIdList:
        return EditTargetIdList()

    @from_.register(Sdf.Layer)
    @classmethod
    def _(cls, layer: Sdf.Layer) -> EditTargetIdList:
        return EditTargetIdList([EditTargetId.from_(layer)])

    @from_.register(Sdf.Spec)
    @classmethod
    def _(cls, spec: Sdf.Spec) -> EditTargetIdList:
        return EditTargetIdList([EditTargetId.from_(spec)])

    @from_.register(Usd.Stage)
    @classmethod
    def _(cls, stage: Usd.Stage) -> EditTargetIdList:
        return EditTargetIdList.from_(stage.GetRootLayer())

    @from_.register(Usd.Prim)
    @classmethod
    def _(cls, prim: Usd.Prim) -> EditTargetIdList:
        prim_id = PrimId(
            stage_id=StageId.from_(prim.GetStage()),
            path=prim.GetPath(),
        )
        edit_target_ids: list[EditTargetId] = []
        for spec in prim.GetPrimStack():
            edit_target_id = EditTargetId.from_(spec)
            if edit_target_id._internal:
                continue
            edit_target_ids.append(replace(edit_target_id, composed=prim_id))
        return EditTargetIdList(edit_target_ids)

    @from_.register(Usd.Property)
    @classmethod
    def _(cls, prop: Usd.Property) -> EditTargetIdList:
        property_id = PropertyId(
            prim_id=PrimId.from_(prop.GetPrim()),
            path=prop.GetPath(),
        )
        edit_target_ids: list[EditTargetId] = []
        for spec in prop.GetPropertyStack(time=Usd.TimeCode.Default()):
            edit_target_id = EditTargetId.from_(spec)
            if edit_target_id._internal:
                continue
            edit_target_ids.append(replace(edit_target_id, composed=property_id))
        return EditTargetIdList(edit_target_ids)

    @from_.register(Usd.SchemaBase)
    @classmethod
    def _(cls, schema: Usd.SchemaBase) -> EditTargetIdList:
        return EditTargetIdList.from_(schema.GetPrim())

    @from_.register(list)
    @classmethod
    def _(cls, objects: list[AtType]) -> EditTargetIdList:
        result: list[EditTargetId] = []
        for obj in objects:
            result.extend(EditTargetIdList.from_(obj))
        return EditTargetIdList(result)


SpecIdList = EditTargetIdList
"""
Deprecated. Use EditTargetIdList instead.
"""


@dataclass(frozen=True)
class FormatDependencyId(Identifier[FormatDependency]):
    """
    A unique identifier for a :py:class:`~nvidia_usd_validation.FormatDependency`.

    Attributes:
        path (str): The specific dependency path.
        root_asset_path (str): The top-level asset that initiated this dependency chain.
    """

    path: str
    root_asset_path: str

    @classmethod
    def from_(cls, dep: FormatDependency) -> FormatDependencyId:
        return FormatDependencyId(path=dep.path, root_asset_path=dep.root_asset_path)


@singledispatch
def to_identifier(value: AtType | None) -> Identifier[AtType] | None:
    """
    Args:
        value (AtType | None): An USD object.

    Returns:
        An identifier (i.e. stateful representation) to a USD object.
    """
    raise NotImplementedError(f"Unknown type {type(value)}")


@to_identifier.register(Identifier)
def _(value: Identifier[AtType]) -> Identifier[AtType]:
    return value


@to_identifier.register(type(None))
def _(value: None) -> None:
    return None


@to_identifier.register(Usd.Attribute)
def _(value: Usd.Attribute) -> AttributeId:
    return AttributeId.from_(value)


@to_identifier.register(Usd.Property)
def _(value: Usd.Property) -> PropertyId:
    return PropertyId.from_(value)


@to_identifier.register(Usd.Relationship)
def _(value: Usd.Relationship) -> RelationshipId:
    return RelationshipId.from_(value)


@to_identifier.register(UsdGeom.Primvar)
def _(value: UsdGeom.Primvar) -> PrimvarId:
    return PrimvarId.from_(value)


@to_identifier.register(Usd.Prim)
def _(value: Usd.Prim) -> PrimId:
    return PrimId.from_(value)


@to_identifier.register(Usd.Stage)
def _(value: Usd.Stage) -> StageId:
    return StageId.from_(value)


@to_identifier.register(Sdf.Layer)
def _(value: Sdf.Layer) -> LayerId:
    return LayerId.from_(value)


@to_identifier.register(Sdf.Spec)
def _(value: Sdf.Spec) -> SpecId:
    return SpecId.from_(value)


@to_identifier.register(Usd.SchemaBase)
def _(value: Usd.SchemaBase) -> SchemaBaseId:
    return SchemaBaseId.from_(value)


@to_identifier.register(FormatDependency)
def _(value: FormatDependency) -> FormatDependencyId:
    return FormatDependencyId.from_(value)


@to_identifier.register(list)
@to_identifier.register(tuple)
def _(value: list[AtType] | tuple[AtType, ...]) -> tuple[Identifier[AtType], ...]:
    return tuple(to_identifier(item) for item in value)


def to_identifiers(value: list[AtType] | None) -> tuple[Identifier[AtType], ...] | None:
    """Alias for :func:`to_identifier` when called with a list."""
    return to_identifier(value)
