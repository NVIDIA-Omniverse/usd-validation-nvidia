# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

import nvidia_usd_validation.capabilities as cap
from common import AsyncioValidationTestCase, get_url
from nvidia_usd_validation import (
    GaussianSplatSchemaChecker,
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
)
from nvidia_usd_validation.tests import IsAFailure, IsAnError, IsAWarning
from pxr import Sdf, Usd


class SubdivisionSchemeCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneHasNormals.usda"),
            rule=SubdivisionSchemeChecker,
            asserts=[],
        )

        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneNoNormals.usda"),
            rule=SubdivisionSchemeChecker,
            asserts=[],
        )

        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedHasNormals.usda"),
            rule=SubdivisionSchemeChecker,
            asserts=[
                IsAFailure("Subdivision scheme is not set. There are normals on the mesh. "),
            ],
        )

        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedNoNormals.usda"),
            rule=SubdivisionSchemeChecker,
            asserts=[
                IsAFailure("Subdivision scheme is not set. There are no normals on the mesh. "),
            ],
        )

    async def test_fix(self):
        await self.assertSuggestionAsync(
            asset=get_url("subdivisionUndefinedHasNormals.usda"),
            rule=SubdivisionSchemeChecker,
            predicate=None,
        )


class ManifoldCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryManifold.usda"),
            rule=ManifoldChecker,
            asserts=[
                IsAWarning("The face winding is not consistent.", at=Sdf.Path("/root/Quad_2")),
                IsAWarning("1 edges are non-manifold.", at=Sdf.Path("/root/Quad_3")),
                IsAWarning("1 vertices are non-manifold.", at=Sdf.Path("/root/Quad_4")),
                IsAWarning("1 vertices are non-manifold.", at=Sdf.Path("/root/Quad_7")),
            ],
        )


class IndexedPrimvarCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryPrimvars.usda"),
            rule=IndexedPrimvarChecker,
            asserts=[
                IsAnError("Primvar indices out of bounds", at=Sdf.Path("/root/Quad_1.primvars:testing")),
                IsAnError("Primvar is not of array type.", at=Sdf.Path("/root/Quad_2.primvars:testing")),
                IsAWarning(
                    "primvars:testing contains repeated values that can be indexed.",
                    at=Sdf.Path("/root/Quad_3.primvars:testing"),
                ),
                IsAnError("Primvar indices out of bounds", at=Sdf.Path("/root/Quad_10.primvars:testing")),
            ],
        )


class UnusedMeshTopologyCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryFail.usda"),
            rule=UnusedMeshTopologyChecker,
            asserts=[
                IsAFailure("Some points are not referenced by the faces."),
                IsAFailure("Some points are not referenced by the faces."),
            ],
        )

    async def test_fix(self):
        await self.assertSuggestionAsync(
            asset=get_url("Geometry/geometryFail.usda"),
            rule=UnusedMeshTopologyChecker,
            predicate=None,
        )

    async def test_failures_without_fix(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryNoFix.usda"),
            rule=UnusedMeshTopologyChecker,
            asserts=[
                IsAFailure(
                    "Some points are not referenced by the faces (but it cannot be fixed"
                    " automatically as it has primvars that are vertex or varying interpolated"
                    " and time varying)."
                ),
                IsAFailure(
                    "Some points are not referenced by the faces (but it cannot be fixed"
                    " automatically as it has primvars that are vertex or varying interpolated"
                    " and time varying)."
                ),
                IsAFailure(
                    "Some points are not referenced by the faces (but it cannot be fixed"
                    " automatically as it has primvars that are vertex or varying interpolated"
                    " and time varying)."
                ),
            ],
        )


class ZeroAreaFaceCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryFail.usda"),
            rule=ZeroAreaFaceChecker,
            asserts=[
                IsAWarning("The mesh contains zero area faces."),
                IsAWarning("The mesh contains zero area faces."),
            ],
        )


class WeldCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryFail.usda"),
            rule=WeldChecker,
            asserts=[
                IsAWarning("Some points are co-located and may be able to be merged."),
            ],
        )

    async def test_validate_stage(self):
        stage = Usd.Stage.Open(get_url("Geometry/geometryFail.usda"))
        await self.assertRuleAsync(
            asset=stage,
            rule=WeldChecker,
            asserts=[
                IsAWarning("Some points are co-located and may be able to be merged."),
            ],
        )

    async def test_validate_vertex_incomplete(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/weldableIncomplete.usda"),
            rule=WeldChecker,
            asserts=[
                IsAFailure(
                    "Attribute (/root/Quad_1.normals) values length does not match points length although its interpolation is vertex or varying.",
                    at=Sdf.Path("/root/Quad_1"),
                ),
                IsAFailure(
                    "Primvar (/root/Quad_2.primvars:st) values length does not match points length although its interpolation is vertex or varying.",
                    at=Sdf.Path("/root/Quad_2"),
                ),
            ],
        )


class ValidateTopologyCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryTopology.usda"),
            rule=ValidateTopologyChecker,
            asserts=[
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_1")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_2")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_3")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_4")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_5")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_6")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_7")),
                IsAFailure("Invalid topology found", at=Sdf.Path("/root/Quad_10")),
            ],
        )


class UnusedPrimvarCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryPrimvars.usda"),
            rule=UnusedPrimvarChecker,
            asserts=[
                IsAWarning(
                    "primvars:testing contains invalid indices that are above the number of values.",
                    at=Sdf.Path("/root/Quad_1.primvars:testing"),
                ),
                IsAWarning(
                    "primvars:testing contains values not referenced by its indices.",
                    at=Sdf.Path("/root/Quad_5.primvars:testing"),
                ),
                IsAWarning(
                    "primvars:testing contains invalid indices that are above the number of values.",
                    at=Sdf.Path("/root/Quad_10.primvars:testing"),
                ),
            ],
        )

    async def test_fix(self):
        await self.assertSuggestionAsync(
            asset=get_url("Geometry/geometryPrimvars.usda"),
            rule=UnusedPrimvarChecker,
            predicate=None,
        )

    async def test_fix_stage(self):
        stage: Usd.Stage = Usd.Stage.Open(get_url("Geometry/geometryPrimvars.usda"))
        await self.assertSuggestionAsync(
            asset=stage,
            rule=UnusedPrimvarChecker,
            predicate=None,
        )


class NormalsExistCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        # Both normals and primvars normals are set. Fail since only one should be present
        await self.assertRuleAsync(
            asset=get_url("Geometry/planeWithNormalsAndPrimvarNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[
                IsAFailure("Both normals and primvar:normals exist. Only one set of normals should be present."),
            ],
        )

        # Subdivision is None. Has normals. Pass.
        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneHasNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[],
        )

        # Subdivision is None. No normals. Pass since subdiv is valid even though no normals
        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneNoNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[
                IsAFailure("Either normals should be authored or subdivision should be set"),
            ],
        )

        # Subdivision is Catmull-Clark. Has normals. Fail - can't have both
        await self.assertRuleAsync(
            asset=get_url("subdivisionCatmullHasNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[
                IsAFailure("Normals are defined but subdivision mesh also has normals"),
            ],
        )

        # Subdivision is Catmull-Clark. No normals. Pass
        await self.assertRuleAsync(
            asset=get_url("subdivisionCatmullNoNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[],
        )

        # Subdivision is undefined. Defaults to Catmull Clark. Has
        # normals. Fail because want explicit subdiv scheme defined
        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedHasNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[
                IsAFailure("Normals are defined but subdivision mesh also has normals"),
            ],
        )

        # Subdivision is undefined. Defaults to Catmull Clark. No normals. Pass.
        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedNoNormals.usda"),
            rule=NormalsExistChecker,
            asserts=[],
        )

    async def test_fix(self):
        await self.assertSuggestionAsync(
            asset=get_url("Geometry/planeWithNormalsAndPrimvarNormals.usda"),
            rule=NormalsExistChecker,
            predicate=None,
        )
        await self.assertSuggestionAsync(
            asset=get_url("subdivisionUndefinedHasNormals.usda"),
            rule=NormalsExistChecker,
            predicate=None,
        )
        await self.assertSuggestionAsync(
            asset=get_url("subdivisionCatmullHasNormals.usda"),
            rule=NormalsExistChecker,
            predicate=None,
        )
        # subdivisionNoneNoNormals fails but has no suggested fix since user must decide


class NormalsValidCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        # Both normals and primvars normals are set. Fail since only one should be present
        await self.assertRuleAsync(
            asset=get_url("Geometry/planeWithNormalsAndPrimvarNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[
                IsAFailure("Mesh '/pPlane3' normals have 7 elements but expected 8 for 'faceVarying' interpolation."),
            ],
        )

        # Subdivision is None. Has normals. Pass.
        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneHasNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[],
        )

        # Subdivision is None. No normals. Pass.
        await self.assertRuleAsync(
            asset=get_url("subdivisionNoneNoNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[],
        )

        # Subdivision is Catmull-Clark. Has normals. Fail - can't have both
        await self.assertRuleAsync(
            asset=get_url("subdivisionCatmullHasNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[
                IsAFailure(
                    "Mesh '/World/Cube' is subdiv ('catmullClark') but has authored normals; USD recommends not authoring normals on subdiv meshes."
                ),
            ],
        )
        # Subdivision is Catmull-Clark. No normals. Pass
        await self.assertRuleAsync(
            asset=get_url("subdivisionCatmullNoNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[],
        )

        # Subdivision is undefined. Defaults to Catmull Clark. Has
        # normals. Fail because want explicit subdiv scheme defined
        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedHasNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[
                IsAFailure(
                    "Mesh '/World/Cube' is subdiv ('catmullClark') but has authored normals; USD recommends not authoring normals on subdiv meshes."
                ),
            ],
        )

        # Subdivision is undefined. Defaults to Catmull Clark. No normals. Pass.
        await self.assertRuleAsync(
            asset=get_url("subdivisionUndefinedNoNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[],
        )

        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryInvalidNormals.usda"),
            rule=NormalsValidChecker,
            asserts=[
                IsAnError("Mesh '/root/Quad_0' has non-finite normal components."),
                IsAWarning("Mesh '/root/Quad_1' has non-unit normal (length=1.414214)."),
                IsAnError("Mesh '/root/Quad_2' has non-finite normal components."),
                IsAWarning("Mesh '/root/Quad_3' has non-unit normal (length=1.414214)."),
                IsAWarning("Mesh '/root/Quad_4' has non-unit normal (length=177.000000)."),
                IsAWarning("Mesh '/root/Quad_6' has non-unit normal (length=77.006493)."),
                IsAnError("Mesh '/root/Quad_7' has non-finite normal components."),
                IsAWarning("Mesh '/root/Quad_8' has non-unit normal (length=1.414214)."),
                IsAnError("Mesh '/root/Quad_9' has non-finite normal components."),
                IsAWarning("Mesh '/root/Quad_10' has non-unit normal (length=3.162278)."),
            ],
        )


class NormalsWindingsCheckerTest(AsyncioValidationTestCase):
    async def test_validate(self):
        # Both normals and primvars normals are set. Fail since only one should be present
        await self.assertRuleAsync(
            asset=get_url("Geometry/geometryWindings.usda"),
            rule=NormalsWindingsChecker,
            asserts=[
                IsAnError("Mesh '/World/reversedDefaultOrientation' has normals inconsistent with the face windings."),
                IsAnError(
                    "Mesh '/World/reversedIndexedDefaultOrientation' has normals inconsistent with the face windings."
                ),
                IsAnError(
                    "Mesh '/World/reversedRightHandOrientation' has normals inconsistent with the face windings."
                ),
                IsAnError("Mesh '/World/reversedPerVertex' has normals inconsistent with the face windings."),
                IsAnError("Mesh '/World/perVertexNormalsLeftHanded' has normals inconsistent with the face windings."),
            ],
        )


@unittest.skipUnless(
    GaussianSplatSchemaChecker.is_implemented(), "OpenUSD 26.03+ required for VG.035 / GaussianSplatSchemaChecker"
)
class GaussianSplatSchemaCheckerTest(AsyncioValidationTestCase):

    async def test_validate(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.VG_035)


class ContainsMeshCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.VG_MESH_001)


class AssetOriginPositioningCheckerTest(AsyncioValidationTestCase):

    async def test_validate_ok(self):
        await self.assertExamplesAsync(requirement=cap.Requirements.VG_025)

    async def test_fix_ok(self):
        await self.assertExamplesSuggestionsAsync(requirement=cap.Requirements.VG_025)
