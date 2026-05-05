# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import pathlib
import tempfile
import unittest

from common import AsyncioValidationTestCase, get_url
from pxr import Sdf, Usd

from nvidia_usd_validation import (
    LayerId,
    LayerSpecChecker,
    UsdAsciiPerformanceChecker,
    ValidationEngine,
)
from nvidia_usd_validation.tests import IsAFailure


class LayerSpecCheckerTest(AsyncioValidationTestCase):
    async def test_attribute_specs(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            """Creates content violates the following rules in the Layer Validation Specification
            - C0/R2: All attribute spec type names should conform to SdfValueTypeNames
            - C0/R3: All attribute default and time sample values should match the underlying type names
            """
            usdc_file_path = os.path.join(temp_folder, "test.usd")
            stage: Usd.Stage = Usd.Stage.CreateNew(usdc_file_path)
            prim: Usd.Prim = stage.DefinePrim("/prim")
            attribute: Usd.Attribute = prim.CreateAttribute("unknownTypename", Sdf.ValueTypeNames.String, False)
            attribute_spec: Sdf.AttributeSpec = stage.GetRootLayer().GetPropertyAtPath(attribute.GetPath())

            # Fake an invalid type to fail validator.
            attribute_spec.SetInfo("typeName", "invalid")

            # Fake an attribute that its ypename and value type don't match.
            attribute: Usd.Attribute = prim.CreateAttribute("typeMismatch", Sdf.ValueTypeNames.String, False)
            attribute.Set("value")
            attribute.SetTypeName(Sdf.ValueTypeNames.Int)

            # Fake an attribute that its timesamples contain sample that has different value type as the property's typeName.
            attribute: Usd.Attribute = prim.CreateAttribute(
                "typeMismatchForTimesample", Sdf.ValueTypeNames.Double, False
            )
            for t in range(0, 15):
                attribute.Set(t, t)

            attribute.SetTypeName(Sdf.ValueTypeNames.String)
            attribute.Set("invalid", 5)
            attribute.SetTypeName(Sdf.ValueTypeNames.Double)

            # Over 5 errors
            for t in range(10, 15):
                attribute.SetTypeName(Sdf.ValueTypeNames.String)
                attribute.Set("invalid", t)
                attribute.SetTypeName(Sdf.ValueTypeNames.Double)

            # Fake an attribute with token as its typename and assign a string value won't fail validator.
            attribute: Usd.Attribute = prim.CreateAttribute("stringToString", Sdf.ValueTypeNames.Token, False)
            attribute.Set("value")

            # Fake an attribute with float as its typename and assign a double value won't fail validator.
            attribute: Usd.Attribute = prim.CreateAttribute("doubleToFloat", Sdf.ValueTypeNames.Float, False)
            attribute.Set(1.0)

            # Fake an attribute with invalid value type
            attribute: Usd.Attribute = prim.CreateAttribute("unknownValueType", Sdf.ValueTypeNames.Int, False)
            attribute_spec: Sdf.AttributeSpec = stage.GetRootLayer().GetPropertyAtPath(attribute.GetPath())
            attribute_spec.SetInfo("default", Sdf.SpecifierDef)

            stage.Save()
            stage = None

            asset_url = LayerId(identifier=get_url(usdc_file_path)).identifier
            await self.assertRuleAsync(
                asset=asset_url,
                rule=LayerSpecChecker,
                asserts=[
                    IsAFailure(
                        "Unregistered type (invalid) found for property spec.",
                        at=f"Sdf.Find('{asset_url}', '/prim.unknownTypename')",
                    ),
                    IsAFailure(
                        "Property's type (int) and its value type (string) doesn't match.",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatch')",
                    ),
                    IsAFailure(
                        "Value type (string) of timesample at timecode 5.0 doesn't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Value type (string) of timesample at timecode 10.0 doesn't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Value type (string) of timesample at timecode 11.0 doesn't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Value type (string) of timesample at timecode 12.0 doesn't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Value type (string) of timesample at timecode 13.0 doesn't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Over 5 errors found for timesample values that don't match property type (double).",
                        at=f"Sdf.Find('{asset_url}', '/prim.typeMismatchForTimesample')",
                    ),
                    IsAFailure(
                        "Unknown type found for value of property spec.",
                        at=f"Sdf.Find('{asset_url}', '/prim.unknownValueType')",
                    ),
                ],
            )

    @unittest.skipIf(Usd.GetVersion() >= (0, 24, 11), "Tests disabled because PEGTL will not load this invalid format")
    async def test_relationship_specs(self):
        asset_url = LayerId(identifier=get_url("sdfRelationshipSpec.usda")).identifier

        await self.assertRuleAsync(
            asset=asset_url,
            rule=LayerSpecChecker,
            asserts=[
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.emptyTimesamplesWithDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.singleTimesampleWithDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.multipleTimesamplesWithDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.differentTimesamplesWithDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.emptyTimesamplesWithoutDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.singleTimesampleWithoutDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying.",
                    at=f"Sdf.Find('{asset_url}', '/prim.multipleTimesamplesWithoutDefault')",
                ),
                IsAFailure(
                    "Relationship spec should not be time varying (with 2 samples).",
                    at=f"Sdf.Find('{asset_url}', '/prim.differentTimesamplesWithoutDefault')",
                ),
            ],
        )

    async def test_unsupported_fields(self):
        asset_url = LayerId(identifier=get_url("sdfSpecFields.usda")).identifier

        expected_failures = []
        for spec_path in ["/prim.relationship", "/prim.attribute", "/prim"]:
            for field in LayerSpecChecker._UNSUPPORTED_FIELDS:
                expected_failures.append(
                    IsAFailure(f"Unsupported field ({field}) found.", at=f"Sdf.Find('{asset_url}', '{spec_path}')"),
                )

        await self.assertRuleAsync(asset=asset_url, rule=LayerSpecChecker, asserts=expected_failures)


class UsdAsciiPerformanceCheckerTest(AsyncioValidationTestCase):
    async def test_pass(self):
        """Verify layers without large numbers of time samples and array lengths pass."""
        await self.assertRuleAsync(
            asset=get_url("usdaPerformancePass.usda"),
            rule=UsdAsciiPerformanceChecker,
            asserts=[],
        )

    async def test_failure(self):
        """Verify layers with large numbers of time samples and array lengths are flagged."""
        await self.assertRuleAsync(
            asset=get_url("usdaPerformanceFail.usda"),
            rule=UsdAsciiPerformanceChecker,
            asserts=[
                IsAFailure(r"2 attribute\(s\) in '.+' have large numbers of time samples"),
                IsAFailure(r"1 attribute\(s\) in '.+' have large array lengths"),
            ],
        )

    async def test_underlying_ascii_failure(self):
        """Copy the layer to a .usd layer with ASCII contents and verify the rule still fails."""
        source = Sdf.Layer.FindOrOpen(get_url("usdaPerformanceFail.usda"))
        with tempfile.TemporaryDirectory() as directory:
            ascii_underlying_layer = Sdf.Layer.CreateNew(
                str(pathlib.Path(directory) / "underlying_ascii.usd"), args={"format": "usda"}
            )
            ascii_underlying_layer.TransferContent(source)
            await self.assertRuleAsync(
                asset=ascii_underlying_layer.identifier,
                rule=UsdAsciiPerformanceChecker,
                asserts=[
                    IsAFailure(r"2 attribute\(s\) in '.+' have large numbers of time samples"),
                    IsAFailure(r"1 attribute\(s\) in '.+' have large array lengths"),
                ],
            )

    async def test_underlying_crate_pass(self):
        """Copy the layer to a .usd layer with crate contents and verify the rule passes."""
        source = Sdf.Layer.FindOrOpen(get_url("usdaPerformanceFail.usda"))
        with tempfile.TemporaryDirectory() as directory:
            crate_underlying_layer = Sdf.Layer.CreateNew(
                str(pathlib.Path(directory) / "underlying_crate.usd"), args={"format": "usdc"}
            )
            crate_underlying_layer.TransferContent(source)
            await self.assertRuleAsync(
                asset=crate_underlying_layer.identifier,
                rule=UsdAsciiPerformanceChecker,
                asserts=[],
            )

    async def test_anonymous_layer(self):
        """Verify anonymous layer with large numbers of time samples and array lengths pass."""
        anonymous_stage = Usd.Stage.CreateInMemory()
        anonymous_layer = anonymous_stage.GetRootLayer()
        source = Sdf.Layer.FindOrOpen(get_url("usdaPerformanceFail.usda"))
        anonymous_layer.TransferContent(source)

        # Source layer should fail
        await self.assertRuleAsync(
            asset=get_url("usdaPerformanceFail.usda"),
            rule=UsdAsciiPerformanceChecker,
            asserts=[
                IsAFailure(r"2 attribute\(s\) in '.+' have large numbers of time samples"),
                IsAFailure(r"1 attribute\(s\) in '.+' have large array lengths"),
            ],
        )

        # Anonymous layer - no failures
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(UsdAsciiPerformanceChecker)

        result = engine.validate(anonymous_stage)
        self.assertEqual(0, len(result.issues()))
