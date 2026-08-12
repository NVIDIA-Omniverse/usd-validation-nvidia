Rules
#####

.. automodule:: usd_validation_nvidia
    :noindex:
    :platform: Windows-x86_64, Linux-x86_64

.. autoclass:: UsdzPackageValidator()
.. autoclass:: MissingReferenceChecker()
.. autoclass:: StageMetadataChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`UN.001 </specs/capabilities/core/units/requirements/upaxis>` :doc:`UN.002 </specs/capabilities/core/units/requirements/meters-per-unit>`
.. autoclass:: TextureChecker()
.. autoclass:: PrimEncapsulationChecker()
.. autoclass:: NormalMapTextureChecker()
.. autoclass:: KindChecker()
.. autoclass:: ExtentsChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.002 </specs/capabilities/geometry/requirements/usdgeom-extent>`
.. autoclass:: TypeChecker()
.. autoclass:: IndexedPrimvarChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.009 </specs/capabilities/geometry/requirements/usdgeom-mesh-primvar-indexing>`
.. autoclass:: ManifoldChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.007 </specs/capabilities/geometry/requirements/usdgeom-mesh-manifold>`
.. autoclass:: NormalsExistChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.027 </specs/capabilities/geometry/requirements/usdgeom-mesh-normals-exist>`
.. autoclass:: NormalsValidChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.028 </specs/capabilities/geometry/requirements/usdgeom-mesh-normals-must-be-valid>`
.. autoclass:: NormalsWindingsChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.029 </specs/capabilities/geometry/requirements/usdgeom-mesh-winding-order>`
.. autoclass:: SubdivisionSchemeChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.010 </specs/capabilities/geometry/requirements/usdgeom-mesh-subdivision>`
.. autoclass:: UnusedMeshTopologyChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.018 </specs/capabilities/geometry/requirements/usdgeom-mesh-unused-topology>`
.. autoclass:: UnusedPrimvarChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.011 </specs/capabilities/geometry/requirements/usdgeom-mesh-primvar-usage>`
.. autoclass:: ValidateTopologyChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.014 </specs/capabilities/geometry/requirements/usdgeom-mesh-topology>`
.. autoclass:: WeldChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.016 </specs/capabilities/geometry/requirements/usdgeom-mesh-colocated-points>`
.. autoclass:: ZeroAreaFaceChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VG.019 </specs/capabilities/geometry/requirements/usdgeom-mesh-zero-area-faces>`
.. autoclass:: LayerSpecChecker()
.. autoclass:: UsdAsciiPerformanceChecker()
.. autoclass:: DefaultPrimChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`HI.004 </specs/capabilities/hierarchy/requirements/stage-has-default-prim>`
.. autoclass:: DanglingOverPrimChecker()
.. autoclass:: MaterialPathChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VM.MDL.001 </specs/capabilities/materials/requirements/material-mdl-source-asset>`
.. autoclass:: MaterialOutOfScopeChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VM.BIND.001 </specs/capabilities/materials/requirements/material-bind-scope>`
.. autoclass:: UsdDanglingMaterialBinding()
.. autoclass:: UsdMaterialBindingApi()
.. autoclass:: MaterialUsdPreviewSurfaceChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VM.PS.001 </specs/capabilities/materials/requirements/material-preview-surface>`
.. autoclass:: ShaderImplementationSourceChecker()
.. autoclass:: MaterialOldMdlSchemaChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`VM.MDL.002 </specs/capabilities/materials/requirements/material-mdl-schema>`
.. autoclass:: UnicodeNameChecker()
.. autoclass:: UsdGeomSubsetChecker()
.. autoclass:: UsdLuxSchemaChecker()
.. autoclass:: SkelBindingAPIAppliedChecker()
.. autoclass:: RigidBodyChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`RB.005 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-no-instancing>` :doc:`RB.003 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-schema-application>` :doc:`RB.009 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-schema-no-skew-matrix>`
.. autoclass:: ColliderChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`RB.COL.004 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/collider-non-uniform-scale>`
.. autoclass:: PhysicsJointChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`JT.002 </specs/capabilities/physics_bodies/physics_joints/requirements/joint-body-target-exists>` :doc:`JT.003 </specs/capabilities/physics_bodies/physics_joints/requirements/joint-no-multiple-body-targets>`
.. autoclass:: ArticulationChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`JT.ART.002 </specs/capabilities/physics_bodies/physics_joints/requirements/articulation-no-nesting>` :doc:`JT.ART.004 </specs/capabilities/physics_bodies/physics_joints/requirements/articulation-not-on-static-body>`
.. autoclass:: MassChecker()

   .. list-table::
       :width: 100%

       * - Requirements
       * - :doc:`RB.007 </specs/capabilities/physics_bodies/physics_rigid_bodies/requirements/rigid-body-mass>`
