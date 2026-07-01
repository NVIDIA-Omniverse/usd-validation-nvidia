# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Usd, UsdGeom, UsdLux, UsdShade, UsdSkel

from .._base_rule_checker import BaseRuleChecker
from .._categories import register_rule
from .._issues import Suggestion

__all__ = [
    "SkelBindingAPIAppliedChecker",
    "UsdGeomSubsetChecker",
    "UsdLuxSchemaChecker",
]


@register_rule("Other")
class UsdGeomSubsetChecker(BaseRuleChecker):
    """
    Ensures that a valid family name attribute is set for every UsdGeomSubset that has a material binding.
    """

    @classmethod
    def apply_family_name_fix(cls, _: Usd.Stage, subset: UsdGeom.Subset) -> None:
        subset.CreateFamilyNameAttr().Set(UsdShade.Tokens.materialBind)

    def CheckPrim(self, prim):
        if not prim.IsA(UsdGeom.Subset):
            return

        has_material_binding_rel = False
        has_family_name = False

        for prop in prim.GetProperties():
            has_material_binding_rel = has_material_binding_rel or prop.GetName().startswith(
                UsdShade.Tokens.materialBinding
            )
            has_family_name = has_family_name or prop.GetName().startswith("familyName")

        subset = UsdGeom.Subset(prim)

        if has_material_binding_rel and (
            not has_family_name or subset.GetFamilyNameAttr().Get() != UsdShade.Tokens.materialBind
        ):
            self._AddFailedCheck(
                f"GeomSubset '{prim.GetName()}' has a material binding but no valid family name attribute.",
                at=subset,
                suggestion=Suggestion(
                    callable=self.apply_family_name_fix,
                    message="Adds the family name attribute.",
                    at=[
                        relationship
                        for relationship in prim.GetRelationships()
                        if relationship.GetName().startswith(UsdShade.Tokens.materialBinding)
                    ],
                ),
            )


@register_rule("Other")
class UsdLuxSchemaChecker(BaseRuleChecker):
    """
    In USD 21.02, Lux attributes were prefixed with inputs: to make them connectable. This rule checker ensure that
    all UsdLux attributes have the appropriate prefix.
    """

    LUX_ATTRIBUTES: set[str] = {
        "angle",
        "color",
        "temperature",
        "diffuse",
        "specular",
        "enableColorTemperature",
        "exposure",
        "height",
        "width",
        "intensity",
        "length",
        "normalize",
        "radius",
        "shadow:color",
        "shadow:distance",
        "shadow:enable",
        "shadow:falloff",
        "shadow:falloffGamma",
        "shaping:cone:angle",
        "shaping:cone:softness",
        "shaping:focus",
        "shaping:focusTint",
        "shaping:ies:angleScale",
        "shaping:ies:file",
        "shaping:ies:normalize",
        "texture:format",
    }
    """
    List of attributes to check prefixes for.
    """

    @classmethod
    def fix_attribute_name(cls, _: Usd.Stage, attribute: Usd.Attribute) -> None:
        attribute_value = attribute.Get()
        prim: Usd.Prim = attribute.GetPrim()
        old_name = attribute.GetName()
        new_name = f"inputs:{old_name}"
        new_attribute = prim.CreateAttribute(new_name, attribute.GetTypeName())
        new_attribute.Set(attribute_value)
        if attribute.ValueMightBeTimeVarying():
            time_samples = attribute.GetTimeSamples()
            for time in time_samples:
                timecode = Usd.TimeCode(time)
                new_attribute.Set(attribute.Get(timecode), timecode)

        # prim.RemoveProperty(old_name)

    def CheckPrim(self, prim):
        if not (hasattr(UsdLux, "Light") and prim.IsA(UsdLux.Light)) and not (
            hasattr(UsdLux, "LightAPI") and prim.HasAPI(UsdLux.LightAPI)
        ):
            return

        attributes = prim.GetAuthoredAttributes()
        attribute_names = [attr.GetName() for attr in attributes]
        for attribute in attributes:
            attribute_value = attribute.Get()

            if attribute_value is None:
                continue

            if not attribute.GetName() in self.LUX_ATTRIBUTES:
                continue

            if f"inputs:{attribute.GetName()}" in attribute_names:
                continue

            self._AddFailedCheck(
                f"UsdLux attribute {attribute.GetName()} has been renamed in USD 21.02 and should be prefixed with 'inputs:'.",
                at=attribute,
                suggestion=Suggestion(
                    callable=self.fix_attribute_name,
                    message=f"Creates a new attribute {attribute.GetName()} prefixed with inputs: for compatibility.",
                    at=attribute,
                ),
            )


@register_rule("Other")
class SkelBindingAPIAppliedChecker(BaseRuleChecker):
    """
    A prim providing skelBinding properties, must have SkelBindingAPI applied on the prim.
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        usd_schema_registry = Usd.SchemaRegistry()
        prim_def = usd_schema_registry.BuildComposedPrimDefinition("", ["SkelBindingAPI"])
        self._skel_binding_api_props = prim_def.GetPropertyNames()

    @classmethod
    def apply_api(cls, _: Usd.Stage, prim: Usd.Prim) -> None:
        UsdSkel.BindingAPI.Apply(prim)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if not prim.HasAPI(UsdSkel.BindingAPI):
            for property_name in self._skel_binding_api_props:
                if prim.HasProperty(property_name):
                    # Verify has authored value, i.e. not blocked.
                    prop: Usd.Property = prim.GetProperty(property_name)
                    if isinstance(prop, Usd.Attribute):
                        if not prop.HasAuthoredValue():
                            continue
                    elif isinstance(prop, Usd.Relationship):
                        if not prop.HasAuthoredTargets():
                            continue

                    self._AddFailedCheck(
                        f"Found a UsdSkelBinding property ({property_name}), but no SkelBindingAPI "
                        f"applied on the prim.",
                        at=prim,
                        suggestion=Suggestion(
                            callable=self.apply_api,
                            message="Apply SkelBindingAPI",
                            at=prop,
                        ),
                    )
                    return
        else:
            skel_root_type_name: str = "SkelRoot"

            # If the API is already applied make sure this prim is either
            # SkelRoot type or is rooted under a SkelRoot prim, else prim won't
            # be considered for any UsdSkel Skinning.
            if prim.GetTypeName() == skel_root_type_name:
                return
            parent_prim: Usd.Prim = prim.GetParent()
            while not parent_prim.IsPseudoRoot():
                if parent_prim.GetTypeName() == skel_root_type_name:
                    return
                parent_prim = parent_prim.GetParent()

            self._AddFailedCheck(
                "The prim has the UsdSkelBindingAPI applied, but it is not a SkelRoot nor a descendant of one.",
                at=prim,
            )
