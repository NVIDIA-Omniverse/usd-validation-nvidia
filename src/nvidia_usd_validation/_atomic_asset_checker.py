# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import os
from pathlib import Path

import nvidia_usd_validation.capabilities as cap
from pxr import Ar, Sdf, Usd, UsdShade, UsdUtils

from ._base_rule_checker import BaseRuleChecker
from ._categories import register_rule
from ._requirements import register_requirements

__all__ = [
    "AnchoredAssetPathsChecker",
    "SupportedFileTypesChecker",
    "UsdzUdimLimitationChecker",
]


@register_rule("AtomicAsset", skip=True)
@register_requirements(cap.Requirements.AA_002)
class SupportedFileTypesChecker(BaseRuleChecker):
    """
    For maximum portability, assets should only use file types that are widely supported across platforms.
    This includes specific formats for USD files, images, and audio.
    Use only the following file types:
    USD files: usda, usdc, usd, usdz
    Image files: png, jpeg/jpg, exr
    Audio files: M4A, MP3, WAV
    """

    _ALLOWED_FILE_EXTENSIONS = ["usda", "usdc", "usd", "usdz", "png", "jpeg", "jpg", "exr", "m4a", "mp3", "wav"]

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self._processed_paths: set[str] = set()

    def _check_and_record_file_extension(self, path):
        """
        Check if the file extension is allowed.
        """
        # Empty path is allowed.
        if not path:
            return True

        file_extension = Sdf.FileFormat.GetFileExtension(path)

        if file_extension == "mdl":
            self._AddWarning(
                requirement=cap.Requirements.AA_002,
                message=f"MDL (.mdl) materials may not render correctly outside of Omniverse. For better compatibility, consider using USDPreviewSurface or MaterialX / OpenPBR. Path: {path}",
            )
        elif file_extension not in SupportedFileTypesChecker._ALLOWED_FILE_EXTENSIONS:
            self._record_failed_check(path)

    def _record_failed_check(self, path):
        """
        Add a failed check for the given path.
        """
        self._AddFailedCheck(
            requirement=cap.Requirements.AA_002,
            message=f"Dependent file '{path}' is not a supported file type.",
        )

    def CheckZipFile(self, zip_file: Usd.ZipFile, package_path: str):
        """
        Scan all files in the usdz file and check if they are allowed.
        """
        # NOTE: We shouldn't need to use UsdUtils.ExtractExternalReferences or UsdUtils.ComputeAllDependencies because
        # the usdz file should be self-contained.
        if not zip_file:
            # This might be caused by a unresolved path.
            self._AddError(message=f"Could not open usdz package at path '{package_path}'.")
            return
        file_names = zip_file.GetFileNames()
        for file_name in file_names:
            self._check_and_record_file_extension(file_name)

    def _check_file_types(self, paths: list[str]):
        """
        Check the file types of the given paths.
        """
        for path in set(paths):
            if path in self._processed_paths:
                continue
            self._processed_paths.add(path)
            self._check_and_record_file_extension(path)

    def CheckUnresolvedPaths(self, unresolvedPaths: list[str]):
        """
        We check the file types of all unresolved paths.
        """
        self._check_file_types(unresolvedPaths)

    def CheckDependencies(self, _, layer_deps: list[Sdf.Layer], asset_deps: list[str]):
        """
        We check the file types of all layer_deps and asset_deps.
        """
        self._check_file_types([layer.realPath for layer in layer_deps] + asset_deps)


@register_rule("AtomicAsset", skip=True)
@register_requirements(cap.Requirements.AA_001)
class AnchoredAssetPathsChecker(BaseRuleChecker):
    """
    Asset references should use anchored paths.
    For reproducible results, asset references should use anchored paths (paths that begin with "./" or "../")
    rather than absolute paths or search paths. Paths containing "../" should also be encapsulated and
    avoid to target locations above the asset root.
    """

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self._processed_layers: set[Sdf.Layer] = set()
        self._dependencies: set[str] = set()
        self._stage: Usd.Stage | None = None

    @property
    def _asset_root(self) -> Usd.Stage:
        if not self._stage:
            raise RuntimeError("Stage is not set. No asset root can be determined.")
        return Path(os.path.dirname(os.path.abspath(self._stage.GetRootLayer().realPath))).resolve()

    @staticmethod
    def _is_usdz_layer(layer):
        """
        Check if the layer is a USDZ file.
        """
        return layer.GetFileFormat().IsPackage() or Ar.IsPackageRelativePath(layer.identifier)

    def _record_failed_check(self, message: str, at: Sdf.Layer | None = None):
        """
        Add a failed check for the given path, with optional failure location and dependency_type.
        """
        self._AddFailedCheck(
            requirement=cap.Requirements.AA_001,
            message=message,
            at=at,
        )

    def _resolve_path(self, asset_path: str, anchor_path: str | Ar.ResolvedPath) -> str:
        """
        Resolve the path to the asset.
        """
        if isinstance(anchor_path, str):
            anchor_path = Ar.ResolvedPath(anchor_path)
        resolver = Ar.GetResolver()
        resolved = resolver.Resolve(resolver.CreateIdentifier(asset_path, anchor_path))
        return resolved.GetPathString() if resolved else ""

    def _is_within_asset_root(self, asset_path: str) -> bool:
        """
        Check if the given asset_path is within the anchor_path.
        """
        return self._asset_root in Path(asset_path).resolve().parents

    def _check_valid_anchored_path(
        self,
        asset_path: str | Sdf.AssetPath,
        layer: Sdf.Layer = None,
        prim: Usd.Prim = None,
        dependency_type: str = "",
    ):
        """
        Check if the given path is a valid anchored path.
        """
        if isinstance(asset_path, Sdf.AssetPath):
            asset_path = asset_path.path

        # Empty asset path is ok for this checker.
        if not asset_path:
            return

        msg = f'Dependent {dependency_type} "{asset_path}"'
        # In the SearchPath case, only MDL search paths are allowed, and a warning will be issued. OMPE-46019
        if "/" not in asset_path and Sdf.FileFormat.GetFileExtension(asset_path) == "mdl":
            self._AddWarning(
                requirement=cap.Requirements.AA_001,
                message=f"MDL (.mdl) asset {asset_path} relies on a search path. Materials will not load outside of Omniverse, or may differ between Omniverse versions.",
                at=prim or layer,
            )
            return

        # Not anchored relative path case - we only allow "./" or "../"
        if not asset_path.startswith("./") and not asset_path.startswith("../"):
            message = f'{msg} should begin with "./" or "../".'
            self._record_failed_check(message=message, at=prim or layer)
            return

        # For paths that cannot be resolved, should be reported from CheckUnresolvedPaths
        resolved_path = self._resolve_path(asset_path, layer.realPath if layer else None)
        if not resolved_path:
            self._record_failed_check(message=f"{msg} cannot be resolved.", at=layer)
            return

        if not self._is_within_asset_root(resolved_path):
            message = f'{msg} (resolved to "{resolved_path}") is outside of the asset root.'
            self._record_failed_check(message=message, at=prim or layer)

    def CheckStage(self, stage):
        self._stage = stage

    def CheckLayer(self, layer):
        """
        Check the sublayers of the given layer.
        """
        if layer in self._processed_layers:
            return
        self._processed_layers.add(layer)

        # USDZ layers are not checked here because they are self-contained.
        if self._is_usdz_layer(layer):
            return

        # In-memory layer - this is not allowed in an Atomic Asset.
        if not layer.realPath:
            self._record_failed_check(message="In-memory layer is not allowed in an Atomic Asset.", at=layer)
            return

        sublayers, references, payloads = UsdUtils.ExtractExternalReferences(layer.realPath)
        # Sublayers
        for sublayer_path in sublayers:
            self._check_valid_anchored_path(sublayer_path, layer, dependency_type="Sublayer")

        # References
        for reference in references:
            self._check_valid_anchored_path(reference, layer, dependency_type="Reference")

        # Payloads
        for payload in payloads:
            self._check_valid_anchored_path(payload, layer, dependency_type="Payload")


@register_rule("AtomicAsset", skip=True)
@register_requirements(cap.Requirements.AA_OV_001)
class UsdzUdimLimitationChecker(BaseRuleChecker):
    """
    Texture UDIMs are not supported in USDZ files in Nvidia Omniverse.
    Nvidia Omniverse currently (kit 107.0.3) does not support texture tiles (UDIMs) in USDZ files.
    """

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def _record_failed_check(self, path, source: Sdf.Layer | Usd.Prim | None = None):
        """
        Add a failed check for the given path and its source.
        """
        self._AddFailedCheck(
            requirement=cap.Requirements.AA_OV_001,
            message=f"{cap.Requirements.AA_OV_001.message} UDIM texture: {path}",
            at=source,
        )

    @staticmethod
    def _prim_is_in_usdz(prim: Usd.Prim) -> bool:
        """Check if the prim has any opinion authored in a USDZ package."""
        return any(
            spec.layer.GetFileFormat().IsPackage() or Ar.IsPackageRelativePath(spec.layer.identifier)
            for spec in prim.GetPrimStack()
        )

    def CheckPrim(self, prim: Usd.Prim) -> None:
        """
        Check shader prims for UDIM textures within USDZ packages.
        """
        shader = UsdShade.Shader(prim)
        if not shader:
            return

        udim_paths = []
        for shader_input in shader.GetInputs():
            val = shader_input.Get()
            if not isinstance(val, Sdf.AssetPath | Sdf.AssetPathArray):
                continue
            if isinstance(val, Sdf.AssetPath):
                val = [val]
            for tex_path in val:
                if "<UDIM>" in tex_path.path:
                    udim_paths.append(tex_path.path)

        if not udim_paths or not self._prim_is_in_usdz(prim):
            return

        for path in udim_paths:
            self._record_failed_check(path, prim)
