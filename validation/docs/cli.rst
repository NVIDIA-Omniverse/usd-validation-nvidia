Command Line Interface
######################

usage: nvidia_usd_validate [-h] [--version] [-e] [-r RULE] [-D RULE] [-c CATEGORY]
                           [--disable-category CATEGORY] [--requirement REQUIREMENT]
                           [--capability CAPABILITY] [--feature FEATURE]
                           [--disable-feature FEATURE] [--profile PROFILE]
                           [--disable-profile PROFILE] [--parameter PARAMETER]
                           [-f | --fix | --no-fix] [--stamp | --no-stamp] [-p PREDICATE]
                           [--group-by GROUP_BY]
                           [-d | --init-rules | --no-init-rules | --defaultRules | --no-defaultRules]
                           [--variants | --no-variants]
                           [--instance-prototypes | --no-instance-prototypes]
                           [--csv-output CSV] [--json-output JSON]
                           ASSET

Utility for USD validation to ensure assets run smoothly across all OpenUSD
products. Validation is based on the USD ComplianceChecker (i.e. the same
backend as the usdchecker commandline tool), and has been extended with
additional rules as follows:

- Additional rules applicable in the broader OpenUSD ecosystem.
- Configurable end-user rules that can be specific to individual company
  and/or team workflows.

Note this level of configuration requires setting the environment,
prior to launching this tool.

positional arguments:
  ASSET                 A single OpenUSD Asset.
                        | Note: This can be a file or folder.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -e, --explain         Provide descriptions for each argument provided and exit.
  -r RULE, --rule RULE, --enable-rule RULE
                        | Rule to select. Valid options include:
                        | :py:class:`UsdzPackageValidator`
                        | :py:class:`MissingReferenceChecker`
                        | :py:class:`StageMetadataChecker`
                        | :py:class:`TextureChecker`
                        | :py:class:`PrimEncapsulationChecker`
                        | :py:class:`NormalMapTextureChecker`
                        | :py:class:`KindChecker`
                        | :py:class:`ExtentsChecker`
                        | :py:class:`TypeChecker`
                        | :py:class:`IndexedPrimvarChecker`
                        | :py:class:`ManifoldChecker`
                        | :py:class:`NormalsExistChecker`
                        | :py:class:`NormalsValidChecker`
                        | :py:class:`NormalsWindingsChecker`
                        | :py:class:`SubdivisionSchemeChecker`
                        | :py:class:`UnusedMeshTopologyChecker`
                        | :py:class:`UnusedPrimvarChecker`
                        | :py:class:`ValidateTopologyChecker`
                        | :py:class:`WeldChecker`
                        | :py:class:`ZeroAreaFaceChecker`
                        | :py:class:`LayerSpecChecker`
                        | :py:class:`UsdAsciiPerformanceChecker`
                        | :py:class:`DefaultPrimChecker`
                        | :py:class:`DanglingOverPrimChecker`
                        | :py:class:`MaterialPathChecker`
                        | :py:class:`MaterialOutOfScopeChecker`
                        | :py:class:`UsdDanglingMaterialBinding`
                        | :py:class:`UsdMaterialBindingApi`
                        | :py:class:`MaterialUsdPreviewSurfaceChecker`
                        | :py:class:`ShaderImplementationSourceChecker`
                        | :py:class:`MaterialOldMdlSchemaChecker`
                        | :py:class:`UnicodeNameChecker`
                        | :py:class:`UsdGeomSubsetChecker`
                        | :py:class:`UsdLuxSchemaChecker`
                        | :py:class:`SkelBindingAPIAppliedChecker`
                        | :py:class:`RigidBodyChecker`
                        | :py:class:`ColliderChecker`
                        | :py:class:`PhysicsJointChecker`
                        | :py:class:`ArticulationChecker`
                        | :py:class:`MassChecker` (default: [])
  -D RULE, --disable-rule RULE, --disableRules RULE
                        | Rule to disable. Valid options include:
                        | :py:class:`UsdzPackageValidator`
                        | :py:class:`MissingReferenceChecker`
                        | :py:class:`StageMetadataChecker`
                        | :py:class:`TextureChecker`
                        | :py:class:`PrimEncapsulationChecker`
                        | :py:class:`NormalMapTextureChecker`
                        | :py:class:`KindChecker`
                        | :py:class:`ExtentsChecker`
                        | :py:class:`TypeChecker`
                        | :py:class:`IndexedPrimvarChecker`
                        | :py:class:`ManifoldChecker`
                        | :py:class:`NormalsExistChecker`
                        | :py:class:`NormalsValidChecker`
                        | :py:class:`NormalsWindingsChecker`
                        | :py:class:`SubdivisionSchemeChecker`
                        | :py:class:`UnusedMeshTopologyChecker`
                        | :py:class:`UnusedPrimvarChecker`
                        | :py:class:`ValidateTopologyChecker`
                        | :py:class:`WeldChecker`
                        | :py:class:`ZeroAreaFaceChecker`
                        | :py:class:`LayerSpecChecker`
                        | :py:class:`UsdAsciiPerformanceChecker`
                        | :py:class:`DefaultPrimChecker`
                        | :py:class:`DanglingOverPrimChecker`
                        | :py:class:`MaterialPathChecker`
                        | :py:class:`MaterialOutOfScopeChecker`
                        | :py:class:`UsdDanglingMaterialBinding`
                        | :py:class:`UsdMaterialBindingApi`
                        | :py:class:`MaterialUsdPreviewSurfaceChecker`
                        | :py:class:`ShaderImplementationSourceChecker`
                        | :py:class:`MaterialOldMdlSchemaChecker`
                        | :py:class:`UnicodeNameChecker`
                        | :py:class:`UsdGeomSubsetChecker`
                        | :py:class:`UsdLuxSchemaChecker`
                        | :py:class:`SkelBindingAPIAppliedChecker`
                        | :py:class:`RigidBodyChecker`
                        | :py:class:`ColliderChecker`
                        | :py:class:`PhysicsJointChecker`
                        | :py:class:`ArticulationChecker`
                        | :py:class:`MassChecker` (default: [])
  -c CATEGORY, --category CATEGORY, --enable-category CATEGORY
                        | Category to select. Valid options include:
                        | :py:class:`Basic`
                        | :py:class:`Geometry`
                        | :py:class:`Layer`
                        | :py:class:`Layout`
                        | :py:class:`Material`
                        | :py:class:`Other`
                        | :py:class:`Physics` (default: [])
  --disable-category CATEGORY
                        | Category to disable. Valid options include:
                        | :py:class:`Basic`
                        | :py:class:`Geometry`
                        | :py:class:`Layer`
                        | :py:class:`Layout`
                        | :py:class:`Material`
                        | :py:class:`Other`
                        | :py:class:`Physics` (default: [])
  --requirement REQUIREMENT
                        | Requirement to add. Valid options include:
                        | AA.001
                        | AA.001@1.0.0
                        | AA.002
                        | AA.002@1.0.0
                        | AA.003
                        | AA.003@1.0.0
                        | AA.OV.001
                        | AA.OV.001@1.0.0
                        | HI.001
                        | HI.001@1.0.0
                        | HI.003
                        | HI.003@1.0.0
                        | HI.004
                        | HI.004@1.0.0
                        | JT.002
                        | JT.002@1.0.0
                        | JT.003
                        | JT.003@1.0.0
                        | JT.ART.002
                        | JT.ART.002@1.0.0
                        | JT.ART.004
                        | JT.ART.004@1.0.0
                        | RB.003
                        | RB.003@1.0.0
                        | RB.005
                        | RB.005@1.0.0
                        | RB.007
                        | RB.007@1.0.0
                        | RB.009
                        | RB.009@1.0.0
                        | RB.COL.004
                        | RB.COL.004@1.0.0
                        | UN.001
                        | UN.001@1.0.0
                        | UN.002
                        | UN.002@1.0.0
                        | UN.006
                        | UN.006@1.0.0
                        | UN.007
                        | UN.007@1.0.0
                        | VG.002
                        | VG.002@1.0.0
                        | VG.007
                        | VG.007@1.0.0
                        | VG.009
                        | VG.009@1.0.0
                        | VG.010
                        | VG.010@1.0.0
                        | VG.011
                        | VG.011@1.0.0
                        | VG.014
                        | VG.014@1.0.0
                        | VG.016
                        | VG.016@1.0.0
                        | VG.018
                        | VG.018@1.0.0
                        | VG.019
                        | VG.019@1.0.0
                        | VG.020
                        | VG.020@1.0.0
                        | VG.025
                        | VG.025@1.0.0
                        | VG.027
                        | VG.027@1.0.0
                        | VG.028
                        | VG.028@1.0.0
                        | VG.029
                        | VG.029@1.0.0
                        | VG.035
                        | VG.035@1.0.0
                        | VG.MESH.001
                        | VG.MESH.001@1.0.0
                        | VG.RTX.001
                        | VG.RTX.001@1.0.0
                        | VM.BIND.001
                        | VM.BIND.001@1.0.0
                        | VM.MDL.001
                        | VM.MDL.001@1.0.0
                        | VM.MDL.002
                        | VM.MDL.002@1.0.0
                        | VM.PS.001
                        | VM.PS.001@1.0.0 (default: [])
  --capability CAPABILITY
                        | Capability to add. Valid options include:
                        | atomic_asset
                        | atomic_asset@1.0.0
                        | dense_captions
                        | dense_captions@1.0.0
                        | geometry
                        | geometry@1.0.0
                        | hierarchy
                        | hierarchy@1.0.0
                        | materials
                        | materials@1.0.0
                        | nonvisual_materials
                        | nonvisual_materials@1.0.0
                        | physics_joints
                        | physics_joints@1.0.0
                        | physics_rigid_bodies
                        | physics_rigid_bodies@1.0.0
                        | semantic_labels
                        | semantic_labels@1.0.0
                        | units
                        | units@1.0.0 (default: [])
  --feature FEATURE, --enable-feature FEATURE
                        | Feature to enable. Valid options include:
                        | minimal_placeable_visual
                        | minimal_placeable_visual@1.0.0
                        | performant_placeable_visual
                        | performant_placeable_visual@0.0.1 (default: [])
  --disable-feature FEATURE
                        | Feature to disable. Valid options include:
                        | minimal_placeable_visual
                        | minimal_placeable_visual@1.0.0
                        | performant_placeable_visual
                        | performant_placeable_visual@0.0.1 (default: [])
  --profile PROFILE, --enable-profile PROFILE
                        | Profile to enable. Valid options include: (default: [])
  --disable-profile PROFILE
                        | Profile to disable. Valid options include: (default: [])
  --parameter PARAMETER
                        | Parameter to override in NAME=VALUE format. Can be specified multiple times. (default: [])
  -f, --fix, --no-fix   Whether to fix issues. (default: False)
  --stamp, --no-stamp   Stamp the asset's metadata with validation profile info after successful validation. Requires --profile. (default: False)
  -p PREDICATE, --predicate PREDICATE
                        | Predicate to select. Valid options include:
                        | Any
                        | HasRootLayer
                        | IsError
                        | IsFailure
                        | IsWarning (default: None)
  --group-by GROUP_BY   Group by. Valid options include:
                        | requirement
                        | rule_name (default: None)
  -d, --init-rules, --no-init-rules, --defaultRules, --no-defaultRules
                        | Whether to use the default enabled validation rules.
                        | Opt-out of this behavior to gain finer control over
                        | the rules using the --categories and --rules flags. (default: True)
  --variants, --no-variants
                        | Whether to set variants. Note: This can be expensive. (default: True)
  --instance-prototypes, --no-instance-prototypes
                        | Whether to process instance proxy prims for every instance.
                        | Disabling this can speed up heavily instanced stages. (default: True)
  --csv-output CSV      Path to the CSV output file. (default: None)
  --json-output JSON    Path to the JSON output file. (default: None)

See https://github.com/NVIDIA-Omniverse/usd-validation-nvidia for more details.
