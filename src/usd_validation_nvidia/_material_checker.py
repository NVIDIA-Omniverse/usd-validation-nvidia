# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from pxr import Ar, Gf, Sdf, Sdr, Tf, Usd, UsdShade, UsdUtils

import usd_validation_nvidia.capabilities as cap

from ._base_rule_checker import BaseRuleChecker
from ._categories import register_rule
from ._fix import AuthoringLayers
from ._issues import Suggestion
from ._requirements import register_requirements
from ._url_utils import make_relative_url_if_possible, normalize_url
from ._usd_utils import get_sdf_type_for_shader_property

__all__ = [
    "MaterialOldMdlSchemaChecker",
    "MaterialOutOfScopeChecker",
    "MaterialPathChecker",
    "MaterialUsdPreviewSurfaceChecker",
    "ShaderImplementationSourceChecker",
    "UsdDanglingMaterialBinding",
    "UsdMaterialBindingApi",
]

USD_2508_API = Usd.GetVersion() >= (0, 25, 8)


@register_rule("Material")
@register_requirements(cap.Requirements.VM_MDL_001)
class MaterialPathChecker(BaseRuleChecker):
    """
    MDL assets require absolute paths or relative paths prefixed with ``./`` to resolve properly.
    This Rule suggests to prefix ambiguous MDL asset path(s) with a ``./`` to enforce that it is a
    relative path (i.e ``./M_PlantSet_A13.mdl``).
    """

    # Keep this docstring and that of derived classes in sync

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.unresolved_paths: set[str] = set()
        self.resolved_paths: set[str] = set()
        self.resolver: Ar.Resolver = Ar.GetResolver()

    def _path_exists(self, path) -> bool:
        resolved_path: Ar.ResolvedPath = self.resolver.Resolve(path)
        return bool(resolved_path)

    @classmethod
    def _prefix(cls, relative_path) -> str:
        if relative_path.startswith("./"):
            return relative_path
        elif relative_path.startswith("/"):
            return f".{relative_path}"
        else:
            return f"./{relative_path}"

    def CheckUnresolvedPaths(self, unresolvedPaths):
        """
        We collect all unresolved paths, this is because all AssetResolvers are already applied and unresolved paths
        computed here are correct. Any missing path should be validated against this set.
        """
        self.unresolved_paths = set([normalize_url(path) for path in unresolvedPaths])

    def CheckDependencies(self, usdStage, layerDeps, assetDeps):
        """
        We collect all assetDeps, this is because all AssetResolvers are already applied and resolved paths
        computed here are correct. Any existing path should be validated against this set.
        """
        self.resolved_paths = set([normalize_url(path) for path in assetDeps])

    @classmethod
    def fix_path_callback(cls, stage: Usd.Stage, attribute: Usd.Attribute) -> None:
        """
        Suggestion to fix the path. The fix should take into account the location of the layer to be fixed.
        """
        strongest_layer = AuthoringLayers(attribute)[0]
        asset_absolute_path: str = strongest_layer.ComputeAbsolutePath(cls._prefix(attribute.Get().path))

        edit_layer: Sdf.Layer = stage.GetEditTarget().GetLayer()
        if edit_layer.anonymous:
            attribute.Set(Sdf.AssetPath(asset_absolute_path))
        else:
            asset_relative_path: str = make_relative_url_if_possible(edit_layer.identifier, asset_absolute_path)
            attribute.Set(Sdf.AssetPath(cls._prefix(asset_relative_path)))

    def CheckPrim(self, prim):
        if not prim.IsA(UsdShade.Shader):
            return

        for attribute in prim.GetAttributes():
            if attribute.GetTypeName() != Sdf.ValueTypeNames.Asset:
                continue

            attribute_value = attribute.Get()

            # Expected MDL path to be present
            is_mdl_source_asset = attribute.GetName() == "info:mdl:sourceAsset"
            if is_mdl_source_asset and (not attribute_value or not attribute_value.path):
                self._AddFailedCheck(
                    requirement=cap.Requirements.VM_MDL_001,
                    message="MDL file path must be present.",
                    at=attribute,
                )
                continue

            if attribute_value is None:
                continue

            parsed_url = urlparse(attribute_value.path)
            # url.path doesn't include fragments and query string.
            if not is_mdl_source_asset and not parsed_url.path.endswith(".mdl"):
                continue
            elif is_mdl_source_asset and not parsed_url.path.endswith(".mdl"):
                self._AddWarning(
                    requirement=cap.Requirements.VM_MDL_001,
                    message="It should have MDL (.mdl) file specified.",
                    at=attribute,
                )

            material_file_path = normalize_url(attribute_value.path)

            # If it is a resolved path
            if material_file_path in self.resolved_paths:
                continue
            strongest_layer: Sdf.Layer = AuthoringLayers(attribute)[0]

            # If it's a relative path without "." prefixed.
            original_path = attribute_value.path
            prefixed_path = self._prefix(material_file_path)
            if not original_path.startswith("."):
                asset_path = normalize_url(strongest_layer.ComputeAbsolutePath(prefixed_path))
                if self._path_exists(asset_path):
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VM_MDL_001,
                        message=f"Relative path {original_path} should be corrected to {prefixed_path}.",
                        at=attribute,
                        suggestion=Suggestion(
                            callable=self.fix_path_callback,
                            message=f"Corrects asset path `{original_path}` to `{prefixed_path}`",
                            at=attribute,
                        ),
                    )
                    continue

            # Unresolved absolute path
            if material_file_path in self.unresolved_paths:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VM_MDL_001,
                    message=f"The path {original_path} does not exist.",
                    at=attribute,
                )
                continue

            # Unresolved relative path
            asset_path = normalize_url(strongest_layer.ComputeAbsolutePath(prefixed_path))
            if asset_path in self.unresolved_paths:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VM_MDL_001,
                    message=f"The relative path {original_path} does not exist.",
                    at=attribute,
                )
                continue


@register_rule("Material")
@register_requirements(cap.Requirements.VM_BIND_001)
class MaterialOutOfScopeChecker(BaseRuleChecker):
    """
    USD ignores material bindings which target materials that are outside the payloads' hierarchy.
    """

    # Keep this docstring and that of derived classes in sync

    @classmethod
    def _is_material_binding_relationship(cls, rel: Usd.Relationship) -> bool:
        return rel.GetName() == UsdShade.Tokens.materialBinding or rel.GetName().startswith(
            UsdShade.Tokens.materialBinding + ":"
        )

    @classmethod
    def _get_out_of_scope_specs(cls, rel: Usd.Relationship) -> Iterator[tuple[Sdf.Layer, Sdf.Path]]:
        """
        if `GetTargets` contains a relationship target out of scope, it will be missing, i.e. `GetTargets` will
        return empty. However, we can catch the error with UsdUtilsCoalescingDiagnosticDelegate.

        Diagnostics may contain multiple hits (i.e. other threads), so we filter by the current relationship,
        for unresolved references and for warnings. We then proceed to choose the right spec.
        """
        delegate = UsdUtils.CoalescingDiagnosticDelegate()
        rel.GetTargets()
        diagnostics = delegate.TakeUncoalescedDiagnostics()
        specs: Sequence[Sdf.Spec] = rel.GetPropertyStack(time=Usd.TimeCode.Default())
        for diagnostic in diagnostics:
            is_warning: bool = diagnostic.diagnosticCode == Tf.TF_DIAGNOSTIC_WARNING_TYPE
            if not is_warning:
                continue
            is_unresolved: bool = "_ReportErrors" in diagnostic.sourceFunction
            if not is_unresolved:
                continue
            is_relationship: bool = str(rel.GetPath()) in diagnostic.commentary
            if not is_relationship:
                continue
            for spec in specs:
                has_payload_layer: bool = spec.layer.identifier in diagnostic.commentary
                if not has_payload_layer:
                    continue
                has_payload_path: bool = str(spec.path) in diagnostic.commentary
                if not has_payload_path:
                    continue
                yield spec.layer, spec.path

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if not prim.HasAPI(UsdShade.MaterialBindingAPI):
            return
        for rel in prim.GetRelationships():
            if not self._is_material_binding_relationship(rel):
                continue
            for spec_layer, spec_path in self._get_out_of_scope_specs(rel):
                self._AddFailedCheck(
                    requirement=cap.Requirements.VM_BIND_001,
                    message=f"The relationship target from <{spec_path}> in layer @{spec_layer.identifier}@ refers to a path "
                    f"outside the scope of the payload.",
                    at=rel,
                )


@register_rule("Material")
class UsdDanglingMaterialBinding(BaseRuleChecker):
    """
    Rule ensuring that the bound material exists in the scene.
    """

    @classmethod
    def apply_dangling_material_binding_fix(cls, _: Usd.Stage, prim) -> None:
        api = UsdShade.MaterialBindingAPI(prim)
        api.UnbindAllBindings()

    def CheckPrim(self, prim):
        rel = prim.GetRelationship(UsdShade.Tokens.materialBinding)

        if rel:
            stage = prim.GetStage()
            for target in rel.GetTargets():
                if not stage.GetPrimAtPath(target):
                    self._AddFailedCheck(
                        f"Prim '{prim.GetName()}' has a material binding to '{target}' but that location does not exist",
                        at=prim,
                        suggestion=Suggestion(
                            callable=self.apply_dangling_material_binding_fix,
                            message="Remove material bindings from the prim.",
                            at=rel,
                        ),
                    )
                    break


@register_rule("Material")
class UsdMaterialBindingApi(BaseRuleChecker):
    """
    Rule ensuring that the MaterialBindingAPI is applied on all prims that have a material binding property.
    """

    @classmethod
    def apply_material_binding_api_fix(cls, _: Usd.Stage, prim) -> None:
        UsdShade.MaterialBindingAPI.Apply(prim)

    def CheckPrim(self, prim):
        if prim.HasAPI(UsdShade.MaterialBindingAPI):
            return

        has_material_binding_rel = any(
            rel.GetName().startswith(UsdShade.Tokens.materialBinding) for rel in prim.GetRelationships()
        )
        if has_material_binding_rel and not prim.HasAPI(UsdShade.MaterialBindingAPI):
            self._AddFailedCheck(
                f"Prim '{prim.GetName()}' has a material binding but does not have the MaterialBindingApi.",
                at=prim,
                suggestion=Suggestion(
                    callable=self.apply_material_binding_api_fix,
                    message="Applies the material binding API.",
                    at=[
                        relationship
                        for relationship in prim.GetRelationships()
                        if relationship.GetName().startswith(UsdShade.Tokens.materialBinding)
                    ],
                ),
            )


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


@register_rule("Material")
@register_requirements(cap.Requirements.VM_PS_001)
class MaterialUsdPreviewSurfaceChecker(BaseRuleChecker):
    """
    Rule ensuring that UsdShadeShader prims conform to the UsdPreviewSurface specification.
    """

    # Keep this docstring in sync with derived classes

    usd_preview_surface_shaders = []

    @dataclass
    class _ValidationResult:
        """Returned as a result of a failed validation check."""

        requirement: cap.Requirements
        path: Sdf.Path
        message: str
        suggestion: str

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool) -> None:
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

        if not MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders:
            if USD_2508_API:
                nodes = Sdr.Registry().GetShaderNodeNames()
            else:
                nodes = Sdr.Registry().GetNodeNames()
            for sdr_node_name in nodes:
                if sdr_node_name.startswith("Usd"):
                    MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders.append(sdr_node_name)

    def CheckStage(self, usdStage: Usd.Stage) -> None:
        # Without UsdPreviewSurface shader definitions in the Sdr Registry the per-prim checks
        # below cannot identify any UsdPreviewSurface shaders and the rule silently passes.
        # This typically means the ``shaderDefs.usda`` shader resource is missing from the
        # runtime (e.g., on the ``usd-exchange`` wheel). Surface a warning so users know the
        # rule did not actually inspect their shaders.
        if not MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders:
            self._AddWarning(
                "No UsdPreviewSurface shader definitions are registered with the Sdr Registry, "
                "so this rule cannot validate any shaders. This typically means the "
                "'shaderDefs.usda' shader resource is unavailable in the current USD runtime.",
                at=usdStage,
            )

    # Fixes

    @classmethod
    def write_usd_shade_input_output_type_name(
        cls, usdshade_inout: UsdShade.Input | UsdShade.Output, type_name: Sdf.ValueTypeName
    ) -> None:
        """Set the typeName of the underlying attribute iff the current value differs from the new one."""
        if usdshade_inout.GetTypeName() != type_name:
            usdshade_inout.GetAttr().SetTypeName(type_name)

    @classmethod
    def write_usd_shade_input_value(cls, usd_shade_input: UsdShade.Input, input_value: _InputValue) -> None:
        """Set the value of the attribute iff the current value differs from the new one."""
        attr = usd_shade_input.GetAttr()

        if attr.HasAuthoredValue() and attr.GetNumTimeSamples():
            existing_samples = []

            for sample_time in attr.GetTimeSamples():
                existing_samples.append((sample_time, attr.Get(sample_time)))

            if existing_samples:
                if not input_value.time_samples:
                    # new value is not time sampled, so clear.
                    attr.Clear()

                elif input_value.time_samples != existing_samples:
                    # new values don't match what is already set
                    attr.Clear()

                    for sample_time, sample_value in input_value.time_samples:
                        attr.Set(sample_value, sample_time)

        if (input_value.value is not None) and (input_value.value != attr.Get()):
            attr.Set(input_value.value)

    def write_usd_shade_input_metadata(self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty) -> None:
        """Set the metadata iff it differs from what is already defined."""
        if self._validate_usd_shade_input_metadata(usd_shade_input, sdr_property) is not None:
            options = [o[0] for o in sdr_property.GetOptions()]
            usd_shade_input.GetAttr().SetMetadata("allowedTokens", options)

    @classmethod
    def write_usd_shade_input_connections(
        cls, usd_shade_input: UsdShade.Input, connections: list[UsdShade.ConnectionSourceInfo], force_write: bool
    ) -> None:
        """Set the usd_shade_input connected sources"""
        if force_write or len(connections[0]) > 1:
            usd_shade_input.ClearSources()
            usd_shade_input.SetConnectedSources(connections[0][0:1])

    @classmethod
    def write_usd_shade_input_empty_connection(
        cls,
        usd_shade_input: UsdShade.Input,
    ) -> None:
        """Clear the usd_shade_input connected sources"""
        list_op = Sdf.PathListOp()
        list_op.explicitItems = []
        usd_shade_input.GetAttr().SetMetadata("connectionPaths", list_op)

    @classmethod
    def write_usd_shade_input_connectibility(cls, usd_shade_input: UsdShade.Input, token_value: str) -> None:
        if usd_shade_input.GetConnectability() != token_value:
            usd_shade_input.SetConnectability(token_value)

    @classmethod
    def convert_color3f_to_float(
        cls, input_value: _InputValue, connections: list[UsdShade.ConnectionSourceInfo]
    ) -> tuple[_InputValue, list[UsdShade.ConnectionSourceInfo]]:
        if input_value.value and isinstance(input_value.value, Gf.Vec3f):
            input_value.value = input_value.value[0]

        # assume all type sampled values are the same
        # if they are not the Usd would error on load.
        if input_value.time_samples and isinstance(input_value.time_samples[0][1], Gf.Vec3f):
            new_values = []

            for sample_time, sample_value in input_value.time_samples:
                new_values.append((sample_time, sample_value[0]))

            input_value.time_samples = new_values

        if connections:
            for i, info in enumerate(connections[0]):
                source_name = info.sourceName
                if source_name == "rgb":
                    source_name = "r"

                connections[0][i] = UsdShade.ConnectionSourceInfo(
                    info.source, source_name, info.sourceType, Sdf.ValueTypeNames.Float
                )

        return input_value, connections

    def _input_value_and_connections_transform(
        self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> tuple[bool, Sdf.ValueTypeName, Any, list[UsdShade.ConnectionSourceInfo]]:
        input_value = _InputValue.create_from_input(usd_shade_input)
        type_name = usd_shade_input.GetTypeName()
        connections = usd_shade_input.GetConnectedSources()
        transformed = False

        return transformed, type_name, input_value, connections

    def update_usd_shade_input(self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty) -> None:
        """Update the UsdShade.Input from SdrProperty, restore any parameter values and/or connections that have been set."""

        (force_connection_write, type_name, input_value, connections) = self._input_value_and_connections_transform(
            usd_shade_input, sdr_property
        )

        if self._validate_usd_shade_input_value(usd_shade_input, input_value, sdr_property) is not None:
            input_value.value = sdr_property.GetDefaultValue()
            input_value.time_samples = None

        sdf_type = get_sdf_type_for_shader_property(sdr_property)

        if not self._validate_type_name(sdr_property, sdf_type):
            input_value.value = sdr_property.GetDefaultValue()
            input_value.time_samples = None

        self.write_usd_shade_input_output_type_name(usd_shade_input, sdf_type)

        if self._validate_usd_shade_input_connectability(usd_shade_input, sdr_property) is not None:
            # we end up here if the connectability metadata has been explicitly set,
            # and it's value does not match what is specificed via Sdr.
            connectability = UsdShade.Tokens.interfaceOnly
            if sdr_property.IsConnectable():
                connectability = UsdShade.Tokens.full

            self.write_usd_shade_input_connectibility(usd_shade_input, connectability)

        self.write_usd_shade_input_metadata(usd_shade_input, sdr_property)

        if connections and connections[0]:
            self.write_usd_shade_input_connections(usd_shade_input, connections, force_connection_write)

        self.write_usd_shade_input_value(usd_shade_input, input_value)

    def update_usdshade_output(self, usdshade_output: UsdShade.Output, sdr_property: Sdr.ShaderProperty) -> None:
        """Update the UsdShade.Output from SdrProperty."""
        sdf_type = get_sdf_type_for_shader_property(sdr_property)
        self.write_usd_shade_input_output_type_name(usdshade_output, sdf_type)

    def _should_input_be_filtered(self, shader_input: UsdShade.Input) -> True:
        # Placeholder
        return False

    def update_usdshade_shader(self, usdshade_shader: UsdShade.Shader) -> None:
        """Update shader prim inputs and outputs if they fail validation"""
        shader_id = usdshade_shader.GetShaderId()

        # not a UsdPreviewSurface shader, so skip.
        if shader_id not in MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders:
            return

        sdr_node = Sdr.Registry().GetShaderNodeByName(shader_id)

        # inputs
        for usd_shade_input in usdshade_shader.GetInputs():
            base_name = usd_shade_input.GetBaseName()

            # skip inputs we don't care about
            if self._should_input_be_filtered(usd_shade_input):
                # don't allow connections to any of these parameters
                self.write_usd_shade_input_connectibility(usd_shade_input, UsdShade.Tokens.interfaceOnly)
                continue

            sdr_property = sdr_node.GetShaderInput(base_name) if USD_2508_API else sdr_node.GetInput(base_name)
            if not sdr_property:
                if self._validate_usd_shade_input_invalid_connection(usd_shade_input):
                    self.write_usd_shade_input_empty_connection(usd_shade_input)

                # don't allow connections to any of these parameters
                self.write_usd_shade_input_connectibility(usd_shade_input, UsdShade.Tokens.interfaceOnly)
                continue

            if self._validate_usd_shade_input(usd_shade_input, sdr_property) is not None:
                self.update_usd_shade_input(usd_shade_input, sdr_property)

        # outputs
        for usdshade_output in usdshade_shader.GetOutputs():
            base_name = usdshade_output.GetBaseName()
            sdr_property = sdr_node.GetShaderOutput(base_name) if USD_2508_API else sdr_node.GetOutput(base_name)

            if self._validate_usdshade_output(usdshade_output, sdr_property) is not None:
                self.update_usdshade_output(usdshade_output, sdr_property)

    def update_usdshade_nodegraph(self, usdshade_nodegraph: UsdShade.NodeGraph) -> None:
        consumers_map = usdshade_nodegraph.ComputeInterfaceInputConsumersMap()

        # an input on the Nodegraph can have multiple properties connected to it
        # internally, set its type to be the same type as the first connection (if it exists)
        for usd_shade_input, connected_inputs in consumers_map.items():
            if connected_inputs:
                self.write_usd_shade_input_output_type_name(usd_shade_input, connected_inputs[0].GetTypeName())

        for usdshade_output in usdshade_nodegraph.GetOutputs():
            connections = usdshade_output.GetConnectedSources()
            if connections[0]:
                self.write_usd_shade_input_output_type_name(usdshade_output, connections[0][0].typeName)

    def update_prim(self, stage: Usd.Stage, prim: Usd.Prim) -> bool:
        """Update all child UsdShade.Shader prims that do not conform to the UsdPreviewSurface specification."""

        # If the prim is an instance or proxy skip it.
        # If the prototype exists on the stage root layer it will be flagged for updating if necessary;
        # however if the prototype is on another layer and composed via reference or payload there is
        # nothing we can do about it.
        if prim.IsInstance() or prim.IsInstanceProxy():
            return False

        if UsdShade.ConnectableAPI(prim).IsContainer():
            did_update = False
            for child_prim in prim.GetAllChildren():
                did_update |= self.update_prim(stage, child_prim)

            if did_update:
                # if the prim is a UsdShade Nodegraph, and we have modified its contents
                # update the types on any input and/or output ports if necessary
                usdshade_nodegraph = UsdShade.NodeGraph(prim)
                if usdshade_nodegraph:
                    self.update_usdshade_nodegraph(usdshade_nodegraph)

            return did_update

        elif self._validate_prim(prim):
            usdshade_shader = UsdShade.Shader(prim)

            if usdshade_shader:
                self.update_usdshade_shader(usdshade_shader)

            return True

        return False

    # Validations

    @classmethod
    def _validate_type_name(cls, sdr_property: Sdr.ShaderProperty, type_name: Sdf.ValueTypeName) -> bool:
        # The SDR registry will return Sdf.ValueTypeNames.String for
        # properties that the spec declares as Sdf.ValueTypeNames.Token.
        # So when comparing for equality convert to Token to String
        sdf_type = get_sdf_type_for_shader_property(sdr_property)

        if sdf_type == Sdf.ValueTypeNames.Token:
            sdf_type = Sdf.ValueTypeNames.String

        type_name_to_check = type_name
        if type_name_to_check == Sdf.ValueTypeNames.Token:
            type_name_to_check = Sdf.ValueTypeNames.String

        return sdf_type == type_name_to_check

    def _validate_attribute_type_name(
        self,
        sdr_property: Sdr.ShaderProperty,
        attribute: Usd.Attribute,
    ) -> _ValidationResult | None:
        type_name = attribute.GetTypeName()
        if not self._validate_type_name(sdr_property, type_name):
            sdf_type = get_sdf_type_for_shader_property(sdr_property)
            return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                requirement=cap.Requirements.VM_PS_001,
                path=attribute.GetPath(),
                message=f"Expected type: '{sdf_type}' actual type: '{type_name}'",
                suggestion="Change type name",
            )

    def _validate_usd_shade_input_connectability(
        self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        attribute = usd_shade_input.GetAttr()

        if attribute and attribute.HasMetadata("connectability"):
            connectability = attribute.GetMetadata("connectability")
            if sdr_property.IsConnectable():
                if connectability != UsdShade.Tokens.full:
                    return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                        requirement=cap.Requirements.VM_PS_001,
                        path=attribute.GetPath(),
                        message=f"Expected connectability to be '{UsdShade.Tokens.full}'",
                        suggestion="Change UsdShadeInput connectability metadata",
                    )

            elif connectability != UsdShade.Tokens.interfaceOnly:
                return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                    requirement=cap.Requirements.VM_PS_001,
                    path=attribute.GetPath(),
                    message=f"Expected connectability to be '{UsdShade.Tokens.interfaceOnly}'",
                    suggestion="Change UsdShadeInput connectability metadata",
                )

    def _validate_usd_shade_input_metadata(
        self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        options = sdr_property.GetOptions()
        if not options:
            return

        attribute = usd_shade_input.GetAttr()

        if attribute and attribute.HasMetadata("allowedTokens"):
            options = sorted([o[0] for o in options])
            allowed_tokens = sorted(attribute.GetMetadata("allowedTokens"))

            if allowed_tokens != options:
                return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                    requirement=cap.Requirements.VM_PS_001,
                    path=attribute.GetPath(),
                    message=f"'allowedTokens' metadata does not match specification, expected: '{options}' actual: '{allowed_tokens}'",
                    suggestion="Change UsdShadeInput allowedTokens metadata",
                )

    def _validate_usd_shade_input_connections(
        self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        connections = usd_shade_input.GetConnectedSources()
        if not connections or not connections[0]:
            return

        is_connectable: bool = sdr_property.IsConnectable()

        if not is_connectable:
            source_info = connections[0][0]
            source_prim = source_info.source.GetPrim()
            # interfaceOnly inputs are allowed to be connected to node graphs (and therefore materials)
            # however Sdr still reports them as not-connectable as of USD 26.03, so we need to check explicitly.
            if source_info.sourceType == UsdShade.AttributeType.Input and source_prim.IsA(UsdShade.NodeGraph):
                is_connectable = True

        # property is tagged as not-connectable but there is a connection
        if not is_connectable:
            return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                requirement=cap.Requirements.VM_PS_001,
                path=usd_shade_input.GetAttr().GetPath(),
                message="Has a connection; however connections to this parameter are prohibited by the specification.",
                suggestion="Remove connections",
            )

        # inputs can only have one connected source
        if len(connections[0]) > 1:
            return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                requirement=cap.Requirements.VM_PS_001,
                path=usd_shade_input.GetAttr().GetPath(),
                message="Has multiple incoming connections.",
                suggestion="Remove additional connections",
            )

    def _validate_usd_shade_input_invalid_connection(self, usd_shade_input: UsdShade.Input) -> _ValidationResult | None:
        connections = usd_shade_input.GetConnectedSources()
        if not connections or not connections[0]:
            return

        # usd_shade_input is connected, but the sdr_property is not defined.
        return MaterialUsdPreviewSurfaceChecker._ValidationResult(
            requirement=cap.Requirements.VM_PS_001,
            path=usd_shade_input.GetAttr().GetPath(),
            message="Has a connection; however this parameter is not defined in the specification.",
            suggestion="Create an empty connection",
        )

    def _validate_token_value(
        self, usd_shade_input: UsdShade.Input, input_value: _InputValue, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        options = sdr_property.GetOptions()

        if options:
            options = [o[0] for o in options]
        elif usd_shade_input.GetBaseName() == "sourceColorSpace":
            # TODO: we should be getting this information from the SDR registry but for the SourceColorSpace parameter we are not.
            # hardcoding this here for now until the Sdr plugins are updated.
            options = ["raw", "sRGB", "auto"]

        if options:
            if input_value.value and input_value.value not in options:
                return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                    requirement=cap.Requirements.VM_PS_001,
                    path=usd_shade_input.GetAttr().GetPath(),
                    message=f"Attribute token value: '{input_value.value}' is not present in the list of allowed tokens: '{options}'",
                    suggestion="Change attribute token value",
                )

            if input_value.time_samples:
                for sample_time, sample_value in input_value.time_samples:
                    if sample_value not in options:
                        return MaterialUsdPreviewSurfaceChecker._ValidationResult(
                            requirement=cap.Requirements.VM_PS_001,
                            path=usd_shade_input.GetAttr().GetPath(),
                            message=f"Attribute contains time sampled value(s) that are not present in the list of allowed tokens: {options}",
                            suggestion="Change time samples",
                        )

    def _validate_usd_shade_input_value(
        self, usd_shade_input: UsdShade.Input, input_value: _InputValue, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        if (input_value.value is not None) or (input_value.time_samples is not None):
            sdf_type = get_sdf_type_for_shader_property(sdr_property)
            if sdf_type in [Sdf.ValueTypeNames.Token, Sdf.ValueTypeNames.String]:
                return self._validate_token_value(usd_shade_input, input_value, sdr_property)

    def _validate_usd_shade_input(
        self, usd_shade_input: UsdShade.Input, sdr_property: Sdr.ShaderProperty
    ) -> list[_ValidationResult]:
        input_value = _InputValue.create_from_input(usd_shade_input)

        results = [
            self._validate_attribute_type_name(sdr_property, usd_shade_input.GetAttr()),
            self._validate_usd_shade_input_connections(usd_shade_input, sdr_property),
            self._validate_usd_shade_input_connectability(usd_shade_input, sdr_property),
            self._validate_usd_shade_input_metadata(usd_shade_input, sdr_property),
            self._validate_usd_shade_input_value(usd_shade_input, input_value, sdr_property),
        ]
        return list(filter(None, results))

    def _validate_usdshade_output(
        self, usdshade_output: UsdShade.Output, sdr_property: Sdr.ShaderProperty
    ) -> _ValidationResult | None:
        return self._validate_attribute_type_name(sdr_property, usdshade_output.GetAttr())

    def _validate_usdshade_shader(
        self, usdshade_shader: UsdShade.Shader, sdr_node: Sdr.ShaderNode
    ) -> list[_ValidationResult]:
        """Compare the inputs and outputs with what those defined in the Sdr.
        Only check the those inputs and outputs that are defined, we can skip the ones that
        are not as they would be default and would be up to spec.
        """
        results = []
        for usd_shade_input in usdshade_shader.GetInputs():
            base_name = usd_shade_input.GetBaseName()

            # skip inputs we don't care about
            if self._should_input_be_filtered(usd_shade_input):
                continue

            sdr_property = sdr_node.GetShaderInput(base_name) if USD_2508_API else sdr_node.GetInput(base_name)
            if not sdr_property:
                results.append(self._validate_usd_shade_input_invalid_connection(usd_shade_input))
                continue

            # skip blocked
            connections = usd_shade_input.GetConnectedSources()
            connected = connections or connections[0]
            if not (connected or usd_shade_input.GetAttr().HasAuthoredValue()):
                continue

            results.extend(self._validate_usd_shade_input(usd_shade_input, sdr_property))

        for output_name in sdr_node.GetShaderOutputNames() if USD_2508_API else sdr_node.GetOutputNames():
            usdshade_output = usdshade_shader.GetOutput(output_name)

            # if the output does not exist, skip it so that we don't
            # unnecessarily add defaulted properties.
            if not usdshade_output:
                continue

            sdr_property = sdr_node.GetShaderOutput(output_name) if USD_2508_API else sdr_node.GetOutput(output_name)
            results.append(self._validate_usdshade_output(usdshade_output, sdr_property))

        return list(filter(None, results))

    def _validate_prim(self, prim: Usd.Prim) -> list[_ValidationResult]:
        """Compare shader with its equivalent SdrNode, if anything is different then flag the
        shader as one that needs to be re-created
        """

        # If the prim is an instance or proxy skip it.
        # If the prototype exists on the stage root layer it will be flagged for updating if necessary;
        # however if the prototype is on another layer and composed via reference or payload there is
        # nothing we can do about it.
        if prim.IsInstance() or prim.IsInstanceProxy():
            return []

        # check container prims: Nodegraphs
        if UsdShade.ConnectableAPI(prim).IsContainer():
            results = []
            for child_prim in prim.GetAllChildren():
                results.extend(self._validate_prim(child_prim))
            return results

        # if we are here and the prim is not a shader then
        # skip it.
        usdshade_shader = UsdShade.Shader(prim)
        if not usdshade_shader:
            return []

        shader_id = usdshade_shader.GetShaderId()

        # not a UsdPreviewSurface shader, so skip.
        if shader_id not in MaterialUsdPreviewSurfaceChecker.usd_preview_surface_shaders:
            return []

        sdr_node = Sdr.Registry().GetShaderNodeByName(shader_id)
        return self._validate_usdshade_shader(usdshade_shader, sdr_node)

    @classmethod
    def prim_has_ancestor_container(cls, prim: Usd.Prim) -> bool:
        """Return True if the prim has an ancestor prim that is a
        UsdShade container, else False
        """

        parent_prim = prim.GetParent()
        if not parent_prim:
            return False

        if UsdShade.ConnectableAPI(parent_prim).IsContainer():
            return True

        return cls.prim_has_ancestor_container(parent_prim)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        """Validate UsdShade Material and Nodegraph prims to ensure conformity with the UsdPreviewSurface specification."""

        # this check covers UsdShade Material and Nodegraph prims
        if not UsdShade.ConnectableAPI(prim).IsContainer():
            return

        # we can skip prims that have an ancestor container
        # as they will be processed when the ancestor is.
        if self.prim_has_ancestor_container(prim):
            return

        for failure in self._validate_prim(prim):
            self._AddFailedCheck(
                requirement=failure.requirement,
                message=f"{failure.path}: {failure.message}",
                at=prim,
                suggestion=Suggestion(
                    self.update_prim,
                    failure.suggestion,
                ),
            )


@register_rule("Material")
class ShaderImplementationSourceChecker(BaseRuleChecker):
    """
    Shader prims require a source implementation, which can be one of "id" (for builtins), "sourceAsset" (for assets),
    or "sourceCode" (for inline JIT compiled shaders). Source Asset or Source Code Shaders can have multiple implementations
    (e.g. one per renderer) which are differentiated by an arbitrary sourceType prefix.
    """

    def CheckPrim(self, prim):
        shader = UsdShade.Shader(prim)
        if not shader:
            return

        source_attr = shader.GetImplementationSourceAttr()
        source_impl = source_attr.Get() if source_attr.HasAuthoredValue() else UsdShade.Tokens.id
        attrs = prim.GetAuthoredPropertiesInNamespace("info")
        has_id = shader.GetIdAttr().HasAuthoredValue()
        source_asset_attrs = [
            x
            for x in attrs
            if x.GetName().endswith(":sourceAsset") or x.GetName().endswith(":sourceAsset:subIdentifier")
        ]
        source_code_attrs = [x for x in attrs if x.GetName().endswith(":sourceCode")]

        if source_impl == UsdShade.Tokens.id:
            if not shader.GetShaderId():
                self._AddFailedCheck("The Shader has an invalid 'info:id'", at=shader)
            if source_asset_attrs or source_code_attrs:
                self._AddWarning("The Shader has multiple source implementation attributes", at=shader)
        elif source_impl == UsdShade.Tokens.sourceAsset:
            if has_id or source_code_attrs:
                self._AddWarning("The Shader has multiple source implementation attributes", at=shader)
        elif source_impl == UsdShade.Tokens.sourceCode:
            if has_id or source_asset_attrs:
                self._AddWarning("The Shader has multiple source implementation attributes", at=shader)
        else:
            self._AddFailedCheck("The Shader has an invalid 'info:implementationSource'", at=shader)


@register_rule("Material")
@register_requirements(cap.Requirements.VM_MDL_002)
class MaterialOldMdlSchemaChecker(BaseRuleChecker):
    """
    Rule ensuring that the deprecated MDL schema is not being used.

    The deprecated MDL schema worked by setting the 'info:implementationSource' property to 'mdlMaterial'.
    The location of the MDL module was passed in via a custom attribute called 'module' of type 'asset'.
    and the subIdentifier was passed in via a custom called 'name' of type 'string' or 'token'.
    """

    # Keep this docstring and that of derived classes in sync

    def update_deprecated_mdl_schema(self, _: Usd.Stage, prim: Usd.Prim) -> bool:
        """Update UsdShade.Shader prims that are using the deprecated MDL schema.

        Updating will make the following changes:
          1. Set the 'info:implementationSource' attribute to 'sourceAsset'.
          2. Set the 'info:mdl:sourceAsset' attribute to the value held by the 'module' attribute of type 'asset'.
          3. Set the 'info:mdl:sourceAsset:subIdentifier' attribute to the value held by the 'name' attribute of type 'string' or 'token'.

        If either the 'module' or 'name' attributes do not exist or if they are not of the expected types, then
        no update will occur and a warning message will be issued.
        """

        shader = UsdShade.Shader(prim)
        if not shader:
            self._AddWarning(
                requirement=cap.Requirements.VM_MDL_002,
                message="Unable to apply deprecated MDL schema fix because the provided Usd.Prim is not a UsdShade.Shader.",
                at=prim,
            )
            return False

        warnings = []

        # verify 'module' attribute exists and is of type Sdf.ValueTypeNames.Asset
        module_attr = prim.GetAttribute("module")
        module = module_attr.Get() if module_attr.HasAuthoredValue() else None

        if not module:
            warnings.append("Missing or empty 'module' attribute.")
        elif module_attr.GetTypeName() != Sdf.ValueTypeNames.Asset:
            warnings.append(f"'module' attribute not of expected type: '{Sdf.ValueTypeNames.Asset}'.")
            module = None

        # verify 'name' attribute exists and is of type Sdf.ValueTypeNames.String or Sdf.ValueTypeNames.Token
        name_attr = prim.GetAttribute("name")
        name = name_attr.Get() if name_attr.HasAuthoredValue() else None

        if not name:
            warnings.append("Missing or empty 'name' attribute.")
        elif name_attr.GetTypeName() not in [Sdf.ValueTypeNames.String, Sdf.ValueTypeNames.Token]:
            warnings.append(
                f"'name' attribute not of expected type: '{Sdf.ValueTypeNames.String}' or '{Sdf.ValueTypeNames.Token}'."
            )
            name = None

        if name and module:
            shader.SetSourceAsset(module, "mdl")
            shader.SetSourceAssetSubIdentifier(name, "mdl")
            return True

        warning_message = "\n".join(warnings)
        self._AddWarning(
            requirement=cap.Requirements.VM_MDL_002,
            message=f"Unable to fix shader using deprecated MDL schema due to the following:\n{warning_message}",
            at=prim,
        )

        return False

    def CheckPrim(self, prim):
        shader = UsdShade.Shader(prim)
        if not shader:
            return

        source_attr = shader.GetImplementationSourceAttr()
        source_impl = source_attr.Get() if source_attr.HasAuthoredValue() else None

        if source_impl == "mdlMaterial":
            self._AddFailedCheck(
                requirement=cap.Requirements.VM_MDL_002,
                message="The shader is using the deprecated MDL schema where 'info:sourceImplementation' is set to 'mdlMaterial',"
                " the 'module' attribute contains the assetPath of the MDL module and the 'name' attribute the subIdentifer.",
                at=prim,
                suggestion=Suggestion(
                    self.update_deprecated_mdl_schema,
                    "Update by setting the following:"
                    " set the 'info:implementationSource' attribute to 'sourceAsset',"
                    " set the 'info:mdl:sourceAsset' attribute to the value held by the 'module' attribute"
                    " and set the 'info:mdl:sourceAsset:subIdentifier' to the value held by the 'name' attribute."
                    " If the 'module' and/or 'name' attributes do not exist, or they are not of the expected types the shader"
                    " will not be fixed and a warning issued.",
                ),
            )
