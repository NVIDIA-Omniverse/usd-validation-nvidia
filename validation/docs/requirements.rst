Requirements
############

.. automodule:: usd_validation_nvidia
    :noindex:
    :platform: Windows-x86_64, Linux-x86_64

.. list-table::
   :header-rows: 1
   :width: 100%

   * - Code
     - Message
     - Rule
   * - :doc:`AA.002 </specs/capabilities/core/atomic_asset/requirements/supported-file-types>`
     - Asset must use only supported file types
     - :py:class:`SupportedFileTypesChecker`
   * - :doc:`AA.001 </specs/capabilities/core/atomic_asset/requirements/anchored-asset-paths>`
     - Asset references should use anchored paths
     - :py:class:`AnchoredAssetPathsChecker`
   * - :doc:`AA.OV.001 </specs/capabilities/core/atomic_asset/requirements/ov-usdz-udim-limitation>`
     - Texture UDIMs are not supported in USDZ files in NVIDIA Omniverse
     - :py:class:`UsdzUdimLimitationChecker`
   * - :doc:`AA.003 </specs/capabilities/core/atomic_asset/requirements/portable-asset-paths>`
     - Asset paths should use forward slashes for cross-platform portability
     - :py:class:`PortableAssetPathChecker`
   * - :doc:`UN.001 </specs/capabilities/core/units/requirements/upaxis>`
     - Stage must specify upAxis to define the orientation of the stage
     - :py:class:`StageMetadataChecker`
   * - :doc:`UN.002 </specs/capabilities/core/units/requirements/meters-per-unit>`
     - Stage must specify metersPerUnit to define the linear unit scale
     - :py:class:`StageMetadataChecker`
   * - :doc:`VG.002 </specs/capabilities/geometry/requirements/usdgeom-extent>`
     - Boundable geometry primitives should have valid extent values.
     - :py:class:`ExtentsChecker`
   * - :doc:`VG.010 </specs/capabilities/geometry/requirements/usdgeom-mesh-subdivision>`
     - Do not subdivide meshes with Normals.
     - :py:class:`SubdivisionSchemeChecker`
   * - :doc:`VG.007 </specs/capabilities/geometry/requirements/usdgeom-mesh-manifold>`
     - Mesh geometry must be manifold
     - :py:class:`ManifoldChecker`
   * - :doc:`VG.009 </specs/capabilities/geometry/requirements/usdgeom-mesh-primvar-indexing>`
     - Use indexed primvars when values are repeated
     - :py:class:`IndexedPrimvarChecker`
   * - :doc:`VG.018 </specs/capabilities/geometry/requirements/usdgeom-mesh-unused-topology>`
     - Mesh topology should be without unused vertices, edges, or faces.
     - :py:class:`UnusedMeshTopologyChecker`
   * - :doc:`VG.019 </specs/capabilities/geometry/requirements/usdgeom-mesh-zero-area-faces>`
     - Faces should have non-zero area.
     - :py:class:`ZeroAreaFaceChecker`
   * - :doc:`VG.016 </specs/capabilities/geometry/requirements/usdgeom-mesh-colocated-points>`
     - Each vertex position should be unique
     - :py:class:`WeldChecker`
   * - :doc:`VG.014 </specs/capabilities/geometry/requirements/usdgeom-mesh-topology>`
     - Mesh topology must be valid
     - :py:class:`ValidateTopologyChecker`
   * - :doc:`VG.011 </specs/capabilities/geometry/requirements/usdgeom-mesh-primvar-usage>`
     - Only include primvars that are actively used
     - :py:class:`UnusedPrimvarChecker`
   * - :doc:`VG.027 </specs/capabilities/geometry/requirements/usdgeom-mesh-normals-exist>`
     - All non-subdivided meshes must have normals.
     - :py:class:`NormalsExistChecker`
   * - :doc:`VG.028 </specs/capabilities/geometry/requirements/usdgeom-mesh-normals-must-be-valid>`
     - Mesh normals values must be valid to produce correct shading.
     - :py:class:`NormalsValidChecker`
   * - :doc:`VG.029 </specs/capabilities/geometry/requirements/usdgeom-mesh-winding-order>`
     - The winding order of faces in a mesh must correctly represent the orientation (front/back) of the face.
     - :py:class:`NormalsWindingsChecker`
   * - :doc:`VG.MESH.001 </specs/capabilities/geometry/requirements/geom-shall-be-mesh>`
     - All geometry shall be represented as non-subdivided mesh primitives using the UsdGeomMesh schema.
     - :py:class:`ContainsMeshChecker`
   * - :doc:`VG.025 </specs/capabilities/geometry/requirements/asset-at-origin>`
     - Geometry shall be defined as such that the asset is correctly positioned and oriented at the origin (0,0,0).
     - :py:class:`AssetOriginPositioningChecker`
   * - :doc:`HI.004 </specs/capabilities/hierarchy/requirements/stage-has-default-prim>`
     - Stage must specify a default prim to define the root entry point.
     - :py:class:`DefaultPrimChecker`
   * - :doc:`VM.MDL.001 </specs/capabilities/materials/requirements/material-mdl-source-asset>`
     - MDL material source assets must be properly referenced and accessible to ensure material loading and rendering.
     - :py:class:`MaterialPathChecker`
   * - :doc:`VM.BIND.001 </specs/capabilities/materials/requirements/material-bind-scope>`
     - Material bindings must use appropriate scope to ensure proper material assignment and inheritance.
     - :py:class:`MaterialOutOfScopeChecker`
   * - :doc:`VM.PS.001 </specs/capabilities/materials/requirements/material-preview-surface>`
     - Material attributes must comply with the UsdPreviewSurface specification to ensure consistent rendering and viewer compatibility.
     - :py:class:`MaterialUsdPreviewSurfaceChecker`
   * - :doc:`VM.MDL.002 </specs/capabilities/materials/requirements/material-mdl-schema>`
     - MDL Shaders must use standard OpenUSD shader source attributes to ensure compatibility.
     - :py:class:`MaterialOldMdlSchemaChecker`
   * - :doc:`RB.005 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-no-instancing>`
     - Rigid bodies cannot be part of a scene graph instance.
     - :py:class:`RigidBodyChecker`
   * - :doc:`RB.003 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-schema-application>`
     - Rigid bodies have to be UsdGeomXformable prims.
     - :py:class:`RigidBodyChecker`
   * - :doc:`RB.009 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-schema-no-skew-matrix>`
     - Rigid bodies have to be UsdGeomXformable prims without skew matrix.
     - :py:class:`RigidBodyChecker`
   * - :doc:`RB.COL.004 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/collider-non-uniform-scale>`
     - The collision shape scale must be uniform for the following geometries: Sphere, Capsule, Cylinder, Cone & Points.
     - :py:class:`ColliderChecker`
   * - :doc:`JT.002 </specs/capabilities/physics_bodies/physics_joints/requirements/joint-body-target-exists>`
     - Targets set to Body0 and Body1 relationships must exist.
     - :py:class:`PhysicsJointChecker`
   * - :doc:`JT.003 </specs/capabilities/physics_bodies/physics_joints/requirements/joint-no-multiple-body-targets>`
     - Body0 and Body1 relationships must not have more than one target.
     - :py:class:`PhysicsJointChecker`
   * - :doc:`JT.ART.002 </specs/capabilities/physics_bodies/physics_joints/requirements/articulation-no-nesting>`
     - Articulation roots cannot be nested.
     - :py:class:`ArticulationChecker`
   * - :doc:`JT.ART.004 </specs/capabilities/physics_bodies/physics_joints/requirements/articulation-not-on-static-body>`
     - Articulations are not allowed on static bodies.
     - :py:class:`ArticulationChecker`
   * - :doc:`RB.007 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-mass>`
     - Rigid bodies _or_ their descendent collision shapes should have a mass & their other inertial properties explicitly specified.
     - :py:class:`MassChecker`
   * - :doc:`VG.035 </specs/capabilities/geometry/requirements/usdgeom-particle-field-gaussian-splat>`
     - `ParticleField3DGaussianSplat` prims must satisfy schema and data consistency rules required for interoperable 3D Gaussian splat assets.
     - :py:class:`GaussianSplatSchemaChecker`
   * - :doc:`HI.001 </specs/capabilities/hierarchy/requirements/hierarchy-has-root>`
     - Prim hierarchy must have a single root prim.
     - :py:class:`HierarchyHasRootChecker`
   * - :doc:`HI.003 </specs/capabilities/hierarchy/requirements/root-is-xformable>`
     - The root prim of the asset hierarchy must be transformable
     - :py:class:`RootPrimXformableChecker`
   * - :doc:`VG.RTX.001 </specs/capabilities/geometry/requirements/usdgeom-boundable-size-rtx-limit>`
     - World space bounds must not exceed RTX limit.
     - :py:class:`AlmostExtremeExtentChecker`
   * - :doc:`VG.020 </specs/capabilities/geometry/requirements/usdgeom-pointbased-points-precision>`
     - The values of the points attribute must not exceed the limit at which a given precision can be represented using 32-bit floats.
     - :py:class:`PointsPrecisionChecker`
   * - :doc:`UN.006 </specs/capabilities/core/units/requirements/upaxis-z>`
     - Stage must specify upAxis = "Z" to define the orientation of the stage
     - :py:class:`UpAxisZChecker`
   * - :doc:`UN.007 </specs/capabilities/core/units/requirements/meters-per-unit-1>`
     - Stage must specify metersPerUnit = 1.0 to define the linear unit scale
     - :py:class:`UnitsInMetersChecker`
