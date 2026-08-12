# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import enum

from pxr import Sdf, Usd

from .._base_rule_checker import BaseRuleChecker
from .._categories import register_rule
from .._issues import Suggestion
from ..utils import multiprocess_safe

__all__ = [
    "LayerSpecChecker",
    "UsdAsciiPerformanceChecker",
]


@register_rule("Layer")
class LayerSpecChecker(BaseRuleChecker):
    """
    This checker validates all LayerSpecs to ensure their type names and values types conform to SdfValueTypeNames.
    Also, their value types (including timesamples) should match the underlying type names.
    """

    _UNSUPPORTED_FIELDS = [
        Sdf.PrimSpec.PermissionKey,
        Sdf.PrimSpec.SymmetricPeerKey,
        Sdf.PrimSpec.SymmetryArgumentsKey,
        Sdf.PrimSpec.SymmetryFunctionKey,
        Sdf.PrimSpec.PrefixKey,
        "suffix",
    ]

    _TIMESAMPLES_TOKEN = "timeSamples"

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    @staticmethod
    def _should_skip_validate_types(property_type_name: Sdf.ValueTypeName, value_type: Sdf.ValueTypeName):
        # VtValue's automatically unpack in python and tokens automatically convert to strings in python.
        # So it cannot validate value type in Sdf.ValueTypeNames.String with property type in Sdf.ValueTypeNames.Token.
        if value_type == Sdf.ValueTypeNames.String and property_type_name == Sdf.ValueTypeNames.Token:
            return True

        # The same for double/float types.
        if value_type == Sdf.ValueTypeNames.Double and property_type_name == Sdf.ValueTypeNames.Float:
            return True

        skip_types = [
            Sdf.ValueTypeNames.UChar,
            Sdf.ValueTypeNames.Int,
            Sdf.ValueTypeNames.Int64,
            Sdf.ValueTypeNames.UInt,
            Sdf.ValueTypeNames.UInt64,
        ]
        if value_type == Sdf.ValueTypeNames.Int and property_type_name in skip_types:
            return True

        return False

    @classmethod
    def fix_unsupported_fields_callback(cls, stage: Usd.Stage, spec: Sdf.Spec) -> None:
        for field in cls._UNSUPPORTED_FIELDS:
            if spec.HasInfo(field):
                spec.ClearInfo(field)

    @classmethod
    def fix_timesamples_callback(cls, stage: Usd.Stage, spec: Sdf.Spec) -> None:
        if spec.HasInfo(cls._TIMESAMPLES_TOKEN):
            spec.ClearInfo(cls._TIMESAMPLES_TOKEN)

    @staticmethod
    def fix_time_varying_relationship_callback(stage: Usd.Stage, spec: Sdf.AttributeSpec) -> None:
        timesamples = spec.GetInfo(LayerSpecChecker._TIMESAMPLES_TOKEN)
        if not timesamples:
            return

        value = next(iter(timesamples.values()))
        if not value:
            return

        value_list = value if isinstance(value, list) else [value]
        filtered_values = []
        for item in value_list:
            if not isinstance(item, Sdf.Path):
                continue

            filtered_values.append(item)

        target_path_list: Sdf.PathListOp = spec.targetPathList
        target_path_list.ClearEditsAndMakeExplicit()
        target_path_list.explicitItems = filtered_values

        # Clears timesamples after making the first sample as default targetPaths.
        spec.ClearInfo(LayerSpecChecker._TIMESAMPLES_TOKEN)

    def _validate_metadata_fields(self, spec: Sdf.Spec):
        """Validates the following rules in the Layer Validation Specification
        - C0: Layer content is internally consistent
         - R5: Fields for unsupported features should not be specified
        """

        # Checks unsupported fields firstly.
        for unsupported_field in LayerSpecChecker._UNSUPPORTED_FIELDS:
            if spec.HasInfo(unsupported_field):
                self._AddFailedCheck(
                    f"Unsupported field ({unsupported_field}) found.",
                    at=spec,
                    suggestion=Suggestion(
                        callable=self.fix_unsupported_fields_callback,
                        message="Remove unsupported fields from spec.",
                    ),
                )

    def _validate_relationship_spec(self, spec: Sdf.RelationshipSpec):
        """Validates the following rules in the Layer Validation Specification
        - C0: Layer content is internally consistent
         - R4: Relationships should not be time varying
        """

        # For relationship spec, timesamples are not allowed.
        if spec.HasInfo(self._TIMESAMPLES_TOKEN):
            timesamples: dict = spec.GetInfo(self._TIMESAMPLES_TOKEN)
            timesample_values = list(timesamples.values())
            count = len(timesample_values)
            # No samples present, or only one timesample presents but its value is empty
            # or default relationship presents already.
            if count == 0 or (count == 1 and not timesample_values[0]) or spec.HasInfo("targetPaths"):
                self._AddFailedCheck(
                    "Relationship spec should not be time varying.",
                    at=spec,
                    suggestion=Suggestion(
                        callable=self.fix_timesamples_callback,
                        message="Remove timesamples.",
                    ),
                )
            else:
                value = timesample_values[0]
                # All samples have the same value
                if value and all([item == value for item in timesample_values]):
                    self._AddFailedCheck(
                        "Relationship spec should not be time varying.",
                        at=spec,
                        suggestion=Suggestion(
                            callable=self.fix_time_varying_relationship_callback,
                            message="Convert time varying relationship into default relationship.",
                        ),
                    )
                else:
                    # Otherwise, we report error only without suggestion.
                    self._AddFailedCheck(
                        f"Relationship spec should not be time varying (with {count} samples).", at=spec
                    )

    def _validate_attribute_spec(self, spec: Sdf.AttributeSpec):
        """Validates the following rules in the Layer Validation Specification
        - C0: Layer content is internally consistent
         - R2: All attribute spec type names should conform to SdfValueTypeNames
         - R3: All attribute default and time sample values should match the underlying type names
        """

        # For attribute spec, it needs to ensure their type names and values types conform to SdfValueTypeNames.
        # Also, their value types (including timesamples) should match the underlying type names
        if not Sdf.ValueTypeNames.Find(str(spec.typeName)):
            self._AddFailedCheck(f"Unregistered type ({spec.typeName}) found for property spec.", at=spec)
        elif spec.default is not None and spec.default != Sdf.ValueBlock():
            value_type: Sdf.ValueTypeName = Sdf.GetValueTypeNameForValue(spec.default)
            if not value_type:
                self._AddFailedCheck("Unknown type found for value of property spec.", at=spec)
            elif (
                not self._should_skip_validate_types(spec.typeName, value_type)
                and spec.typeName.type != value_type.type
            ):
                self._AddFailedCheck(
                    f"Property's type ({spec.typeName}) and its value type ({value_type}) doesn't match.", at=spec
                )

        if spec.HasInfo(self._TIMESAMPLES_TOKEN):
            timesamples_map = spec.GetInfo(self._TIMESAMPLES_TOKEN)
            maximum_errors = 5
            count = 0
            for time_code, value in timesamples_map.items():
                timesample_value_type: Sdf.ValueTypeName = Sdf.GetValueTypeNameForValue(value)
                if (
                    value != Sdf.ValueBlock()
                    and not self._should_skip_validate_types(spec.typeName, timesample_value_type)
                    and timesample_value_type.type != spec.typeName.type
                ):
                    if count < maximum_errors:
                        self._AddFailedCheck(
                            f"Value type ({timesample_value_type}) of timesample at timecode {time_code} "
                            f"doesn't match property type ({spec.typeName}).",
                            at=spec,
                        )

                    count += 1

                if count > maximum_errors:
                    break

            if count > maximum_errors:
                self._AddFailedCheck(
                    f"Over {maximum_errors} errors found for timesample values that don't match property type ({spec.typeName}).",
                    at=spec,
                )

    @multiprocess_safe
    def CheckLayer(self, layer: Sdf.Layer):
        def on_prim_spec_path(spec_path: Sdf.Path):
            spec = layer.GetObjectAtPath(spec_path)
            if not spec:
                return

            self._validate_metadata_fields(spec)

            if not spec_path.IsPropertyPath():
                return

            spec: Sdf.PropertySpec = layer.GetPropertyAtPath(spec_path)
            if isinstance(spec, Sdf.RelationshipSpec):
                self._validate_relationship_spec(spec)

                return

            self._validate_attribute_spec(spec)

        layer.Traverse(Sdf.Path.absoluteRootPath, on_prim_spec_path)


def _TraverseDescendents(prim_spec: Sdf.PrimSpec):
    for child_prim_spec in prim_spec.nameChildren:
        yield child_prim_spec
        yield from _TraverseDescendents(child_prim_spec)


class _UsdaLayerType(enum.Enum):
    Explicit = 0  # .usda layers
    Underlying = 1  # .usd layers whose contents are ASCII


@register_rule("Layer")
class UsdAsciiPerformanceChecker(BaseRuleChecker):
    """For performance reasons, large arrays and time samples are better stored in
    crate files. This alerts users to any layers which contain large arrays or time sample
    dictionaries stored in .usda or ASCII backed .usd files."""

    # It's not uncommon for single unchanging values to be authored to the time sample
    # dictionary. Only flag time samples exceeding a relatively small threshold as
    # potential performance issues.
    _TIME_SAMPLE_LIMIT = 4
    # It's not uncommon for values which may be constant or varying over the topology
    # of a surface (primvars) to be authored as array types. Only flag array values
    # greater than a relatively small threshold as potential performance issues.
    _ARRAY_LENGTH_LIMIT = 64

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def _GetUsdaLayerType(self, layer: Sdf.Layer) -> _UsdaLayerType | None:
        """Returns if the layer contents was authored as USDA either explicitly or indirectly."""
        file_format = layer.GetFileFormat()
        if file_format == Sdf.FileFormat.FindById("usda"):
            return _UsdaLayerType.Explicit
        if file_format in (Sdf.FileFormat.FindById("usd"), Sdf.FileFormat.FindById("omni")):
            if Sdf.FileFormat.FindById("usda").CanRead(layer.identifier):
                return _UsdaLayerType.Underlying
        return None

    def _ValueExceedsArrayLengthLimit(self, value) -> bool:
        if value == Sdf.ValueBlock():
            return False
        return len(value) > self._ARRAY_LENGTH_LIMIT

    def CheckLayer(self, layer: Sdf.Layer):
        """Verify the contents of the the ASCII layer won't create performance issues."""

        # The file format of anonymous layers could be tagged as ASCII
        # We don't validate anonymous layers
        if layer.anonymous:
            return

        usda_layer_type = self._GetUsdaLayerType(layer)
        if not usda_layer_type:
            return

        large_time_sample_specs = []
        long_array_value_specs = []

        for prim_spec in _TraverseDescendents(layer.GetPrimAtPath(Sdf.Path.absoluteRootPath)):
            for attribute_spec in prim_spec.attributes:
                # Prefer storing attributes with large time sample dictionaries in USDC
                if layer.GetNumTimeSamplesForPath(attribute_spec.path) > self._TIME_SAMPLE_LIMIT:
                    large_time_sample_specs.append(attribute_spec)
                # Prefer storing long array valued attributes in USDC
                elif attribute_spec.typeName.isArray:
                    if attribute_spec.HasDefaultValue() and self._ValueExceedsArrayLengthLimit(attribute_spec.default):
                        long_array_value_specs.append(attribute_spec)
                    else:
                        if any(
                            self._ValueExceedsArrayLengthLimit(layer.QueryTimeSample(attribute_spec.path, time))
                            for time in layer.ListTimeSamplesForPath(attribute_spec.path)
                        ):
                            long_array_value_specs.append(attribute_spec)
        if large_time_sample_specs:
            self._AddFailedCheck(
                f"{len(large_time_sample_specs)} attribute(s) in '{layer.identifier}' have large numbers "
                "of time samples and should be stored in crate files for improved performance. usdcat can be used to "
                "convert .usd files containing ASCII to crate in place or .usda files to crate stored in .usdc or "
                ".usd.",
            )
        if long_array_value_specs:
            self._AddFailedCheck(
                f"{len(long_array_value_specs)} attribute(s) in '{layer.identifier}' have large array "
                "lengths and should be stored in crate files for improved performance. usdcat can be used to convert "
                ".usd files containing ASCII to crate in place or .usda files to crate stored in .usdc or .usd.",
            )
