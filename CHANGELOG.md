# Changelog

## [1.18.2] - 2026-05-05
### Added
- `omni.asset_validator` compatibility shims

### Fixed
- Use the package version constant for version reporting

## [1.18.1] - 2026-04-29
### Added
- `FormatDependencyId` identifier and `FormatDependency` added to `AtType`, allowing rules to pass `at=dependency` in `_AddFailedCheck` and related methods from `CheckFormatDependency`
- `pathlib.Path` support in `IsAnIssue.at_cmp` for asserting `FormatDependencyId` locations in tests

## [1.18.0] - 2026-04-27
### Added
- `AssetFormat` protocol and registry for non-USD asset formats
- `CheckFormatDependency` callback and `FormatDependency` context object
- `basename` and `relative_uri` methods on `UriResolver` protocol

### Changed
- Remove SimReady validators from core
- Update repo USD profiles to 1.11.2

### Fixed
- Handle deprecated `GetNdrType` on `SdfTypeIndicator`
- Resolve plugin manager limitations: remove isolated environment variable, support `nvidia_usd_validation.X` import syntax

## [1.17.0] - 2026-04-17
### Added
- Profile auto-detection mode: validate an asset against all registered profiles automatically
- Validation stamp and profile support in the asset validator
- `ValidationContext` per `Results` for per-asset profile compliance
- `UriResolver` protocol with `parent_uri` and `join_uri`, extracted from `ValidationEngine`
- `GaussianSplatSchemaChecker`: validates ParticleField3DGaussianSplat prims (required attributes, array consistency, value ranges, spherical harmonics)

## [1.16.0] - 2026-04-14
### Added
- Add full Profile support to Engine, CLI, and UI
- Add tree-structured validation report for profiles and features

## [1.15.1] - 2026-03-24
### Changed
- No changes

## [1.15.0] - 2026-03-22
### Added
- Multiple suggestions per issue
### Changed
- Explicit lifecycle management for capability, feature and profile registries
- Add logging to `register_*`/`unregister_*` functions
- Introduce `@singleton` decorator to hide `cache_clear` from registries
### Fixed
- `ComplianceChecker` should not reset externally-owned stats

## [1.14.0] - 2026-03-16
### Added
- Add autovalidate setting to skip re-validation after fix
- Add `IdVersion` to the public API
- `VersionedRegistry.find` now searches for a compatible version rather than an exact match
### Changed
- Physics validation uses USD native validators, with fallback if unavailable
- Use `ResolverScopedCache` to avoid redundant asset resolver calls per batch
### Fixed
- Fix `UsdzUdimLimitationChecker` to use `CheckPrim` instead of opening USDZ as a second stage
- Fix misleading tutorial path placeholders

## [1.13.0] - 2026-03-10
### Added
- Register core validators as entrypoint plugin

## [1.12.0] - 2026-02-26
### Added
- `register_capability`, `unregister_capability` and `add_registry_capability_callback`.
- `register_feature`, `unregister_feature` and `add_registry_feature_callback`.
- `register_profile`, `unregister_profile` and `add_registry_profile_callback`.
- `PluginManager` and `PluginProtocol`.
### Changed
- `SemVer` support for NoneType.

## [1.11.2] - 2026-02-25
### Fixed
- Fixed removal of Issue.code

## [1.11.1] - 2026-02-17
### Added
- CLI: Add JSON output option.
### Fixed
- MaterialUsdPreviewSurfaceChecker: Respect interfaceOnly connectability when validating input connections.

## [1.11.0] - 2026-02-11
### Added
- CLI: Add --group-by option (rule_name, requirement).
- minimal-placeable-visual: Add missing implementation to MVP.
- asset-at-origin spec: Invalid examples for translate, rotate, scale and combinations.
### Changed
- hierarchy-has-root: See changes in the specification.
### Fixed
- PortableAssetPathChecker: Fix missing addedItems in list of ops.
- unregister_requirements: Bug when removing multiple versions.
- UsdValidationAdapter: Better handling of missing shared library.

## [1.10.8] - 2026-02-08
### Fixed
- Fix pip install.

## [1.10.7] - 2026-02-06
### Fixed
- RequirementsRegistry: get_requirements fix.
- ComplianceChecker: Use Sdf.ZipFile instead.

## [1.10.6] - 2026-01-27
### Fixed
- Fix mangled names.
- Fix requirements-table references to not duplicate in toctree.
- Fix enable_capability, disable_capability, enable_feature, disable_feature.

## [1.10.5] - 2026-01-15
### Fixed
- Fix links in documentation.

## [1.10.4] - 2026-01-14
### Added
- usdgeom-invisible-prims requirement.

## [1.10.3] - 2026-01-09
### Added
- usdgeom-mesh-internal-geometry requirement, add CHECK_TRANSPARENCY parameter.

## [1.10.2] - 2026-01-09
### Added
- usdgeom-mesh-internal-geometry requirement, add parameters.

## [1.10.1] - 2026-01-08
### Changed
- ValidationEngine: Revert adapt validation engine to accept async methods.
### Fixed
- Fix capabilities URL.

## [1.10.0] - 2026-01-06
### Added
- Add usdgeom-unused-uvs requirement.
- Add performant placeable visual feature.
### Changed
- ValidationEngine: Adapt validation engine to accept async methods.
- Suggestion/Fixer: Use EditTargetId in Suggestion and Fixer.
- Requirements: Use the new Requirements enumeration.
- Update repo_usd_profiles.
- Update specifications to properly format the examples.

## [1.9.2] - 2025-12-11
### Fixed
- Performance Geometry: Rules disabled by default.

## [1.9.1] - 2025-12-10
### Fixed
- AtomicAsset: Rules disabled by default.

## [1.9.0] - 2025-12-09
### Added
- ComplianceChecker: Add async methods for compliance checking.
### Changed
- UsdzPackageValidator: Use the new UsdzPackageValidator from Pixar.
### Fixed
- Parameters: Additional fixes for parameter handling.

## [1.8.0] - 2025-11-20
### Fixed
- unregister_requirements: Fix a bug when removing multiple requirements.
- Parameters: Fix stacking multiple user parameters overrides.
### Changed
- Issue: Validate suggestion is of type suggestion.
- Suggestion: Validate callable is a callable.

## [1.7.1] - 2025-11-11
### Changed
- OpenUSD profiles dependency updated.

## [1.7.0] - 2025-11-06
### Added
- ValidationEngine: Accept parameters
- NormalsExistChecker: New validator.
- NormalsValidChecker: New validator.
- NormalsWindingsChecker: New validator.
- BaseRuleChecker: Use parameters.
### Changed
- ComplianceChecker: Stage jobs run in background
- CLI: Improved test coverage.
- Requirements: Improve requirements documentation.
### Fixed
- RigidBodyChecker: Mismatch in error behavior for scene loading/simulation.
- CLI: Remove deprecation warnings.
- CLI: Accept parameters.
- ComplianceChecker: Pass the Asset Resolver Context to background thread.

## [1.6.0] - 2025-10-20
### Added
- Added parameter protocol
### Changed
- Requirements: Added parameter attribute
- BaseRuleChecker: Added parameter property
- ComplianceChecker: Added support for parameters

## [1.5.0] - 2025-10-10
### Added
- CLI: Add features.
### Changed
- RequirementsRegistry: Add support for versions in requirements.
- register_rule: Add override parameter.
### Fixed
- WeldChecker: Fix None type exception.

## [1.4.3] - 2025-10-01
### Changed
- Update requirements, includes version.
### Fixed
- ValidationEngine: Fix bug when progress does not start at 0%.

## [1.4.2] - 2025-09-24
### Changed
- Updated shader registry API usage for 25.08 compatbility.

## [1.4.1] - 2025-09-19
### Changed
- Update capabilities.
- Update PrimId class definition.

## [1.4.0] - 2025-09-15
### Added
- EventListener, EventStream: classes to manage event notifications.
- add_registry_requirement_callback: Add callbacks when RequirementsRegistry changes.
### Changed
- ExtentsChecker: Add requirements.
- NormalsExistChecker: Warn and suggest to remove normals if both normals and primvars:normals exist.
- SubdivisionSchemeChecker: Update subdivision validator to limit scope to only check the subdivisionScheme is defined.

## [1.3.1] - 2025-09-01
### Changed
- Update capabilities
- Guard PcpNodeRef, in case it is invalid.

## [1.3.0] - 2025-08-21
### Added
- NormalsExistChecker: Checker for existence of normals.

## [1.2.1] - 2025-08-19
### Added
- Updated documentation.

## [1.2.0] - 2025-08-18
### Changed
- Updated PyPi links.
