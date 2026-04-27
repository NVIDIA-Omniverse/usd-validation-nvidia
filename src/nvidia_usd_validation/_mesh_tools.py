# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import operator
from collections import defaultdict
from collections.abc import Sequence
from functools import cache
from itertools import repeat
from typing import Any, TypeVar

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

from ._graph_tools import DisjointSet
from ._import_utils import default_implementation, default_implementation_method

__all__ = [
    "RepeatedValuesSet",
    "check_manifold_elements",
    "compute_winding_bias",
    "has_empty_faces",
    "has_indexable_values",
    "has_invalid_indices",
    "has_invalid_primvar_indices",
    "has_unreferenced_primvar",
    "has_unreferenced_values",
    "has_weldable_points",
    "is_typename_array",
    "remove_unused_values_and_remap_indices",
]

VtArray = Sequence
"""Alias. For typing."""

ScalarType = TypeVar(
    "ScalarType",
    int,
    float,
    Gf.Vec2f,
    Gf.Vec3f,
)
"""Alias. For typing."""

_ARRAY_TYPE_NAMES: set[Sdf.ValueTypeNames] = {
    Sdf.ValueTypeNames.BoolArray,
    Sdf.ValueTypeNames.UCharArray,
    Sdf.ValueTypeNames.IntArray,
    Sdf.ValueTypeNames.UIntArray,
    Sdf.ValueTypeNames.Int64Array,
    Sdf.ValueTypeNames.UInt64Array,
    Sdf.ValueTypeNames.HalfArray,
    Sdf.ValueTypeNames.FloatArray,
    Sdf.ValueTypeNames.DoubleArray,
    Sdf.ValueTypeNames.TimeCodeArray,
    Sdf.ValueTypeNames.StringArray,
    Sdf.ValueTypeNames.TokenArray,
    Sdf.ValueTypeNames.AssetArray,
    Sdf.ValueTypeNames.Int2Array,
    Sdf.ValueTypeNames.Int3Array,
    Sdf.ValueTypeNames.Int4Array,
    Sdf.ValueTypeNames.Half2Array,
    Sdf.ValueTypeNames.Half3Array,
    Sdf.ValueTypeNames.Half4Array,
    Sdf.ValueTypeNames.Float2Array,
    Sdf.ValueTypeNames.Float3Array,
    Sdf.ValueTypeNames.Float4Array,
    Sdf.ValueTypeNames.Double2Array,
    Sdf.ValueTypeNames.Double3Array,
    Sdf.ValueTypeNames.Double4Array,
    Sdf.ValueTypeNames.Point3hArray,
    Sdf.ValueTypeNames.Point3fArray,
    Sdf.ValueTypeNames.Point3dArray,
    Sdf.ValueTypeNames.Vector3hArray,
    Sdf.ValueTypeNames.Vector3fArray,
    Sdf.ValueTypeNames.Vector3dArray,
    Sdf.ValueTypeNames.Normal3hArray,
    Sdf.ValueTypeNames.Normal3fArray,
    Sdf.ValueTypeNames.Normal3dArray,
    Sdf.ValueTypeNames.Color3hArray,
    Sdf.ValueTypeNames.Color3fArray,
    Sdf.ValueTypeNames.Color3dArray,
    Sdf.ValueTypeNames.Color4hArray,
    Sdf.ValueTypeNames.Color4fArray,
    Sdf.ValueTypeNames.Color4dArray,
    Sdf.ValueTypeNames.QuathArray,
    Sdf.ValueTypeNames.QuatfArray,
    Sdf.ValueTypeNames.QuatdArray,
    Sdf.ValueTypeNames.Matrix2dArray,
    Sdf.ValueTypeNames.Matrix3dArray,
    Sdf.ValueTypeNames.Matrix4dArray,
    Sdf.ValueTypeNames.Frame4dArray,
    Sdf.ValueTypeNames.TexCoord2hArray,
    Sdf.ValueTypeNames.TexCoord2fArray,
    Sdf.ValueTypeNames.TexCoord2dArray,
    Sdf.ValueTypeNames.TexCoord3hArray,
    Sdf.ValueTypeNames.TexCoord3fArray,
    Sdf.ValueTypeNames.TexCoord3dArray,
    # Sdf.ValueTypeNames.PathExpressionArray,
}


def is_typename_array(type_name: Sdf.ValueTypeName):
    return type_name in _ARRAY_TYPE_NAMES


@default_implementation
def check_manifold_elements(num_vertices: int, indices: Vt.IntArray, face_sizes: Vt.IntArray) -> tuple[int, int, bool]:
    """
    Construct all the edges in geometry and finds if we have:
    - Non-manifold vertices: Two or more faces share a vertex but no edge and/or no faces between them.
    - Non-manifold edges: More than 2 faces share an edge.
    - Inconsistent winding: Adjacent faces have opposite winding.

    Args:
        num_vertices: The number of total vertices.
        indices: An array of all indices.
        face_sizes: An array of all face sizes.

    Returns:
        A tuple containing:
        - The number of non-manifold vertices.
        - The number of non-manifold edges.
        - Whether the winding is consistent.
    """
    # Create a mapping for the edges
    num_edges: int = len(indices)
    edges: Sequence[tuple[int, int, int]] = [(0, 0, 0)] * num_edges

    # Collect all edges.
    current_index: int = 0
    for face_index, face_size in enumerate(face_sizes):
        for i in range(face_size):
            p: int = indices[current_index + i]
            q: int = indices[current_index + (i + 1) % face_size]
            edges[current_index + i] = (p, q, face_index)
        current_index += face_size

    # Create a dict of edges.
    edge_to_winding: dict[tuple[int, int], list[bool]] = defaultdict(list)
    edge_to_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for p, q, face_index in edges:
        key: tuple[int, int] = (min(p, q), max(p, q))
        edge_to_winding[key].append(p < q)
        edge_to_faces[key].append(face_index)

    # Non-manifold edges: Three or more faces share an edge.
    num_nonmanifold_edges: int = 0
    for faces in edge_to_faces.values():
        if len(faces) > 2:
            num_nonmanifold_edges += 1
    # Winding consistency: Adjacent faces have opposite winding.
    winding_consistent: bool = True
    for winding in edge_to_winding.values():
        if len(winding) == 2 and winding[0] == winding[1]:
            winding_consistent = False
    # Non-manifold vertices: Two or more faces share a vertex but no edge and/or no faces between them.
    vertex_to_faces = [DisjointSet() for _ in range(num_vertices)]
    current_index: int = 0
    for face_index, face_size in enumerate(face_sizes):
        for i in range(face_size):
            p: int = indices[current_index + i]
            vertex_to_faces[p].make_set(face_index)
        current_index += face_size
    for (p, q), faces in edge_to_faces.items():
        if len(faces) == 2:
            vertex_to_faces[p].union(faces[0], faces[1])
            vertex_to_faces[q].union(faces[0], faces[1])
    num_nonmanifold_vertices = sum(1 for disjoint_set in vertex_to_faces if not disjoint_set.connected)

    return num_nonmanifold_vertices, num_nonmanifold_edges, winding_consistent


@check_manifold_elements.numpy
def _(num_vertices: int, indices: Vt.IntArray, face_sizes: Vt.IntArray) -> tuple[int, int, bool]:
    import numpy as np

    # Convert to numpy arrays if not already
    indices = np.asarray(indices, dtype=np.int64)
    face_sizes = np.asarray(face_sizes, dtype=np.int64)
    num_faces = int(face_sizes.size)

    # Per-index face id and face start positions
    face_starts = np.concatenate(([0], np.cumsum(face_sizes)[:-1]))
    index_faces = np.arange(num_faces, dtype=np.int64).repeat(face_sizes)

    # Build edge list (wrap last vertex of each face to first)
    edge_starts = indices
    edge_ends = np.concatenate([indices[1:], indices[0:1]])
    face_end_indices = face_starts + face_sizes - 1
    edge_ends[face_end_indices] = indices[face_starts]

    # Undirected edge key and direction
    edge_mins = np.minimum(edge_starts, edge_ends)
    edge_maxs = np.maximum(edge_starts, edge_ends)
    edge_directions = edge_starts < edge_ends
    edge_faces = index_faces

    # Unique edges and counts
    edge_keys = (edge_mins << 32) | edge_maxs
    _, inverse_indices, edge_counts = np.unique(edge_keys, return_inverse=True, return_counts=True)

    # Non-manifold edges: Three or more faces share an edge
    num_nonmanifold_edges = int(np.count_nonzero(edge_counts > 2))

    # Winding consistency: only check edges shared by exactly two faces
    winding_consistent = True
    double_mask = edge_counts[inverse_indices] == 2
    if np.any(double_mask):
        edge_keys_double = edge_keys[double_mask]
        edge_directions_double = edge_directions[double_mask]
        order = np.argsort(edge_keys_double)
        edge_directions_sorted = edge_directions_double[order]

        directions = edge_directions_sorted.reshape(-1, 2)
        inconsistent_pairs = directions[:, 0] == directions[:, 1]
        winding_consistent = not np.any(inconsistent_pairs)

    # Non-manifold vertices: Two or more faces share a vertex but no edge and/or no faces between them
    vertex_to_faces = np.empty(num_vertices, dtype=object)
    for i in range(num_vertices):
        vertex_to_faces[i] = DisjointSet()
    for p, face in zip(indices, index_faces):
        vertex_to_faces[p].make_set(face)

    if np.any(double_mask):
        edge_keys_double = edge_keys[double_mask]
        edge_faces_double = edge_faces[double_mask]
        order = np.argsort(edge_keys_double)
        edge_keys_sorted = edge_keys_double[order]
        edge_faces_sorted = edge_faces_double[order]

        edge_keys_unique = edge_keys_sorted[::2]
        face_pairs = edge_faces_sorted.reshape(-1, 2)

        p_vertices = (edge_keys_unique >> 32).astype(np.int64)
        q_vertices = (edge_keys_unique & 0xFFFFFFFF).astype(np.int64)
        for p, q, face1, face2 in zip(p_vertices, q_vertices, face_pairs[:, 0], face_pairs[:, 1]):
            vertex_to_faces[p].union(face1, face2)
            vertex_to_faces[q].union(face1, face2)

    # Count non-manifold vertices (those with multiple forests)
    num_nonmanifold_vertices = sum(1 for disjoint_set in vertex_to_faces if not disjoint_set.connected)

    return num_nonmanifold_vertices, num_nonmanifold_edges, winding_consistent


def vector_area(coords: list[Gf.Vec3f]):
    va = Gf.Vec3f(0, 0, 0)
    n = len(coords)
    x0: Gf.Vec3f = coords[0]
    x_prev: Gf.Vec3f = coords[1] - x0
    for i in range(2, n):
        x: Gf.Vec3f = coords[i] - x0
        va += Gf.Cross(x_prev, x)
        x_prev = x
    return va / 2


@default_implementation
def compute_winding_bias(
    mesh: UsdGeom.Mesh, interp: Tf.Token, normals: list[Gf.Vec3f], normals_indexed: bool, normals_indices: list[int]
) -> float:
    points: Vt.Vec3fArray = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime())
    face_sizes: Vt.IntArray = mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime())
    indices: Vt.IntArray = mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime())

    cursor = 0
    winding_bias = 0.0

    for face_index, nverts in enumerate(face_sizes):
        if nverts < 3:
            cursor += nverts
            continue  # degenerate

        face_coords = [points[i] for i in indices[cursor : cursor + nverts]]
        va = vector_area(face_coords)

        if interp == UsdGeom.Tokens.uniform:  # per face
            if normals_indexed:
                winding_bias += Gf.Dot(va, normals[normals_indices[face_index]])
            else:
                winding_bias += Gf.Dot(va, normals[face_index])
        elif interp == UsdGeom.Tokens.faceVarying:  # per corner
            for i in range(nverts):
                corner_idx = cursor + i
                if normals_indexed:
                    winding_bias += Gf.Dot(va, normals[normals_indices[corner_idx]])
                else:
                    winding_bias += Gf.Dot(va, normals[corner_idx])
        elif interp in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying):  # per vertex
            for i in range(nverts):
                vertex_idx = indices[cursor + i]
                if normals_indexed:
                    winding_bias += Gf.Dot(va, normals[normals_indices[vertex_idx]])
                else:
                    winding_bias += Gf.Dot(va, normals[vertex_idx])
        else:
            pass

        cursor += nverts

    return winding_bias


@compute_winding_bias.numpy
def _(
    mesh: UsdGeom.Mesh, interp: Tf.Token, normals: list[Gf.Vec3f], normals_indexed: bool, normals_indices: list[int]
) -> float:
    import numpy as np

    def _compute_face_vector_areas(points, face_sizes, indices):
        """Optimized for common case: mostly triangles and quads"""

        face_offsets = np.concatenate([[0], np.cumsum(face_sizes)])
        num_faces = len(face_sizes)
        vector_areas = np.zeros((num_faces, 3))

        # Fast path for triangles (nverts == 3)
        tri_mask = face_sizes == 3
        if np.any(tri_mask):
            tri_starts = face_offsets[:-1][tri_mask]
            v0 = points[indices[tri_starts]]
            v1 = points[indices[tri_starts + 1]]
            v2 = points[indices[tri_starts + 2]]
            vector_areas[tri_mask] = np.cross(v1 - v0, v2 - v0) / 2

        # Fast path for quads (nverts == 4)
        quad_mask = face_sizes == 4
        if np.any(quad_mask):
            quad_starts = face_offsets[:-1][quad_mask]
            v0 = points[indices[quad_starts]]
            v1 = points[indices[quad_starts + 1]]
            v2 = points[indices[quad_starts + 2]]
            v3 = points[indices[quad_starts + 3]]
            # Two triangles: (v0,v1,v2) and (v0,v2,v3)
            tri1 = np.cross(v1 - v0, v2 - v0)
            tri2 = np.cross(v2 - v0, v3 - v0)
            vector_areas[quad_mask] = (tri1 + tri2) / 2

        # Slow path for n-gons (nverts > 4)
        ngon_mask = face_sizes > 4
        if np.any(ngon_mask):
            ngon_indices = np.where(ngon_mask)[0]
            for face_idx in ngon_indices:
                start = face_offsets[face_idx]
                nverts = face_sizes[face_idx]
                face_indices_slice = indices[start : start + nverts]
                face_coords = points[face_indices_slice]
                x0 = face_coords[0]
                relative_coords = face_coords[1:] - x0
                crosses = np.cross(relative_coords[:-1], relative_coords[1:])
                vector_areas[face_idx] = crosses.sum(axis=0) / 2

        return vector_areas

    points = np.array(mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime()))
    face_sizes = np.array(mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime()))
    indices = np.array(mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime()))
    normals_np = np.array(normals)

    vector_areas = _compute_face_vector_areas(points, face_sizes, indices)

    # Get valid faces (nverts >= 3)
    valid_faces = face_sizes >= 3

    if normals_indexed:
        normals_indices_np = np.array(normals_indices)
        selected_normals = normals_np[normals_indices_np]
    else:
        selected_normals = normals_np

    if interp == UsdGeom.Tokens.uniform:
        return float(np.sum(np.einsum("ij,ij->i", vector_areas[valid_faces], selected_normals[valid_faces])))
    elif interp == UsdGeom.Tokens.faceVarying:
        # Create a mapping from corners to faces
        face_indices_per_corner = np.repeat(np.arange(len(face_sizes)), face_sizes)
        # Dot product of each corner normal with its face vector area
        dots = np.einsum("ij,ij->i", selected_normals, vector_areas[face_indices_per_corner])
        return float(np.sum(dots))
    elif interp in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying):
        # Map each vertex to its face
        face_indices_per_vertex = np.repeat(np.arange(len(face_sizes)), face_sizes)
        vertex_normals = selected_normals[indices]
        dots = np.einsum("ij,ij->i", vertex_normals, vector_areas[face_indices_per_vertex])
        return float(np.sum(dots))

    return 0.0


@default_implementation
def has_empty_faces(mesh: UsdGeom.Mesh) -> bool:
    vertices: Vt.Vec3fArray = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime())
    indices: Vt.IntArray = mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime())
    face_sizes: Vt.IntArray = mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime())

    index: int = 0
    for face_size in face_sizes:
        # compute normal for orientation
        points: Sequence[Gf.Vec3f] = list(map(vertices.__getitem__, indices[index : index + face_size]))
        # points[i] - points[0]
        deltas: Sequence[Gf.Vec3f] = list(map(operator.sub, points[1:], repeat(points[0], face_size - 1)))
        # deltas[i] * deltas[i+1]
        products: Sequence[Gf.Vec3f] = list(map(Gf.Cross, deltas[:-1], deltas[1:]))
        # To support Python3.7 we can't use `start`
        # normal: Gf.Vec3f = sum(products, start=Gf.Vec3f(0, 0, 0))
        normal = Gf.Vec3f(0, 0, 0)
        for product in products:
            normal += product

        # compute area
        area: float = 0.0
        l: float = normal.GetLength()
        if l > 0.0:
            normal /= l
            area = 0.5 * sum(map(Gf.Dot, products, repeat(normal, len(products))))

        if abs(area) <= 0:
            return True

        index += face_size
    return False


@has_empty_faces.numpy
def _(mesh: UsdGeom.Mesh) -> bool:
    import numpy as np

    vertices: np.array = np.array(mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime()))
    indices: np.array = np.array(mesh.GetFaceVertexIndicesAttr().Get(Usd.TimeCode.EarliestTime()))
    face_sizes: np.array = np.array(mesh.GetFaceVertexCountsAttr().Get(Usd.TimeCode.EarliestTime()))

    # compute flattened vertices
    flattened: np.array = vertices.take(indices, axis=0)
    flattened_start_indices = np.concatenate([[0], np.cumsum(face_sizes)[:-1]])

    # flattened[N][i] - flattened[N][0]
    deltas = flattened - flattened.take(flattened_start_indices, axis=0).repeat(face_sizes, axis=0)

    # deltas[N][i] x deltas[N][i+1]
    deltas = deltas.astype(np.float64)
    cross_product = np.concatenate([np.cross(deltas[:-1], deltas[1:]), deltas[0:1]])

    # sum(products[N][i])
    normals = np.add.reduceat(cross_product, flattened_start_indices, axis=0)
    lengths = np.linalg.norm(normals, axis=1)
    if not lengths.all():
        return True
    unit_normal = (normals / lengths[:, np.newaxis]).repeat(face_sizes, axis=0)

    dot_product = (cross_product * unit_normal).sum(axis=1)
    areas = np.add.reduceat(dot_product, flattened_start_indices, axis=0)
    areas = abs(areas) / 2
    return not areas.all()


class RepeatedValuesSet:
    """A class that finds and manages repetitions in a sequence of values.

    This class identifies repeated values in a sequence and maps each value to its first occurrence.
    It supports both standard Python and NumPy implementations for performance optimization.

    Attributes:
        _indices: List of indices where each index points to the first occurrence of its value.
    """

    @default_implementation_method
    def __init__(self, values: VtArray[ScalarType]) -> None:
        """Creates repetitions class from size and values.

        Args:
            values: The sequence of values to check for repetitions.
        """
        size = len(values)
        indices: list[int] = [0] * size
        value_to_first_index: dict[ScalarType, int] = {}
        for i, value in enumerate(values):
            if value in value_to_first_index:
                indices[i] = value_to_first_index[value]
            else:
                indices[i] = value_to_first_index[value] = i
        self._indices = indices

    @__init__.numpy
    def _(self, values: VtArray[ScalarType]) -> None:
        """NumPy implementation of repetition finding.

        Args:
            values: The sequence of values to check for repetitions.
        """
        import numpy as np

        values_array = np.array(values)
        if values_array.ndim > 1:
            sort_idx = np.lexsort(values_array.T)
            sorted_values = np.take_along_axis(values_array, sort_idx[:, None], axis=0)
            changes = np.any(sorted_values[1:] != sorted_values[:-1], axis=1)
        else:
            sort_idx = np.argsort(values_array, kind="stable")
            sorted_values = values_array[sort_idx]
            changes = sorted_values[1:] != sorted_values[:-1]

        changes = np.concatenate(([True], changes))
        first_occurrence = sort_idx[changes]
        group_ids = np.cumsum(changes) - 1

        size = len(values)
        indices = np.arange(size)
        indices[sort_idx] = first_occurrence[group_ids]
        self._indices = indices

    @default_implementation_method
    @cache
    def __len__(self) -> int:
        """Returns the number of repetitions using standard Python."""
        repetitions: set[int] = set()
        for i, index in enumerate(self._indices):
            if i != index:
                repetitions.add(i)
                repetitions.add(index)
        return len(repetitions)

    @__len__.numpy
    @cache
    def _(self) -> int:
        """Returns the number of repetitions using NumPy."""
        import numpy as np

        indices = np.array(self._indices)
        non_self = indices != np.arange(len(indices))
        repetitions = np.unique(np.concatenate([np.where(non_self)[0], indices[non_self]]))  # positions  # targets
        return len(repetitions)

    @default_implementation_method
    @cache
    def __bool__(self) -> bool:
        """Returns true if it has repetitions using standard Python."""
        for i, index in enumerate(self._indices):
            if i != index:
                return True
        return False

    @__bool__.numpy
    @cache
    def _(self) -> bool:
        """Returns true if it has repetitions using NumPy."""
        import numpy as np

        return bool(np.any(self._indices != np.arange(len(self._indices))))

    @default_implementation_method
    def __and__(self, other: RepeatedValuesSet) -> RepeatedValuesSet:
        """Returns a new repetition object where repetitions exist in both sets."""
        return RepeatedValuesSet(list(zip(self._indices, other._indices)))

    @__and__.numpy
    def _(self, other: RepeatedValuesSet) -> RepeatedValuesSet:
        """NumPy implementation of AND operation."""
        import numpy as np

        return RepeatedValuesSet(np.column_stack((self._indices, other._indices)))


@default_implementation
def has_indexable_values(primvar: UsdGeom.Primvar) -> bool:
    """
    Args:
        primvar: The primvar to verify.

    Returns:
        True if it has indexable values.

    Raises:
        TypeError: If primvar type is not array.
        ValueError: If indices are not numeric.
        IndexError: If indices go out of bounds.
    """
    if not is_typename_array(primvar.GetTypeName()):
        raise TypeError("Primvar type is not array")

    if primvar.GetTypeName() in (
        Sdf.ValueTypeNames.BoolArray,
        Sdf.ValueTypeNames.UCharArray,
        Sdf.ValueTypeNames.IntArray,
        Sdf.ValueTypeNames.UIntArray,
        Sdf.ValueTypeNames.Int64Array,
        Sdf.ValueTypeNames.UInt64Array,
    ):
        # We don't need to index simple type arrays. They do not use more memory than indexed.
        # TODO We need to determine the array size and memory usage for Int2Array, Int3Array, Int4Array types
        return False

    if primvar.GetNamespace() == "primvars:skel":
        # OM-123165: usdSkel related primvars cannot be indexed in the same way as a regular primvar.
        # Skip primvars with "primvars:skel" namespace.
        return False

    if primvar.GetElementSize() > 1:
        # ComputeFlattened in most USD version does not work correctly with elementSize > 1
        return False
    values: VtArray[ScalarType] = primvar.ComputeFlattened(Usd.TimeCode.EarliestTime())
    if not values:
        raise IndexError("Primvar indices are invalid")
    repetitions = RepeatedValuesSet(values)
    if repetitions and not primvar.IsIndexed():
        # Repetitions but no indices?
        return True
    indices: Vt.IntArray = primvar.GetIndices()
    counter: list[int] = [0] * len(values)
    for index in indices:
        counter[index] += 1
    if sum(count for count in counter if count > 1) < len(repetitions):
        # Indices does not cover repetitions set.
        return True
    return False


def has_weldable_points(mesh: UsdGeom.Mesh) -> bool:
    points: Vt.Vec3fArray = mesh.GetPointsAttr().Get(Usd.TimeCode.EarliestTime())
    # Points
    repetitions: RepeatedValuesSet = RepeatedValuesSet(points)
    if not repetitions:
        return False

    # Collect and pre validate
    attributes: list[Usd.Attribute] = []
    attr: Usd.Attribute = mesh.GetAccelerationsAttr()
    if attr.IsAuthored():
        if attr.HasAuthoredValue() and not attr.ValueMightBeTimeVarying():
            attributes.append(attr)
        else:
            return False
    attr: Usd.Attribute = mesh.GetVelocitiesAttr()
    if attr.IsAuthored():
        if attr.HasAuthoredValue() and not attr.ValueMightBeTimeVarying():
            attributes.append(attr)
        else:
            return False
    interpolation: Tf.Token = mesh.GetNormalsInterpolation()
    if interpolation == UsdGeom.Tokens.vertex or interpolation == UsdGeom.Tokens.varying:
        attr: Usd.Attribute = mesh.GetNormalsAttr()
        if attr.IsAuthored():
            if attr.HasAuthoredValue() and not attr.ValueMightBeTimeVarying():
                attributes.append(attr)
            else:
                return False
    primvars: list[UsdGeom.Primvar] = []
    for primvar in UsdGeom.PrimvarsAPI(mesh).GetPrimvarsWithAuthoredValues():
        interpolation: Tf.Token = primvar.GetInterpolation()
        if interpolation != UsdGeom.Tokens.vertex and interpolation != UsdGeom.Tokens.varying:
            continue
        element_size: int = primvar.GetElementSize()
        if element_size > 1:
            continue
        if not primvar.ValueMightBeTimeVarying():
            primvars.append(primvar)
        else:
            return False

    # Validate
    for attr in attributes:
        values = attr.Get(Usd.TimeCode.EarliestTime())
        if len(values) != len(points):
            raise ValueError(
                f"Attribute ({attr.GetPath()}) values length "
                "does not match points length although its "
                "interpolation is vertex or varying."
            )
        repetitions &= RepeatedValuesSet(values)
        if not repetitions:
            return False

    for primvar in primvars:
        values: VtArray[ScalarType] = primvar.ComputeFlattened(Usd.TimeCode.EarliestTime())
        if len(values) != len(points):
            raise ValueError(
                f"Primvar ({primvar.GetAttr().GetPath()}) values length "
                "does not match points length although its "
                "interpolation is vertex or varying."
            )
        repetitions &= RepeatedValuesSet(values)
        if not repetitions:
            return False

    return True


@default_implementation
def has_unreferenced_values(num_values: int, indices: Vt.IntArray) -> bool:
    used_index: Sequence[bool] = [False] * num_values
    for index in indices:
        if index >= num_values:
            continue

        used_index[index] = True

    return not all(used_index)


@has_unreferenced_values.numpy
def _(num_values: int, indices: VtArray[int]) -> bool:
    """NumPy implementation of has_unreferenced_values"""
    import numpy as np

    # Create boolean array to track used indices
    used_index = np.zeros(num_values, dtype=bool)

    # Filter out invalid indices and mark used ones
    indices_array = np.array(indices)
    valid_indices = indices_array[indices_array < num_values]
    used_index[valid_indices] = True

    # Return True if any values are unreferenced (False in used_index)
    return not np.all(used_index)


def has_unreferenced_primvar(primvar: UsdGeom.Primvar) -> bool:
    """

    Args:
        primvar: The primvar to verify.

    Returns:
        True if there are values in the primvar that are unreferenced by its indices.
    """
    if not primvar.IsIndexed():
        return False
    primvar_values = primvar.Get(Usd.TimeCode.EarliestTime()) or []
    num_values: int = len(primvar_values)
    if not num_values:
        return False
    indices: Vt.IntArray = primvar.GetIndices(Usd.TimeCode.EarliestTime()) or []
    return has_unreferenced_values(num_values, indices)


@default_implementation
def has_invalid_indices(num_values: int, indices: Vt.IntArray) -> bool:
    for index in indices:
        if index >= num_values:
            return True

    return False


@has_invalid_indices.numpy
def _(num_values: int, indices: VtArray[int]) -> bool:
    """NumPy implementation of has_invalid_indices"""
    import numpy as np

    # Convert to numpy array and check for invalid indices
    indices_array = np.array(indices)
    return np.any(indices_array >= num_values)


def has_invalid_primvar_indices(primvar: UsdGeom.Primvar) -> bool:
    """

    Args:
        primvar: The primvar to verify.

    Returns:
        True if there are values in the primvar that are unreferenced by its indices.
    """
    if not primvar.IsIndexed():
        return False
    primvar_values = primvar.Get(Usd.TimeCode.EarliestTime()) or []
    num_values: int = len(primvar_values)
    indices: Vt.IntArray = primvar.GetIndices(Usd.TimeCode.EarliestTime()) or []
    return has_invalid_indices(num_values, indices)


def remove_unused_values_and_remap_indices(
    values, indices, remove_invalid_indices=False
) -> tuple[bool, list[Any], list[int], list[int]]:
    """Remove used values that are not referenced by indices array.

    Args:
        values (_type_): Value array.
        indices (_type_): Index array that references the value array.
        remove_invalid_indices (bool, optional): When it's True, it also removes those indices
                                                 that are beyond the length of value array. Defaults to False.

    Returns:
        Tuple[bool, List[Any], List[int], List[int]]: A tuple that the first item returns if the operation is successful
        or not, the second item returns the updated values after this operation, the third item returns the updated indices
        after this operation, and the last item returns all removed indices of the values in the original value array
        after this operation, which doesn't include those indices that are invalid and beyond the length of the original
        value array.
    """

    num_values: int = len(values)
    num_indices: int = len(indices)
    valid_index_count: int = 0
    valid_value_count: int = 0
    removed_value_indices = []

    if num_values == 0:
        if num_indices == 0:
            return False, values, indices, []
        else:
            return True, [], [], []

    # Count all used/unused values and valid indices.
    used_index: list[bool] = [False] * num_values
    for index in indices:
        # Index is out of the bound.
        if index >= num_values:
            continue

        valid_index_count += 1
        if not used_index[index]:
            valid_value_count += 1
        used_index[index] = True

    # No unused values or invalid indices.
    if valid_value_count == num_values and (not remove_invalid_indices or valid_index_count == num_indices):
        return False, values, indices, []

    # Remove unused values, and remap indices.
    updated_values: list[Any] = [None] * valid_value_count
    indices_remapped: list[int] = [None] * num_values
    current_index = 0
    for index, value in enumerate(values):
        if used_index[index]:
            updated_values[current_index] = value
            indices_remapped[index] = current_index
            current_index += 1
        else:
            removed_value_indices.append(index)

    updated_indices: list[int] = [0] * valid_index_count if remove_invalid_indices else [0] * num_indices
    current_index = 0
    for index in indices:
        if index >= num_values and remove_invalid_indices:
            continue

        # If it's not remapped, it means the index is over the bound and it's kept untouched
        # if remove_invalid_indices is False.
        new_index = indices_remapped[index] if index < num_values and used_index[index] else index
        updated_indices[current_index] = new_index
        current_index += 1

    return True, updated_values, updated_indices, removed_value_indices
