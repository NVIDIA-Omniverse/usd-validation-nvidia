# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import math
from collections.abc import Iterator

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

import usd_validation_nvidia.capabilities as cap

from ._base_rule_checker import BaseRuleChecker
from ._categories import register_rule
from ._issues import Suggestion
from ._mesh_tools import (
    check_manifold_elements,
    compute_winding_bias,
    has_empty_faces,
    has_indexable_values,
    has_invalid_indices,
    has_invalid_primvar_indices,
    has_unreferenced_primvar,
    has_unreferenced_values,
    has_weldable_points,
    is_typename_array,
    remove_unused_values_and_remap_indices,
)
from ._requirements import register_requirements

__all__ = [
    "IndexedPrimvarChecker",
    "ManifoldChecker",
    "NormalsExistChecker",
    "NormalsValidChecker",
    "NormalsWindingsChecker",
    "SubdivisionSchemeChecker",
    "UnusedMeshTopologyChecker",
    "UnusedPrimvarChecker",
    "ValidateTopologyChecker",
    "WeldChecker",
    "ZeroAreaFaceChecker",
]


def _get_normals_source(mesh: UsdGeom.Mesh, time: Usd.TimeCode = None):
    """Return a tuple describing the effective normals source:

    interp: interpolation token string
    values: sequence of GfVec3f
    count_for_topology_check: integer (values count or indices count)
    value_attr_or_primvar: the UsdAttribute/UsdGeomPrimvar object (for time checks)
    is_indexed: if the primvar was indexed
    indices: the indices for the primvar
    """

    if time is None:
        time = Usd.TimeCode.EarliestTime()

    prim = mesh.GetPrim()
    pvars = UsdGeom.PrimvarsAPI(prim)
    pv = pvars.GetPrimvar("normals")
    if pv and pv.HasValue():
        interp = pv.GetInterpolation()
        values = pv.Get(time) or []
        # If indexed, the count applies to the indices array, not the values array.
        idx = []
        if pv.IsIndexed():
            idx = pv.GetIndices(time) or []
            topo_count = len(idx)
        else:
            topo_count = len(values)
        return (interp, values, topo_count, pv, pv.IsIndexed(), idx)

    # Fallback to the built-in attribute
    attr = mesh.GetNormalsAttr()
    if attr and attr.HasValue():
        values = attr.Get(time) or []
        interp = mesh.GetNormalsInterpolation()
        return (interp, values, len(values), attr, False, [])

    return None


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_010)
class SubdivisionSchemeChecker(BaseRuleChecker):
    """

    USD default value for subdivision scheme is Catmull-Clark. This is
    often overlooked and so set incorrectly for tessellated CAD geometry.

    This checker ensures that the subdivision scheme is explicitly
    defined. When it is defined, there is a choice between using
    subdivision or not.

    Use the presence of normals to decide what to suggest as a fixer
    operation.  If there are explicit normals, offer an option to
    disable subdivision to avoid overwriting these normals. If there
    are no normals, offer the option to enable subdivision so that
    normals are created.

    Note that these choices are not always going to be the right ones,
    but they are reasonable defaults.

    """

    @classmethod
    def set_to_none(cls, _: Usd.Stage, mesh: UsdGeom.Mesh) -> None:
        """Sets subdivision scheme to None"""
        mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)

    @classmethod
    def set_to_catmull_clark(cls, _: Usd.Stage, mesh: UsdGeom.Mesh) -> None:
        """Sets subdivision scheme to Catmull-Clark."""
        mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.catmullClark)

    def _validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        # Normals may be defined via attribute or via primvar.
        normals_attr: Usd.Attribute = mesh.GetNormalsAttr()
        primvar_api: UsdGeom.PrimvarsAPI = UsdGeom.PrimvarsAPI(mesh)
        primvar: UsdGeom.Primvar = primvar_api.GetPrimvar(UsdGeom.Tokens.normals)
        has_normals: bool = normals_attr.HasAuthoredValue() or primvar.HasAuthoredValue()

        # Get the subdivision attribute
        attr: Usd.Attribute = mesh.GetSubdivisionSchemeAttr()
        if not attr.HasAuthoredValue() and not has_normals:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_010,
                message="Subdivision scheme is not set. There are no normals on the mesh. "
                "Setting subdivision scheme to Catmull-Clark will render a smoothed surface.",
                at=mesh,
                suggestion=Suggestion(
                    message="Set subdivision scheme to Catmull-Clark",
                    callable=self.set_to_catmull_clark,
                    at=attr,
                ),
            )
        elif not attr.HasAuthoredValue() and has_normals:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_010,
                message="Subdivision scheme is not set. There are normals on the mesh. "
                "Setting subdivision scheme to None will ensure normals are not overridden.",
                at=mesh,
                suggestion=Suggestion(
                    message="Set subdivision scheme to None",
                    callable=self.set_to_none,
                    at=attr,
                ),
            )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            self._validate_mesh(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_007)
class ManifoldChecker(BaseRuleChecker):
    """
    Counts the number of non-manifold edges and vertices. A non-manifold edge has more than two adjacent faces. A
    non-manifold vertex as more than two adjacent border edges, where a border edge is an edge with only one adjacent
    face.

    Works on non time varying geometry.
    """

    def _validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        points: Vt.Vec3fArray | None = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime())
        num_points: int = len(points) if points else 0
        indices: Vt.IntArray = mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime())
        face_sizes: Vt.IntArray = mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime())

        if all((indices, face_sizes, num_points)):
            valid, _ = UsdGeom.Mesh.ValidateTopology(indices, face_sizes, num_points)
        else:
            valid = False
        if not valid:
            # Validated in ValidationTopologyChecker
            return

        num_non_manifold_vertices, num_non_manifold_edges, winding_consistent = check_manifold_elements(
            num_points, indices, face_sizes
        )

        if num_non_manifold_vertices > 0:
            self._AddWarning(
                requirement=cap.Requirements.VG_007,
                message=f"{num_non_manifold_vertices} vertices are non-manifold.",
                at=mesh,
            )
        if num_non_manifold_edges > 0:
            self._AddWarning(
                requirement=cap.Requirements.VG_007,
                message=f"{num_non_manifold_edges} edges are non-manifold.",
                at=mesh,
            )
        if not winding_consistent:
            self._AddWarning(
                requirement=cap.Requirements.VG_007,
                message="The face winding is not consistent.",
                at=mesh,
            )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            points_attr: Usd.Attribute = mesh.GetPointsAttr()
            has_static_points: bool = points_attr.IsAuthored() and not points_attr.ValueMightBeTimeVarying()
            if not has_static_points:
                return
            indices_attr: Usd.Attribute = mesh.GetFaceVertexIndicesAttr()
            has_static_indices: bool = indices_attr.IsAuthored() and not indices_attr.ValueMightBeTimeVarying()
            if not has_static_indices:
                return
            face_sizes_attr: Usd.Attribute = mesh.GetFaceVertexCountsAttr()
            has_static_faces: bool = face_sizes_attr.IsAuthored() and not face_sizes_attr.ValueMightBeTimeVarying()
            if not has_static_faces:
                return
            self._validate_mesh(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_009)
class IndexedPrimvarChecker(BaseRuleChecker):
    """
    For Primvars with non-constant values of interpolation, it is often the case that the same value is repeated many
    times in the array.

    An indexed primvar can be used in such cases to optimize for data storage if the primvar's interpolation is
    non-constant (i.e. uniform, varying, face varying or vertex).
    """

    def _validate_primvars(self, primvars_api: UsdGeom.PrimvarsAPI) -> None:
        for primvar in primvars_api.GetPrimvarsWithAuthoredValues():
            interpolation: Tf.Token = primvar.GetInterpolation()
            if interpolation == UsdGeom.Tokens.constant:
                continue
            try:
                if has_indexable_values(primvar):
                    self._AddWarning(
                        requirement=cap.Requirements.VG_009,
                        message=f"{primvar.GetName()} contains repeated values that can be indexed.",
                        at=primvar,
                    )
            except TypeError:
                self._AddError(
                    requirement=cap.Requirements.VG_009,
                    message="Primvar is not of array type.",
                    at=primvar,
                )
            except IndexError:
                self._AddError(
                    requirement=cap.Requirements.VG_009,
                    message="Primvar indices out of bounds",
                    at=primvar,
                )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        primvars_api: UsdGeom.PrimvarsAPI = UsdGeom.PrimvarsAPI(prim)
        if not primvars_api:
            return
        interpolations: set[Tf.Token] = set(
            map(UsdGeom.Primvar.GetInterpolation, primvars_api.GetPrimvarsWithAuthoredValues())
        )
        if not interpolations or interpolations == {UsdGeom.Tokens.constant}:
            return
        self._validate_primvars(primvars_api)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_018)
class UnusedMeshTopologyChecker(BaseRuleChecker):
    """
    Points which are not referenced by the indices can be removed.

    Works on non time varying geometry.
    """

    @staticmethod
    def _validate_mesh_points_indices(mesh: UsdGeom.Mesh):
        points: Vt.Vec3fArray = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime()) or Vt.Vec3fArray()
        num_points: int = len(points)
        indices: Vt.IntArray = mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime())
        face_sizes: Vt.IntArray = mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime())
        if all((indices, face_sizes, num_points)):
            valid, _ = UsdGeom.Mesh.ValidateTopology(indices, face_sizes, num_points)
        else:
            valid = False

        return valid, points, indices

    def _validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        valid, points, indices = self._validate_mesh_points_indices(mesh)
        if not valid:
            return

        num_points = len(points)
        if has_unreferenced_values(num_points, indices):
            if not self._all_primvars_can_be_fixed(mesh.GetPrim(), points):
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_018,
                    message="Some points are not referenced by the faces (but it cannot be fixed"
                    " automatically as it has primvars that are vertex or varying interpolated"
                    " and time varying).",
                    at=mesh,
                )
            else:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_018,
                    message="Some points are not referenced by the faces.",
                    at=mesh,
                    suggestion=Suggestion(
                        message="Removed unreferenced points", callable=self.remove_unreferenced_points
                    ),
                )
        elif has_invalid_indices(num_points, indices):
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_018,
                message="Some face indices are invalid (above number of points).",
                at=mesh,
            )

    @classmethod
    def remove_unreferenced_points(cls, _: Usd.Stage, prim: Usd.Prim):
        if not (mesh := UsdGeom.Mesh(prim)):
            return

        valid, points, indices = UnusedMeshTopologyChecker._validate_mesh_points_indices(mesh)
        if not valid:
            return

        # Don't remove invalid indices from faceIndices as it breaks geometry topology.
        remapped, remapped_points, indices, removed_value_indices = remove_unused_values_and_remap_indices(
            points, indices, False
        )
        if remapped:
            points_attr: Vt.Vec3fArray = mesh.GetPointsAttr()
            indices_attr: Vt.IntArray = mesh.GetFaceVertexIndicesAttr()
            with Sdf.ChangeBlock():
                points_attr.Set(remapped_points)
                indices_attr.Set(indices)

                # Remove corresponding primvar values if they are vertex or varying interpolated.
                primvars_api = UsdGeom.PrimvarsAPI(prim)
                for primvar in primvars_api.GetPrimvarsWithAuthoredValues():
                    if not cls._is_interested_primvar(primvar):
                        continue

                    element_size = primvar.GetElementSize()
                    primvar_values = list(primvar.ComputeFlattened(Usd.TimeCode.EarliestTime())) or []
                    # Invalid primvar size.
                    if element_size < 1 or len(primvar_values) / element_size != len(points):
                        continue

                    # Remove value in reverse order to keep validity of indices.
                    if primvar.IsIndexed():
                        indices = list(primvar.GetIndices(Usd.TimeCode.EarliestTime())) or []
                        for index in sorted(removed_value_indices, reverse=True):
                            del indices[index]
                        primvar.SetIndices(indices)
                    else:
                        # Expand indices based on element size.
                        expanded_indices = []
                        for index in removed_value_indices:
                            expanded_indices.extend(range(index * element_size, (index + 1) * element_size))

                        for index in sorted(expanded_indices, reverse=True):
                            del primvar_values[index]
                        primvar.Set(primvar_values)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            points_attr: Usd.Attribute = mesh.GetPointsAttr()
            has_static_points: bool = points_attr.IsAuthored() and not points_attr.ValueMightBeTimeVarying()
            if not has_static_points:
                return
            indices_attr: Usd.Attribute = mesh.GetFaceVertexIndicesAttr()
            has_static_indices: bool = indices_attr.IsAuthored() and not indices_attr.ValueMightBeTimeVarying()
            if not has_static_indices:
                return
            face_sizes_attr: Usd.Attribute = mesh.GetFaceVertexCountsAttr()
            has_static_faces: bool = face_sizes_attr.IsAuthored() and not face_sizes_attr.ValueMightBeTimeVarying()
            if not has_static_faces:
                return
            self._validate_mesh(mesh)

    @staticmethod
    def _is_interested_primvar(primvar: UsdGeom.Primvar):
        if not is_typename_array(primvar.GetTypeName()):
            return False

        interpolation: Tf.Token = primvar.GetInterpolation()
        is_vertex_or_varying = interpolation in [UsdGeom.Tokens.varying, UsdGeom.Tokens.vertex]
        if not is_vertex_or_varying:
            return False

        return True

    def _all_primvars_can_be_fixed(self, prim: Usd.Prim, points):
        primvars_api = UsdGeom.PrimvarsAPI(prim)
        for primvar in primvars_api.GetPrimvarsWithAuthoredValues():
            if not self._is_interested_primvar(primvar):
                continue

            if primvar.ValueMightBeTimeVarying():
                return False

            element_size = primvar.GetElementSize()
            primvar_values = list(primvar.ComputeFlattened(Usd.TimeCode.EarliestTime())) or []
            # Invalid primvar size.
            if element_size < 1 or len(primvar_values) / element_size != len(points):
                return False

        return True


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_019)
class ZeroAreaFaceChecker(BaseRuleChecker):
    """
    Faces with zero area can be removed. May produce welding after removal.

    Works on non time varying geometry.
    """

    def validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        points: Vt.Vec3fArray | None = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime())
        point_size: int = len(points) if points else 0
        indices: Vt.IntArray = mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime())
        face_sizes: Vt.IntArray = mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime())
        if all((indices, face_sizes, point_size)):
            valid_topology, _ = UsdGeom.Mesh.ValidateTopology(indices, face_sizes, point_size)
        else:
            valid_topology = False
        if not valid_topology:
            # Validated in ValidationTopologyChecker
            return

        if has_empty_faces(mesh):
            self._AddWarning(
                requirement=cap.Requirements.VG_019,
                message="The mesh contains zero area faces.",
                at=mesh,
            )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            points_attr: Usd.Attribute = mesh.GetPointsAttr()
            has_static_points: bool = points_attr.IsAuthored() and not points_attr.ValueMightBeTimeVarying()
            if not has_static_points:
                return
            indices_attr: Usd.Attribute = mesh.GetFaceVertexIndicesAttr()
            has_static_indices: bool = indices_attr.IsAuthored() and not indices_attr.ValueMightBeTimeVarying()
            if not has_static_indices:
                return
            face_sizes_attr: Usd.Attribute = mesh.GetFaceVertexCountsAttr()
            has_static_faces: bool = face_sizes_attr.IsAuthored() and not face_sizes_attr.ValueMightBeTimeVarying()
            if not has_static_faces:
                return
            self.validate_mesh(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_016)
class WeldChecker(BaseRuleChecker):
    """
    If attributes contain equal values they can be unified and the indices adjusted accordingly.

    Works on non time varying geometry.
    """

    def validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        try:
            if has_weldable_points(mesh):
                points_attr: Usd.Attribute = mesh.GetPointsAttr()
                self._AddWarning(
                    requirement=cap.Requirements.VG_016,
                    message="Some points are co-located and may be able to be merged.",
                    at=points_attr,
                )
        except ValueError as e:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_016,
                message=str(e),
                at=mesh,
            )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            points_attr: Usd.Attribute = mesh.GetPointsAttr()
            has_static_points: bool = points_attr.IsAuthored() and not points_attr.ValueMightBeTimeVarying()
            if has_static_points:
                self.validate_mesh(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_014)
class ValidateTopologyChecker(BaseRuleChecker):
    """
    Validate the topology of a mesh on all time samples.
    """

    @classmethod
    def _get_time_samples(cls, attribute: Usd.Attribute) -> Iterator[Usd.TimeCode]:
        if attribute.Get(Usd.TimeCode.Default()):
            yield Usd.TimeCode.Default()
        for time in attribute.GetTimeSamples():
            yield Usd.TimeCode(time)

    def _get_validate_topology_args(self, mesh: UsdGeom.Mesh) -> tuple[Vt.IntArray, Vt.IntArray, int]:
        # Get attributes
        points_attr: Usd.Attribute = mesh.GetPointsAttr()
        indices_attr: Usd.Attribute = mesh.GetFaceVertexIndicesAttr()
        counts_attr: Usd.Attribute = mesh.GetFaceVertexCountsAttr()
        # Determine time varying
        static_points: bool = not points_attr.ValueMightBeTimeVarying()
        static_indices: bool = not indices_attr.ValueMightBeTimeVarying()
        static_counts: bool = not counts_attr.ValueMightBeTimeVarying()
        static_topology: bool = static_indices and static_counts
        # Decide scenario
        if static_points and static_topology:
            indices: Vt.IntArray = indices_attr.Get(Usd.TimeCode.EarliestTime())
            counts: Vt.IntArray = counts_attr.Get(Usd.TimeCode.EarliestTime())
            points_attr_value: Vt.Vec3fArray | None = points_attr.Get(Usd.TimeCode.EarliestTime())
            point_size: int = len(points_attr_value) if points_attr_value else 0
            yield indices, counts, point_size
        elif static_topology:
            indices: Vt.IntArray = indices_attr.Get(Usd.TimeCode.EarliestTime())
            counts: Vt.IntArray = counts_attr.Get(Usd.TimeCode.EarliestTime())
            point_sizes: set[int] = set()
            for time in self._get_time_samples(points_attr):
                point_attr_value: Vt.Vec3fArray | None = points_attr.Get(time)
                point_size = len(point_attr_value) if point_attr_value else 0
                point_sizes.add(point_size)

            for point_size in point_sizes:
                yield indices, counts, point_size
        elif static_points:
            points_attr_value: Vt.Vec3fArray | None = points_attr.Get(Usd.TimeCode.EarliestTime())
            point_size: int = len(points_attr_value) if points_attr_value else 0
            if static_indices:
                indices: Vt.IntArray = indices_attr.Get(Usd.TimeCode.EarliestTime())
                for time in self._get_time_samples(counts_attr):
                    counts: Vt.IntArray = counts_attr.Get(time)
                    yield indices, counts, point_size
            elif static_counts:
                counts: Vt.IntArray = counts_attr.Get(Usd.TimeCode.EarliestTime())
                for time in self._get_time_samples(indices_attr):
                    indices: Vt.IntArray = indices_attr.Get(time)
                    yield indices, counts, point_size
            else:
                times: set[Usd.TimeCode] = set(self._get_time_samples(indices_attr)) & set(
                    self._get_time_samples(counts_attr)
                )
                for time in times:
                    indices: Vt.IntArray = indices_attr.Get(time)
                    counts: Vt.IntArray = counts_attr.Get(time)
                    yield indices, counts, point_size
        else:
            times: set[Usd.TimeCode] = (
                set(self._get_time_samples(points_attr))
                & set(self._get_time_samples(indices_attr))
                & set(self._get_time_samples(counts_attr))
            )
            for time in times:
                indices: Vt.IntArray = indices_attr.Get(time)
                counts: Vt.IntArray = counts_attr.Get(time)
                points: Vt.Vec3fArray | None = points_attr.Get(time)
                point_size: int = len(points) if points else 0
                yield indices, counts, point_size

    def validate(self, mesh: UsdGeom.Mesh) -> None:
        for indices, counts, point_size in self._get_validate_topology_args(mesh):
            if all((indices, counts, point_size)):
                valid_topology, _ = UsdGeom.Mesh.ValidateTopology(indices, counts, point_size)
            else:
                # No Points, no FaceVertexCounts, or no indices - not valid topology
                valid_topology = False

            if not valid_topology:
                self._AddFailedCheck(
                    requirement=cap.Requirements.VG_014,
                    message="Invalid topology found",
                    at=mesh,
                )
                break

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            self.validate(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_011)
class UnusedPrimvarChecker(BaseRuleChecker):
    """
    Values which are not referenced by the indices in a primvar can be removed.

    Works on non time varying geometry.
    """

    def _validate_primvars(self, primvars_api: UsdGeom.PrimvarsAPI) -> None:
        for primvar in primvars_api.GetPrimvarsWithAuthoredValues():
            # Skips non-indexed primvars and ones without a list value type.
            if not primvar.IsIndexed():
                continue

            if not is_typename_array(primvar.GetTypeName()):
                continue

            interpolation: Tf.Token = primvar.GetInterpolation()
            is_vertex_or_varying = interpolation in [UsdGeom.Tokens.varying, UsdGeom.Tokens.vertex]
            invalid_indices = has_invalid_primvar_indices(primvar)
            unreferenced_values = has_unreferenced_primvar(primvar)
            if unreferenced_values or (is_vertex_or_varying and invalid_indices):
                if unreferenced_values:
                    warning_message = f"{primvar.GetName()} contains values not referenced by its indices."
                    suggestion_message = "Remove unreferenced values"
                else:
                    warning_message = (
                        f"{primvar.GetName()} contains invalid indices that are above the number of values."
                    )
                    suggestion_message = "Remove invalid indices"
                self._AddWarning(
                    requirement=cap.Requirements.VG_011,
                    message=warning_message,
                    at=primvar.GetAttr(),
                    suggestion=Suggestion(
                        message=suggestion_message,
                        callable=self.remove_unreferenced_values,
                    ),
                )
            elif invalid_indices:
                self._AddWarning(
                    requirement=cap.Requirements.VG_011,
                    message=f"{primvar.GetName()} contains invalid indices that are above the number of values "
                    f"(but it cannot be fixed automatically as the interpolation is neither UsdGeom.Tokens.Vertex "
                    f"nor UsdGeom.Tokens.Varying).",
                    at=primvar.GetAttr(),
                )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        primvars_api: UsdGeom.PrimvarsAPI = UsdGeom.PrimvarsAPI(prim)
        if primvars_api:
            self._validate_primvars(primvars_api)

    @staticmethod
    def remove_unreferenced_values(_: Usd.Stage, attr: Usd.Attribute):
        if not (primvar := UsdGeom.Primvar(attr)) or not primvar.IsIndexed():
            return

        interpolation: Tf.Token = primvar.GetInterpolation()
        is_vertex_or_varying = interpolation and interpolation in [UsdGeom.Tokens.varying, UsdGeom.Tokens.vertex]
        primvar_values = primvar.Get(Usd.TimeCode.EarliestTime()) or []
        indices: Vt.IntArray = primvar.GetIndices(Usd.TimeCode.EarliestTime()) or []
        remapped, primvar_values, indices, _ = remove_unused_values_and_remap_indices(
            primvar_values, indices, is_vertex_or_varying
        )
        if remapped:
            with Sdf.ChangeBlock():
                primvar.Set(primvar_values)
                primvar.SetIndices(indices)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_027)
class NormalsExistChecker(BaseRuleChecker):
    """
    Check that meshes have normals. All meshes should have normals
    unless they have the subdivision scheme set. Meshes cannot have
    both normals and subdivision set.
    """

    @classmethod
    def set_to_none(cls, _: Usd.Stage, mesh: UsdGeom.Mesh) -> None:
        """Sets subdivision scheme to None"""
        mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)

    @classmethod
    def remove_non_primvar_normals(cls, _: Usd.Stage, mesh: UsdGeom.Mesh) -> None:
        """Remove the non-primvar normals attribute from the mesh"""
        normals_attr: Usd.Attribute = mesh.GetNormalsAttr()
        if normals_attr and normals_attr.HasAuthoredValue():
            normals_attr.Block()

    def _validate_mesh(self, mesh: UsdGeom.Mesh) -> None:
        # If both normals and primvar are set, need to remove one.
        normals_attr: Usd.Attribute = mesh.GetNormalsAttr()
        primvar_normals_attr: UsdGeom.Primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(UsdGeom.Tokens.normals)
        has_normals: bool = normals_attr.HasAuthoredValue() or primvar_normals_attr.HasAuthoredValue()
        has_both_normals: bool = normals_attr.HasAuthoredValue() and primvar_normals_attr.HasAuthoredValue()

        if has_both_normals:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_027,
                message="Both normals and primvar:normals exist. Only one set of normals should be present."
                "primvar:normals will take priority over non-primvar normals",
                at=mesh,
                suggestion=Suggestion(
                    message="Remove non-primvar normals",
                    callable=self.remove_non_primvar_normals,
                    at=normals_attr,
                ),
            )

        # Get the subdivision scheme. If attribute is undefined, this
        # will return Catmull-Clark, so no need to check explicitly
        # for undefined attribute case.
        subdivision_attr: Usd.Attribute = mesh.GetSubdivisionSchemeAttr()
        subdivision_scheme: Tf.Token = mesh.GetSubdivisionSchemeAttr().Get()

        # Normals are set but subdivision scheme is not "none". Fail and suggest fix.
        if subdivision_scheme != UsdGeom.Tokens.none and has_normals:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_027,
                message="Normals are defined but subdivision mesh also has normals, either remove normals or set"
                "subdivision scheme to None.",
                at=mesh,
                suggestion=Suggestion(
                    message="Set subdivision scheme to none for a polygonal mesh which uses normals",
                    callable=self.set_to_none,
                    at=subdivision_attr,
                ),
            )

        # No normals and subdivision is set to None. Invalid. Warn and ask user to set one
        elif subdivision_scheme == UsdGeom.Tokens.none and not has_normals:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_027,
                message="Either normals should be authored or subdivision should be set to Catmull-Clark or Loop ",
                at=mesh,
            )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if mesh:
            self._validate_mesh(mesh)


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_028)
class NormalsValidChecker(BaseRuleChecker):
    """
    Check that all normals have unit length, and that there are no non-finite values.
    Also checks that the supplied number of normal values agrees with the interpolation.
    """

    UNIT_LENGTH_TOLERANCE = 1e-3

    @staticmethod
    def _is_finite_vec3(v: Gf.Vec3f):
        return all(math.isfinite(c) for c in v)

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if not prim.IsA(UsdGeom.Mesh):
            return

        mesh = UsdGeom.Mesh(prim)

        # Subdivision rule: normals should not be authored on subdiv meshes.
        scheme = mesh.GetSubdivisionSchemeAttr().Get() or UsdGeom.Tokens.catmullClark
        src = _get_normals_source(mesh, Usd.TimeCode.EarliestTime())

        if scheme != UsdGeom.Tokens.none and src is not None:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_028,
                message=f"Mesh '{prim.GetPath()}' is subdiv ('{scheme}') but has authored normals; USD recommends not authoring normals on subdiv meshes.",
                at=prim,
            )
            # Continue checking anyway; downstream tools may still consume them.

        # If no normals at all, nothing to validate (often OK → faceted polys).
        if src is None:
            return

        interp, normals, topo_count, _, _, _ = src

        # Accept the standard interpolation tokens. (normals commonly use 'varying' or 'vertex')
        valid_interps = {
            UsdGeom.Tokens.vertex,
            UsdGeom.Tokens.varying,
            UsdGeom.Tokens.uniform,
            UsdGeom.Tokens.faceVarying,
            UsdGeom.Tokens.constant,
        }
        if interp not in valid_interps:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_028,
                message=f"Mesh '{prim.GetPath()}' has invalid normals interpolation: '{interp}'.",
                at=prim,
            )
            return

        # Expected element count by interpolation
        face_counts = mesh.GetFaceVertexCountsAttr().Get() or []
        indices = mesh.GetFaceVertexIndicesAttr().Get() or []
        points = mesh.GetPointsAttr().Get() or []

        face_count = len(face_counts)
        point_count = len(points)
        face_vert_count = len(indices)

        if interp in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying):
            expected = point_count
        elif interp == UsdGeom.Tokens.uniform:
            expected = face_count
        elif interp == UsdGeom.Tokens.faceVarying:
            expected = face_vert_count
        else:  # "constant"
            expected = 1

        if topo_count != expected:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_028,
                message=(
                    f"Mesh '{prim.GetPath()}' normals have {topo_count} elements but expected {expected} "
                    f"for '{interp}' interpolation."
                ),
                at=prim,
            )

        # Check the actual normal vectors for validity & normalization.
        # For indexed primvars we still validate the value array contents themselves.
        for n in normals:
            if not self._is_finite_vec3(n):
                self._AddError(
                    requirement=cap.Requirements.VG_028,
                    message=f"Mesh '{prim.GetPath()}' has non-finite normal components.",
                    at=prim,
                )
                break
            length = n.GetLength()
            if abs(length - 1.0) > self.UNIT_LENGTH_TOLERANCE:
                self._AddWarning(
                    requirement=cap.Requirements.VG_028,
                    message=f"Mesh '{prim.GetPath()}' has non-unit normal (length={length:.6f}).",
                    at=prim,
                )
                break


@register_rule("Geometry")
@register_requirements(cap.Requirements.VG_029)
class NormalsWindingsChecker(BaseRuleChecker):
    """
    Check that the mesh has normals that are consistent with the face windings,
    taking into account the 'orientation' attribute.

    We define the meaning of agreement between a normal attribute value and the
    reference normal of a face (quite loosely) as the two having a positive inner product.
    We then sum these inner products, and if the sum is positive, it would be a relatively
    large number (close to the area of the surface) and this would indicate that the winding
    is right-handed. Otherwise, the sum would be a relatively large negative number to
    indicate a left-handed rule having been used for generation of normals.

    Works on non time varying geometry.
    """

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if not prim.IsA(UsdGeom.Mesh):
            return

        mesh = UsdGeom.Mesh(prim)

        points_attr: Usd.Attribute = mesh.GetPointsAttr()
        has_static_points: bool = points_attr.IsAuthored() and not points_attr.ValueMightBeTimeVarying()
        if not has_static_points:
            return
        indices_attr: Usd.Attribute = mesh.GetFaceVertexIndicesAttr()
        has_static_indices: bool = indices_attr.IsAuthored() and not indices_attr.ValueMightBeTimeVarying()
        if not has_static_indices:
            return
        face_sizes_attr: Usd.Attribute = mesh.GetFaceVertexCountsAttr()
        has_static_faces: bool = face_sizes_attr.IsAuthored() and not face_sizes_attr.ValueMightBeTimeVarying()
        if not has_static_faces:
            return

        orientation_attr: Usd.Attribute = mesh.GetOrientationAttr()
        has_static_orientation: bool = not orientation_attr.ValueMightBeTimeVarying()
        if not has_static_orientation:
            return

        src = _get_normals_source(mesh, Usd.TimeCode.EarliestTime())
        if src is None:
            return

        interp, normals, _, _, normals_indexed, normals_indices = src

        winding_bias = compute_winding_bias(mesh, interp, normals, normals_indexed, normals_indices)

        # Pull topology
        orientation = orientation_attr.Get(Usd.TimeCode.EarliestTime()) or UsdGeom.Tokens.rightHanded

        if (winding_bias >= 0) != (orientation == UsdGeom.Tokens.rightHanded):
            self._AddError(
                requirement=cap.Requirements.VG_029,
                message=f"Mesh '{prim.GetPath()}' has normals inconsistent with the face windings.",
                at=prim,
            )


@register_requirements(cap.Requirements.VG_MESH_001)
class _ContainsMeshChecker(BaseRuleChecker):
    """
    Validates that the stage contains at least one mesh.
    Warns if other geometry is also present.

    Implements VG_MESH_001
    """

    def CheckStage(self, stage: Usd.Stage) -> None:

        def find_mesh_prim(stage: Usd.Stage) -> Usd.Prim | None:
            """
            Traverses a USD stage to find at least one Mesh prim and one other
            type of geometry prim.

            Args:
                stage: The USD stage to traverse.

            Returns:
                A tuple containing the first found Mesh prim and the first found
                other geometry prim. Either can be None if not found.
            """
            for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
                if prim.IsA(UsdGeom.Mesh):
                    return prim
            return None

        mesh_prim: Usd.Prim | None = find_mesh_prim(stage)
        if not mesh_prim:
            self._AddFailedCheck(
                requirement=cap.Requirements.VG_MESH_001, message="Stage does not contain any meshes.", at=stage
            )


@register_requirements(cap.Requirements.VG_025)
class _AssetOriginPositioningChecker(BaseRuleChecker):
    """
    Validates that assets are positioned at origin.

    Asset transforms shall be defined such that the asset is correctly positioned and oriented
    at the origin (0,0,0) with no rotation and unit scale in its local space before any
    instance-specific transformations are applied in an aggregate scene.

    This ensures:
    - Predictable asset placement in scenes
    - Simplified instancing workflows
    - Consistent behavior across different applications
    - Easier debugging of transformation issues
    - Reduced floating-point precision errors when instancing far from origin

    The validator checks the default prim's local transformation matrix against identity,
    reporting specific issues for translation, rotation, and scale deviations.

    Parameters:
        TRANSFORM_TOLERANCE: Maximum allowed deviation from identity transform for translation
                            checks, measured in scene units. Default: 1e-4.
    """

    _ROTATION_TOLERANCE_RADIANS = 1e-4
    _SCALE_TOLERANCE = 1e-4

    @classmethod
    def _get_identity_value(cls, op: UsdGeom.XformOp):
        """
        Returns the identity value based on the op type.
        """
        op_type: Tf.Token = op.GetOpType()
        op_precision: Tf.Token = op.GetPrecision()

        def _Vector3(value: float) -> Gf.Vec3f | Gf.Vec3d | Gf.Vec3h:
            if op_precision == UsdGeom.XformOp.PrecisionFloat:
                return Gf.Vec3f(value, value, value)
            elif op_precision == UsdGeom.XformOp.PrecisionDouble:
                return Gf.Vec3d(value, value, value)
            elif op_precision == UsdGeom.XformOp.PrecisionHalf:
                return Gf.Vec3h(value, value, value)

        def _Matrix4(value: float) -> Gf.Matrix4f | Gf.Matrix4d:
            if op_precision == UsdGeom.XformOp.PrecisionFloat:
                return Gf.Matrix4f(value)
            elif op_precision == UsdGeom.XformOp.PrecisionDouble:
                return Gf.Matrix4d(value)

        def _Quat(value: float) -> Gf.Quatf | Gf.Quatd | Gf.Quath:
            if op_precision == UsdGeom.XformOp.PrecisionFloat:
                return Gf.Quatf(value)
            elif op_precision == UsdGeom.XformOp.PrecisionDouble:
                return Gf.Quatd(value)
            elif op_precision == UsdGeom.XformOp.PrecisionHalf:
                return Gf.Quath(value)

        def _IsTranslateScalar() -> bool:
            try:
                return op_type in [
                    UsdGeom.XformOp.TypeTranslateX,
                    UsdGeom.XformOp.TypeTranslateY,
                    UsdGeom.XformOp.TypeTranslateZ,
                ]
            except AttributeError:
                return False

        def _IsScaleScalar() -> bool:
            try:
                return op_type in [
                    UsdGeom.XformOp.TypeScaleX,
                    UsdGeom.XformOp.TypeScaleY,
                    UsdGeom.XformOp.TypeScaleZ,
                ]
            except AttributeError:
                return False

        def _IsRotateScalar() -> bool:
            try:
                return op_type in [
                    UsdGeom.XformOp.TypeRotateX,
                    UsdGeom.XformOp.TypeRotateY,
                    UsdGeom.XformOp.TypeRotateZ,
                ]
            except AttributeError:
                return False

        def _IsRotateVector() -> bool:
            try:
                return op_type in [
                    UsdGeom.XformOp.TypeRotateXYZ,
                    UsdGeom.XformOp.TypeRotateXZY,
                    UsdGeom.XformOp.TypeRotateYXZ,
                    UsdGeom.XformOp.TypeRotateYZX,
                    UsdGeom.XformOp.TypeRotateZXY,
                    UsdGeom.XformOp.TypeRotateZYX,
                ]
            except AttributeError:
                return False

        if op_type == UsdGeom.XformOp.TypeScale:
            return _Vector3(1.0)
        elif _IsScaleScalar():
            return 1.0
        elif op_type == UsdGeom.XformOp.TypeTranslate:
            return _Vector3(0.0)
        elif _IsTranslateScalar():
            return 0.0
        elif _IsRotateScalar():
            return 0.0
        elif _IsRotateVector():
            return _Vector3(0.0)
        elif op_type == UsdGeom.XformOp.TypeTransform:
            return _Matrix4(1.0)
        elif op_type == UsdGeom.XformOp.TypeOrient:
            return _Quat(1.0)
        return None

    @classmethod
    def _reset_ops(cls, _: Usd.Stage, prim: Usd.Prim) -> None:
        """Iterates over existing ops and resets each to its identity value."""
        xformable = UsdGeom.Xformable(prim)
        for op in xformable.GetOrderedXformOps():
            if identity_value := cls._get_identity_value(op):
                op.Set(identity_value)

    def CheckStage(self, stage: Usd.Stage) -> None:
        default_prim = stage.GetDefaultPrim()
        if not default_prim:
            return

        xformable = UsdGeom.Xformable(default_prim)
        if xformable:
            local_transform = xformable.GetLocalTransformation()

            tolerance = self.parameters["TRANSFORM_TOLERANCE"].assigned_value

            # Check if the matrix is close to identity
            identity = Gf.Matrix4d(1.0)
            if not Gf.IsClose(local_transform, identity, tolerance):
                # Decompose the matrix to provide specific error messages

                # Extract translation
                translation = local_transform.ExtractTranslation()
                if translation.GetLength() > tolerance:
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VG_025,
                        message=f"Asset root prim has non-zero translation: {tuple(translation)}.",
                        at=default_prim,
                        suggestion=Suggestion(
                            message="Reset the xform ops to identity",
                            callable=self._reset_ops,
                        ),
                    )

                # Extract rotation
                rotation = local_transform.ExtractRotation()
                angle = rotation.GetAngle()

                if abs(angle) > self._ROTATION_TOLERANCE_RADIANS:
                    angle_degrees = math.degrees(angle)
                    axis = rotation.GetAxis()
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VG_025,
                        message=f"Asset root prim has non-zero rotation: {angle_degrees:.2f} degrees around axis {tuple(axis)}.",
                        at=default_prim,
                        suggestion=Suggestion(
                            message="Reset the xform ops to identity",
                            callable=self._reset_ops,
                        ),
                    )

                # Check scale - extract scale values from the matrix
                # Note: This assumes no shear in the transformation
                scale_x = local_transform.GetRow(0).GetLength()
                scale_y = local_transform.GetRow(1).GetLength()
                scale_z = local_transform.GetRow(2).GetLength()

                if any(abs(s - 1.0) > self._SCALE_TOLERANCE for s in [scale_x, scale_y, scale_z]):
                    self._AddFailedCheck(
                        requirement=cap.Requirements.VG_025,
                        message=f"Asset root prim has non-unit scale: {(scale_x, scale_y, scale_z)}.",
                        at=default_prim,
                        suggestion=Suggestion(
                            message="Reset the xform ops to identity",
                            callable=self._reset_ops,
                        ),
                    )
