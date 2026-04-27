#
# Copyright 2018 Pixar
# Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

import os
import re
from collections.abc import Callable, Generator
from dataclasses import dataclass
from functools import partial
from itertools import groupby
from typing import Any

import nvidia_usd_validation.capabilities as cap
from pxr import Ar, Gf, Kind, Plug, Sdf, Tf, Usd, UsdGeom, UsdLux, UsdSkel, Vt

from ._base_rule_checker import BaseRuleChecker, Suggestion
from ._categories import register_rule
from ._requirements import register_requirements
from ._usd_validator_adapter import UsdValidatorAdapter

__all__ = [
    "ByteAlignmentChecker",
    "CompressionChecker",
    "ExtentsChecker",
    "KindChecker",
    "MissingReferenceChecker",
    "NormalMapTextureChecker",
    "PortableAssetPathChecker",
    "PrimEncapsulationChecker",
    "StageMetadataChecker",
    "TextureChecker",
    "TypeChecker",
    "UsdzPackageValidator",
]


class NodeTypes:
    UsdPreviewSurface = "UsdPreviewSurface"
    UsdUVTexture = "UsdUVTexture"
    UsdTransform2d = "UsdTransform2d"
    UsdPrimvarReader = "UsdPrimvarReader"


class ShaderProps:
    Bias = "bias"
    Scale = "scale"
    SourceColorSpace = "sourceColorSpace"
    Normal = "normal"
    File = "file"


@register_rule("Basic", skip="usdUtilsValidators:UsdzPackageValidator" not in UsdValidatorAdapter)
class UsdzPackageValidator(UsdValidatorAdapter):

    @classmethod
    def validator_name(cls) -> str:
        return "usdUtilsValidators:UsdzPackageValidator"


@register_rule("Basic", skip=UsdzPackageValidator.is_implemented())
class ByteAlignmentChecker(BaseRuleChecker):
    """
    Files within a usdz package must be laid out properly, i.e. they should be aligned to 64 bytes.
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def CheckZipFile(self, zipFile, packagePath):
        file_names = zipFile.GetFileNames()
        for file_name in file_names:
            _ = Ar.GetResolver().GetExtension(file_name)
            file_info = zipFile.GetFileInfo(file_name)
            offset = file_info.dataOffset
            if offset % 64 != 0:
                self._AddFailedCheck(f"File '{file_name}' in package '{packagePath}' has an invalid offset {offset}.")


@register_rule("Basic", skip=UsdzPackageValidator.is_implemented())
class CompressionChecker(BaseRuleChecker):
    """
    Files within a usdz package should not be compressed or encrypted.
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def CheckZipFile(self, zipFile, packagePath):
        file_names = zipFile.GetFileNames()
        for file_name in file_names:
            _ = Ar.GetResolver().GetExtension(file_name)
            file_info = zipFile.GetFileInfo(file_name)
            if file_info.compressionMethod != 0:
                self._AddFailedCheck(
                    f"File '{file_name}' in package '{packagePath}' has "
                    "compression. Compression method is '{file_info.compressionMethod}', actual size "
                    "is {file_info.size}. Uncompressed size is {file_info.uncompressedSize}."
                )


@register_rule("Basic")
class MissingReferenceChecker(BaseRuleChecker):
    """
    The composed USD stage should not contain any unresolvable asset dependencies (in every possible variation of the
    asset), when using the default asset resolver.
    """

    # See UsdStage::_ReportErrors
    # See PcpErrorInvalidAssetPath::ToString
    _PATH_ASSET_PATTERN = re.compile(
        r"In <(?P<path>.+?)>: Could not open asset @(?P<asset>.+?)@ "
        r"(?P<message>for (reference|payload) introduced by @.+?@<.+?>\.) "
        r"\((instantiating|recomposing) stage on stage @.+?@ <.+?>\)"
    )

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.stage: Usd.Stage | None = None
        self.references: set[str] = set()

    @classmethod
    def _is_composition_warning(cls, diagnostic: Tf.Warning) -> bool:
        """
        A diagnostic is a composition error if it is issued by the _ReportErrors function in the usd::Stage class.

        Args:
            diagnostic: The diagnostic to check.

        Returns:
            True if the diagnostic is a composition error, False otherwise.
        """
        return (
            "_ReportErrors" in diagnostic.sourceFunction
            and os.path.join("usd", "stage.cpp") in diagnostic.sourceFileName
        )

    @classmethod
    def _extract_from_commentary(cls, commentary: str) -> tuple[str, Sdf.Path | None, Sdf.AssetPath | None]:
        """
        Args:
            commentary: The warning found.

        Returns:
            A tuple of message, path (optional) and unresolved reference (optional).
        """
        if match := cls._PATH_ASSET_PATTERN.match(commentary):
            path: Sdf.Path = Sdf.Path(match.group("path"))
            asset: Sdf.AssetPath = Sdf.AssetPath(match.group("asset"))
            message: str = match.group("message")
            return (f"Could not open asset {asset} {message}", path if path else None, asset if asset else None)
        return commentary, None, None

    def CheckStage(self, stage: Usd.Stage) -> None:
        self.stage = stage

    def CheckDiagnostics(self, diagnostics) -> None:
        composition_warnings: list[Tf.Warning] = list(filter(self._is_composition_warning, diagnostics))
        warnings_commentaries: list[str] = list(map(lambda diagnostic: diagnostic.commentary, composition_warnings))
        missing_references: list[tuple] = list(map(self._extract_from_commentary, warnings_commentaries))
        missing_references.sort()
        for (message, path, reference), _ in groupby(missing_references):
            self._AddFailedCheck(message, at=self.stage.GetPrimAtPath(path.GetPrimPath()) if path else None)
            if reference:
                self.references.add(reference.path)

    def CheckUnresolvedPaths(self, unresolvedPaths) -> None:
        paths: set[str] = set(unresolvedPaths)
        paths -= self.references
        for unresolved_path in paths:
            self._AddFailedCheck(f"Found unresolvable external dependency '{unresolved_path}'.")


@register_rule("Basic", skip=True)
@register_requirements(cap.Requirements.AA_003)
class PortableAssetPathChecker(BaseRuleChecker):
    """
    Asset paths should use forward slashes for portability.

    Windows-style backslashes in asset paths are not supported by USD and will cause
    assets to fail loading on non-Windows platforms. This checker detects backslashes
    in sublayer, reference, and payload paths and provides a fixer to convert them
    to forward slashes.
    """

    def CheckLayer(self, layer: Sdf.Layer) -> None:
        for path in layer.subLayerPaths:
            if "\\" in path:
                self._AddFailedCheck(at=layer, fn=self._fix_sublayers)

        def check_spec(spec_path: Sdf.Path) -> None:
            spec = layer.GetObjectAtPath(spec_path)

            if isinstance(spec, Sdf.PrimSpec):
                for list_op in [
                    spec.referenceList.addedItems,
                    spec.referenceList.prependedItems,
                    spec.referenceList.appendedItems,
                    spec.referenceList.explicitItems,
                ]:
                    for ref in list_op:
                        if "\\" in ref.assetPath:
                            self._AddFailedCheck(at=spec, fn=self._fix_references)
                for list_op in [
                    spec.payloadList.addedItems,
                    spec.payloadList.prependedItems,
                    spec.payloadList.appendedItems,
                    spec.payloadList.explicitItems,
                ]:
                    for payload in list_op:
                        if "\\" in payload.assetPath:
                            self._AddFailedCheck(at=spec, fn=self._fix_payloads)

            elif isinstance(spec, Sdf.AttributeSpec):
                if isinstance(spec.default, Sdf.AssetPath) and "\\" in spec.default.path:
                    self._AddFailedCheck(at=spec, fn=self._fix_attribute)

        layer.Traverse(Sdf.Path.absoluteRootPath, check_spec)

    def _AddFailedCheck(self, at: Sdf.Layer | Sdf.Spec, fn: Callable[..., None]) -> None:
        super()._AddFailedCheck(
            "Use forward slashes for portability",
            requirement=cap.Requirements.AA_003,
            at=at,
            suggestion=Suggestion(
                message="Replace backslashes with forward slashes",
                callable=fn,
            ),
        )

    @staticmethod
    def _fix_sublayers(_: Usd.Stage, at: Sdf.Layer) -> None:
        at.subLayerPaths = [p.replace("\\", "/") for p in at.subLayerPaths]

    @staticmethod
    def _fix_references(_: Usd.Stage, at: Sdf.PrimSpec) -> None:
        for list_op in [
            at.referenceList.addedItems,
            at.referenceList.prependedItems,
            at.referenceList.appendedItems,
            at.referenceList.explicitItems,
        ]:
            list_op[:] = [
                (
                    Sdf.Reference(
                        assetPath=ref.assetPath.replace("\\", "/"),
                        primPath=ref.primPath,
                        layerOffset=ref.layerOffset,
                        customData=ref.customData,
                    )
                    if "\\" in ref.assetPath
                    else ref
                )
                for ref in list_op
            ]

    @staticmethod
    def _fix_payloads(_: Usd.Stage, at: Sdf.PrimSpec) -> None:
        for list_op in [
            at.payloadList.addedItems,
            at.payloadList.prependedItems,
            at.payloadList.appendedItems,
            at.payloadList.explicitItems,
        ]:
            list_op[:] = [
                (
                    Sdf.Payload(
                        assetPath=payload.assetPath.replace("\\", "/"),
                        primPath=payload.primPath,
                        layerOffset=payload.layerOffset,
                    )
                    if "\\" in payload.assetPath
                    else payload
                )
                for payload in list_op
            ]

    @staticmethod
    def _fix_attribute(_: Usd.Stage, at: Sdf.AttributeSpec) -> None:
        if isinstance(at.default, Sdf.AssetPath):
            at.default = Sdf.AssetPath(at.default.path.replace("\\", "/"))


@register_rule("Basic")
@register_requirements(cap.Requirements.UN_001, cap.Requirements.UN_002)
class StageMetadataChecker(BaseRuleChecker):
    """
    All stages should declare their 'upAxis' and 'metersPerUnit'. Stages that can be consumed as referencable assets
    should furthermore have a valid 'defaultPrim' declared, and stages meant for consumer-level packaging should
    always have upAxis set to 'Y'
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def CheckStage(self, usdStage):
        from pxr import UsdGeom

        if not usdStage.HasAuthoredMetadata(UsdGeom.Tokens.upAxis):
            self._AddFailedCheck(
                message="Stage does not specify an upAxis.",
                requirement=cap.Requirements.UN_001,
            )
        elif self._consumerLevelChecks:
            up_axis = UsdGeom.GetStageUpAxis(usdStage)
            if up_axis != UsdGeom.Tokens.y:
                self._AddFailedCheck(
                    f"Stage specifies upAxis '{up_axis}'. upAxis should be '{UsdGeom.Tokens.y}'.",
                    requirement=cap.Requirements.UN_001,
                )

        if not usdStage.HasAuthoredMetadata(UsdGeom.Tokens.metersPerUnit):
            self._AddFailedCheck(
                message="Stage does not specify its linear scale " "in metersPerUnit.",
                requirement=cap.Requirements.UN_002,
            )

        if self._assetLevelChecks:
            default_prim = usdStage.GetDefaultPrim()
            if not default_prim:
                self._AddFailedCheck("Stage has missing or invalid defaultPrim.")


@register_rule("Basic")
class TextureChecker(BaseRuleChecker):
    """A RuleChecker which handles locating texture files automatically.

    Texture files should be readable by intended client (only .jpg or .png for consumer-level USDZ). Derived classes
    can reimplement `TextureChecker._CheckTexture`.
    """

    # The most basic formats are those published in the USDZ spec
    _BASIC_USDZ_IMAGE_FORMATS = ("jpg", "png")

    # In non-consumer-content mode, OIIO can allow us to
    # additionaly read other formats from USDZ packages
    _EXTRA_USDZ_OIIO_IMAGE_FORMATS = ".exr"

    # Include a list of "unsupported" image formats to provide better error
    # messages when we find one of these.  Our builtin image decoder
    # _can_ decode these, but they are not considered portable consumer-level
    _UNSUPPORTED_IMAGE_FORMATS = ["bmp", "tga", "hdr", "exr", "tif", "zfile", "tx"]

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        # Check if the prim has an allowed type.
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        # allow all known formats by default
        self._allowedFormats = (
            list(TextureChecker._BASIC_USDZ_IMAGE_FORMATS) + TextureChecker._UNSUPPORTED_IMAGE_FORMATS
        )

    def CheckStage(self, usdStage):
        # This is the point at which we can determine whether we have a USDZ
        # archive, and so have enough information to set the allowed formats.
        root_layer = usdStage.GetRootLayer()
        if root_layer.GetFileFormat().IsPackage() or self._consumerLevelChecks:
            self._allowedFormats = list(TextureChecker._BASIC_USDZ_IMAGE_FORMATS)
            if not self._consumerLevelChecks:
                self._allowedFormats.append(TextureChecker._EXTRA_USDZ_OIIO_IMAGE_FORMATS)

    def _CheckTexture(self, texAssetPath, attr):
        """Check the texture asset used by the shader input

        Args:
            texAssetPath: The AssetPath for the texture file
            attr: The attribute that uses the texture
        """
        text_file_ext = Ar.GetResolver().GetExtension(texAssetPath).lower()

        # Lights are somewhat special in that they have a connectable shader.
        # Their ies light distribution files are not textures, so we skip them.
        if self._is_ies_asset(attr, text_file_ext):
            return

        if self._consumerLevelChecks and text_file_ext in TextureChecker._UNSUPPORTED_IMAGE_FORMATS:
            self._AddFailedCheck(
                f"Texture <{attr.GetPath()}> with asset @{texAssetPath}@ has non-portable " "file format.",
                at=attr,
            )
        elif text_file_ext not in self._allowedFormats:
            self._AddFailedCheck(
                f"Texture <{attr.GetPath()}> with asset @{texAssetPath}@ has unknown " "file format.", at=attr
            )

    def CheckPrim(self, prim):
        # Right now, we find texture referenced by looking at the asset-valued
        # inputs on Connectable prims.
        from pxr import Sdf, Usd, UsdShade

        # Nothing to do if we are an untyped prim
        if not prim.GetTypeName():
            return

        # Check if the prim is Connectable.
        connectable = UsdShade.ConnectableAPI(prim)
        if not connectable:
            return

        shader_inputs = connectable.GetInputs()
        for ip in shader_inputs:
            attr = ip.GetAttr()
            if ip.GetTypeName() == Sdf.ValueTypeNames.Asset:
                text_file_path = ip.Get(Usd.TimeCode.EarliestTime())
                # ip may be unauthored and/or connected
                if text_file_path:
                    self._CheckTexture(text_file_path.path, attr)
            elif ip.GetTypeName() == Sdf.ValueTypeNames.AssetArray:
                text_path_array = ip.Get(Usd.TimeCode.EarliestTime())
                if text_path_array:
                    for text_path in text_path_array:
                        self._CheckTexture(text_path, attr)

    @staticmethod
    def _is_ies_asset(attr: Usd.Attribute, assetFileExt: str):
        """Returns true if the asset type is a light intensity distribution file applied to a light prim.
        Args:
            attr: The attribute that uses the asset
            assetFileExt: The file extension of the asses
        """
        if (attr_prim := attr.GetPrim()) and UsdLux.LightAPI(attr_prim):
            return assetFileExt == "ies"
        return False


@register_rule("Basic")
class PrimEncapsulationChecker(BaseRuleChecker):
    """
    Check for basic prim encapsulation rules:

    - Boundables may not be nested under Gprims
    - Connectable prims (e.g. Shader, Material, etc) can only be nested inside other Container-like Connectable prims.
      Container-like prims include Material, NodeGraph, Light, LightFilter, and *exclude Shader*
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.ResetCaches()

    def _HasGprimAncestor(self, prim):
        from pxr import Sdf, UsdGeom

        path = prim.GetPath()
        if path in self._hasGprimInPathMap:
            return self._hasGprimInPathMap[path]
        elif path == Sdf.Path.absoluteRootPath:
            self._hasGprimInPathMap[path] = False
            return False
        else:
            val = self._HasGprimAncestor(prim.GetParent()) or prim.IsA(UsdGeom.Gprim)
            self._hasGprimInPathMap[path] = val
            return val

    def _FindConnectableAncestor(self, prim):
        from pxr import Sdf, UsdShade

        path = prim.GetPath()
        if path in self._connectableAncestorMap:
            return self._connectableAncestorMap[path]
        elif path == Sdf.Path.absoluteRootPath:
            self._connectableAncestorMap[path] = None
            return None
        else:
            val = self._FindConnectableAncestor(prim.GetParent())
            # The GetTypeName() check is to work around a bug in
            # ConnectableAPIBehavior registry.
            if prim.GetTypeName() and not val:
                conn = UsdShade.ConnectableAPI(prim)
                if conn:
                    val = prim
            self._connectableAncestorMap[path] = val
            return val

    def CheckPrim(self, prim):
        from pxr import UsdGeom, UsdShade

        parent = prim.GetParent()

        # Of course we must allow Boundables under other Boundables, so that
        # schemas like UsdGeom.Pointinstancer can nest their prototypes.  But
        # we disallow a PointInstancer under a Mesh just as we disallow a Mesh
        # under a Mesh, for the same reason: we cannot then independently
        # adjust visibility for the two objects, nor can we reasonably compute
        # the parent Mesh's extent.
        if prim.IsA(UsdGeom.Boundable):
            if parent:
                if self._HasGprimAncestor(parent):
                    self._AddFailedCheck(
                        f"Gprim <{prim.GetPath()}> has an ancestor prim that " "is also a Gprim, which is not allowed.",
                        at=prim,
                    )

        connectable = UsdShade.ConnectableAPI(prim)
        # The GetTypeName() check is to work around a bug in
        # ConnectableAPIBehavior registry.
        if prim.GetTypeName() and connectable:
            if parent:
                p_connectable = UsdShade.ConnectableAPI(parent)
                if not parent.GetTypeName():
                    p_connectable = None

                if p_connectable and hasattr(p_connectable, "IsContainer") and not p_connectable.IsContainer():
                    # XXX This should be a failure as it is a violation of the
                    # UsdShade OM.  But pragmatically, there are many
                    # authoring tools currently producing this structure, which
                    # does not _currently_ perturb Hydra, so we need to start
                    # with a warning
                    self._AddWarning(
                        f"Connectable {prim.GetTypeName()} <{prim.GetPath()}> cannot reside "
                        f"under a non-Container Connectable {parent.GetTypeName()}",
                        at=prim,
                    )
                elif not p_connectable:
                    # it's only OK to have a non-connectable parent if all
                    # the rest of your ancestors are also non-connectable.  The
                    # error message we give is targeted at the most common
                    # infraction, using Scope or other grouping prims inside
                    # a Container like a Material
                    conn_anstr = self._FindConnectableAncestor(parent)
                    if conn_anstr is not None:
                        self._AddFailedCheck(
                            f"Connectable {prim.GetTypeName()} <{prim.GetPath()}> can only have"
                            " Connectable Container ancestors"
                            f" up to {conn_anstr.GetTypeName()} ancestor <{conn_anstr.GetPath()}>, but its"
                            f" parent {parent.GetName()} is a {parent.GetTypeName()}.",
                            at=prim,
                        )

    def ResetCaches(self):
        self._connectableAncestorMap = dict()
        self._hasGprimInPathMap = dict()


@register_rule("Basic")
class NormalMapTextureChecker(BaseRuleChecker):
    """
    UsdUVTexture nodes that feed the `inputs:normals` of a
    UsdPreviewSurface must ensure that the data is encoded and scaled properly.
    Specifically:

       - Since normals are expected to be in the range [(-1,-1,-1), (1,1,1)],
         the Texture node must transform 8-bit textures from their [0..1] range by
         setting its `inputs:scale` to [2, 2, 2, 1] and
         `inputs:bias` to [-1, -1, -1, 0]
       - Normal map data is commonly expected to be linearly encoded.  However, many
         image-writing tools automatically set the profile of three-channel, 8-bit
         images to SRGB.  To prevent an unwanted transformation, the UsdUVTexture's
         `inputs:sourceColorSpace` must be set to "raw".  This program cannot
         currently read the texture metadata itself, so for now we emit warnings
         about this potential infraction for all 8 bit image formats.
    """

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

    def _GetShaderId(self, shader):
        # We might someday try harder to find an identifier...
        return shader.GetShaderId()

    def _TextureIs8Bit(self, asset):
        # Eventually we hope to leverage HioImage through a plugin system,
        # when Imaging is present, to answer this and other image queries
        # more definitively
        from pxr import Ar

        ext = Ar.GetResolver().GetExtension(asset.resolvedPath)
        # not an exhaustive list, but ones we typically can read
        return ext in ["bmp", "tga", "jpg", "png", "tif"]

    def _GetInputValue(self, shader, inputName):
        from pxr import Usd, UsdShade

        shader_input = shader.GetInput(inputName)
        if not shader_input:
            return None
        # Query value producing attributes for input values.
        # This has to be a length of 1, otherwise no attribute is producing a value.
        # If the input is not connected the UsdAttribute for this input is returned,
        # but only if it has an authored value.
        value_producing_attrs = UsdShade.Utils.GetValueProducingAttributes(shader_input)
        if not value_producing_attrs or len(value_producing_attrs) != 1:
            return None
        # We require an input parameter producing the value.
        if not UsdShade.Input.IsInput(value_producing_attrs[0]):
            return None
        return value_producing_attrs[0].Get(Usd.TimeCode.EarliestTime())

    def CheckPrim(self, prim):
        from pxr import Gf, UsdShade
        from pxr.UsdShade import Utils as ShadeUtils

        if not prim.IsA(UsdShade.Shader):
            return

        shader = UsdShade.Shader(prim)
        if not shader:
            self._AddError(f"Invalid shader prim <{prim.GetPath()}>.", at=prim)
            return

        shader_id = self._GetShaderId(shader)

        # We may have failed to fetch an identifier for asset/source-based
        # nodes. We are only interested in UsdPreviewSurface nodes identified via
        # info:id, so it's not an error
        if not shader_id or shader_id != NodeTypes.UsdPreviewSurface:
            return

        normal_input = shader.GetInput(ShaderProps.Normal)
        if not normal_input:
            return
        if not hasattr(ShadeUtils, "GetValueProducingAttributes"):
            return
        value_producing_attrs = ShadeUtils.GetValueProducingAttributes(normal_input)
        if not value_producing_attrs or value_producing_attrs[0].GetPrim() == prim:
            return

        source_prim = value_producing_attrs[0].GetPrim()

        source_shader = UsdShade.Shader(source_prim)
        if not source_shader:
            # In theory, could be connected to an interface attribute of a
            # parent connectable... not useful, but not an error
            if UsdShade.ConnectableAPI(source_prim):
                return
            self._AddFailedCheck(
                f"{NodeTypes.UsdPreviewSurface}.{ShaderProps.Normal} on prim <{source_prim}> is connected to a"
                " non-Shader prim.",
                at=source_prim,
            )
            return

        source_id = self._GetShaderId(source_shader)

        # We may have failed to fetch an identifier for asset/source-based
        # nodes. OR, we could potentially be driven by a UsdPrimvarReader,
        # in which case we'd have nothing to validate
        if not source_id or source_id != NodeTypes.UsdUVTexture:
            return

        text_asset = self._GetInputValue(source_shader, ShaderProps.File)

        if text_asset is None:
            # There's no attribute connected to the input of the source shader
            # and the input has no authored value, so we can't check anything.
            return

        if not text_asset or not text_asset.resolvedPath:
            self._AddFailedCheck(
                f"{NodeTypes.UsdUVTexture} prim <{source_prim.GetPath()}> has invalid or unresolvable "
                f"inputs:file of @{text_asset.path if text_asset else ''}@",
                at=source_prim,
            )
            return

        if not self._TextureIs8Bit(text_asset):
            # really nothing more is required for image depths > 8 bits,
            # which we assume FOR NOW, are floating point
            return

        if not self._GetInputValue(source_shader, ShaderProps.SourceColorSpace):
            self._AddWarning(
                f"{NodeTypes.UsdUVTexture} prim <{source_prim}> that reads Normal Map @{text_asset.path}@ may need "
                "to set inputs:sourceColorSpace to 'raw' as some "
                "8-bit image writers always indicate an SRGB "
                "encoding.",
                at=source_prim,
            )

        bias = self._GetInputValue(source_shader, ShaderProps.Bias)

        scale = self._GetInputValue(source_shader, ShaderProps.Scale)

        if not (bias and scale and isinstance(bias, Gf.Vec4f) and isinstance(scale, Gf.Vec4f)):
            # XXX This should be a failure, as it results in broken normal
            # maps in Storm and hdPrman, at least.  But for the same reason
            # as the shader-under-shader check, we cannot fail until at least
            # the major authoring tools have been updated.
            self._AddWarning(
                f"{NodeTypes.UsdUVTexture} prim <{source_prim.GetPath()}> reads 8 bit Normal Map @{text_asset.path}@, "
                "which requires that inputs:scale be set to "
                "[2, 2, 2, 1] and inputs:bias be set to "
                "[-1, -1, -1, 0] for proper interpretation.",
                at=source_prim,
            )
            return

        # don't really care about fourth components...
        if bias[0] != -1 or bias[1] != -1 or bias[2] != -1 or scale[0] != 2 or scale[1] != 2 or scale[2] != 2:
            self._AddWarning(
                f"{NodeTypes.UsdUVTexture} prim <{source_prim.GetPath()}> reads an 8 bit Normal Map, "
                "but has non-standard inputs:scale and "
                f"inputs:bias values of {scale} and {bias}",
                at=source_prim,
            )


@dataclass(frozen=True)
class _CachedKindState:
    all_group: bool
    """Self and ancestors are all group kind."""

    has_empty_ancestor: bool
    """Self or ancestors have empty kind."""

    has_component_ancestor: bool
    """Self or ancestors have component kind."""

    def join(self, other):
        return self.__class__(
            self.all_group and other.all_group,
            self.has_empty_ancestor or other.has_empty_ancestor,
            self.has_component_ancestor or other.has_component_ancestor,
        )


@register_rule("Basic")
class KindChecker(BaseRuleChecker):
    """
    All kinds must be registered and conform to the rules specified in the `USD Glossary`_.

    .. _`USD Glossary`: https://graphics.pixar.com/usd/release/glossary.html?#usdglossary-kind
    """

    _ROOT_KINDS = tuple(
        kind
        for kind in Kind.Registry.GetAllKinds()
        if Kind.Registry.IsA(kind, Kind.Tokens.assembly)
        or Kind.Registry.IsA(kind, Kind.Tokens.component)
        or Kind.Registry.IsA(kind, Kind.Tokens.group)
    )
    _GROUP_KINDS = tuple(kind for kind in Kind.Registry.GetAllKinds() if Kind.Registry.IsA(kind, Kind.Tokens.group))
    _VALID_KINDS = tuple(kind for kind in Kind.Registry.GetAllKinds() if kind != Kind.Tokens.model)

    def __init__(self, verbose, consumerLevelChecks, assetLevelChecks):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)

        self._kind_cache: dict[Sdf.Path, _CachedKindState] = {}

    @classmethod
    def _is_root_model(cls, prim) -> bool:
        """Whether this is the first model in the hierarchy."""
        model: Usd.ModelAPI = Usd.ModelAPI(prim)
        if not model.IsModel():
            return False
        parent_prim: Usd.Prim = prim.GetParent()
        if parent_prim.IsPseudoRoot():
            return True
        parent_model = Usd.ModelAPI(parent_prim)
        if parent_model.IsModel():
            return False
        return True

    def CheckPrim(self, prim):
        model = Usd.ModelAPI(prim)
        kind = model.GetKind()
        if not kind:
            return
        elif self._is_root_model(prim):
            if kind not in self._ROOT_KINDS:
                self._AddFailedCheck(
                    f'Invalid Kind "{kind}". Kind "{kind}" cannot be at the root of the Model Hierarchy. The root '
                    f"prim of a model must one of {KindChecker._ROOT_KINDS}.",
                    at=prim,
                )
        elif kind == Kind.Tokens.model or kind not in Kind.Registry.GetAllKinds():
            self._AddFailedCheck(
                f'Invalid Kind "{kind}". Must be one of {KindChecker._VALID_KINDS}.',
                at=prim,
            )
        elif Kind.Registry.IsA(kind, Kind.Tokens.model):
            kind_state = self._query_ancestors_kind_state(prim)
            if not kind_state.all_group:
                if kind_state.has_component_ancestor:
                    suggestion = Suggestion(message="Fix", callable=self.fix_ancestors_kind_with_components)
                elif kind_state.has_empty_ancestor:
                    suggestion = Suggestion(message="Fix", callable=self.fix_ancestors_empty_kind)
                else:
                    suggestion = None
                self._AddFailedCheck(
                    f'Invalid Kind "{kind}". Model prims can only be parented under "{KindChecker._GROUP_KINDS}" prims.',
                    at=prim,
                    suggestion=suggestion,
                )

    def _query_ancestors_kind_state(self, prim: Usd.Prim):
        parent_path = prim.GetParent().GetPath()
        if parent_path in self._kind_cache:
            return self._kind_cache[parent_path]

        prims: list[Usd.Prim] = []
        current: Usd.Prim = prim
        while not current.IsPseudoRoot():
            prims.append(current)
            current = current.GetParent()

        kind_state = _CachedKindState(True, False, False)
        for current in reversed(prims):
            try:
                kind_state = self._kind_cache[current.GetPath()]
            except KeyError:
                model: Usd.ModelAPI = Usd.ModelAPI(current)
                prim_kind = model.GetKind()
                is_group_kind: bool = Kind.Registry.IsA(prim_kind, Kind.Tokens.group)
                is_empty_kind: bool = not prim_kind
                is_component_kind: bool = not is_group_kind and Kind.Registry.IsA(prim_kind, Kind.Tokens.component)
                prim_kind_state = _CachedKindState(is_group_kind, is_empty_kind, is_component_kind)
                self._kind_cache[current.GetPath()] = kind_state = kind_state.join(prim_kind_state)

        return self._kind_cache[parent_path]

    def fix_ancestors_kind_with_components(self, _: Usd.Stage, prim: Usd.Prim):
        model = Usd.ModelAPI(prim)
        kind = model.GetKind()
        if Kind.Registry.IsA(kind, Kind.Tokens.model):
            model.SetKind(Kind.Tokens.subcomponent)

    def fix_ancestors_empty_kind(self, _: Usd.Stage, prim: Usd.Prim):
        parent = prim.GetParent()
        while not parent.IsPseudoRoot():
            parent_model = Usd.ModelAPI(parent)
            parent_kind = parent_model.GetKind()
            if not parent_kind:
                parent_model.SetKind(Kind.Tokens.group)

            parent = parent.GetParent()

    def ResetCaches(self):
        self._kind_cache = {}
        return super().ResetCaches()


@register_rule("Basic")
@register_requirements(cap.Requirements.VG_002)
class ExtentsChecker(BaseRuleChecker):
    """
    Boundable prims have the extent attribute. For point based prims, the value of the extent must be correct at each
    time sample of the point attribute
    """

    _SCHEMA_TYPE_GETTERS: list[tuple[type[Usd.SchemaBase], list[Callable[[Usd.SchemaBase], Usd.Attribute]]]] = [
        (UsdGeom.PointBased, [lambda obj: obj.GetPointsAttr()]),
        (UsdGeom.Curves, [lambda obj: obj.GetWidthsAttr()]),
        (UsdGeom.Points, [lambda obj: obj.GetWidthsAttr()]),
        (UsdSkel.Root, [lambda obj: obj.GetExtentAttr()]),
        (UsdSkel.Skeleton, [lambda obj: obj.GetExtentAttr()]),
    ]
    """
    Unfortunately, there's no universal way of knowing which attributes extent calculation depends on.
    Hence we hardcode the attributes per schema in SCHEMA_TYPE_GETTERS
    """
    _MAX_TIME_SAMPLES: int = 5
    """
    int: The maximum number of samples to report.
    """

    def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool):
        super().__init__(verbose, consumerLevelChecks, assetLevelChecks)
        self.ResetCaches()

    @staticmethod
    def _get_attribute_time_samples(attribute: Usd.Attribute) -> Generator[Usd.TimeCode, None, None]:
        """
        Args:
            attribute: The attribute to extract the time samples.
        Returns:
            All time samples in an attribute.
        """
        if attribute.IsValid():
            if not attribute.ValueMightBeTimeVarying():
                yield Usd.TimeCode.Default()
            else:
                for time in attribute.GetTimeSamples():
                    yield Usd.TimeCode(time)

    @classmethod
    def _get_extent_time_samples(cls, prim: Usd.Prim) -> Generator[Usd.TimeCode, None, None]:
        """Get the time samples for the extent attribute from the associated attributes (Points, Widths, Extent, etc..).
        Args:
            prim: The prim of the extent attribute to query the time samples .

        Returns:
            All time samples of the extent attribute.
        """
        for schema_type, getters in cls._SCHEMA_TYPE_GETTERS:
            instance: Usd.SchemaBase = schema_type(prim)
            if not instance:
                continue
            for getter in getters:
                attribute: Usd.Attribute = getter(instance)
                yield from cls._get_attribute_time_samples(attribute)

    @classmethod
    def _layers_to_apply(cls, prim: Usd.Prim) -> list[Sdf.Layer]:
        """
        Iterate Schemas and their respective attributes and fix those layers first.
        """
        layers: list[Sdf.Layer] = []
        for schema_type, getters in cls._SCHEMA_TYPE_GETTERS:
            instance: Usd.SchemaBase = schema_type(prim)
            if not instance:
                continue
            for getter in getters:
                attribute: Usd.Attribute = getter(instance)
                for spec in attribute.GetPropertyStack(time=Usd.TimeCode.Default()):
                    layers.append(spec.layer)
        return layers

    def _compute_extents(
        self, _: Usd.Stage, prim: Usd.Prim, extent_time_samples: list[Usd.TimeCode | float] | None = None
    ) -> None:
        """
        Compute the extents of a specific prim.
        """
        boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)

        time_code_extent: dict[Usd.TimeCode, Vt.Vec3fArray] = {}
        if not extent_time_samples:
            extent_time_samples = list(ExtentsChecker._get_extent_time_samples(prim))
        for time in extent_time_samples:
            time_code_extent[time] = boundable.ComputeExtentFromPlugins(boundable, time)

        attribute: Usd.Attribute = boundable.CreateExtentAttr()
        with Sdf.ChangeBlock():
            for time, extent in time_code_extent.items():
                attribute.Set(extent, time)

    @staticmethod
    def _is_close(lh: Vt.Vec3fArray, rh: Vt.Vec3fArray) -> bool:
        # If either vector is empty don't consider them to be close
        if len(lh) == 0 or len(rh) == 0:
            return False

        # If the vectors are of different length then they cannot be considered close
        if len(lh) != len(rh):
            return False

        # Compare the values in the vector
        for lh_value, rh_value in zip(lh, rh):
            if not Gf.IsClose(lh_value, rh_value, Gf.MIN_VECTOR_LENGTH):
                return False
        return True

    def CheckPrim(self, prim: Usd.Prim) -> None:
        # Skip checked prims.
        if prim in self._checked_prims:
            return

        # Check UsdSkel prims
        if prim.IsA(UsdSkel.Root):
            self._check_skel(prim)
        else:
            self._check_extent(prim)

    def _check_extent(self, prim: Usd.Prim, extent_time_samples: list[Usd.TimeCode | float] | None = None) -> None:
        boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)
        if not boundable:
            return

        attribute: Usd.Attribute = boundable.GetExtentAttr()
        # Has no value
        if not attribute.HasValue():
            prim_type: Tf.Type = prim.GetPrimTypeInfo().GetSchemaType()
            prim_type_metadata: dict[str, Any] = (
                Plug.Registry().GetPluginForType(prim_type).GetMetadataForType(prim_type.typeName)
            )
            # Boundables that implement compute extent but don't have any authored extent
            # We can assume that the user has made the choice explicitly.
            if prim_type_metadata.get("implementsComputeExtent"):
                return
            self._AddFailedCheck(
                "Prim does not have any extent value",
                at=prim,
                requirement=cap.Requirements.VG_002,
                suggestion=Suggestion(
                    message="Compute the extents",
                    callable=partial(self._compute_extents, extent_time_samples=extent_time_samples),
                    at=self._layers_to_apply(prim),
                ),
            )
            return  # Nothing more to do

        # Check extent at each time sample
        authored_vs_computed: dict[Usd.TimeCode, bool] = {}

        extent_time_samples = extent_time_samples or list(ExtentsChecker._get_extent_time_samples(prim))
        for time in extent_time_samples:
            authored_extent: Vt.Vec3fArray = attribute.Get(time)
            if not authored_extent and time == Usd.TimeCode.Default():
                # It is possible the extent time sample is authored on a time that is not at default. We try at time 0
                time = Usd.TimeCode()
                authored_extent = attribute.Get(time)
            computed_extent: Vt.Vec3fArray = boundable.ComputeExtentFromPlugins(boundable, time)
            authored_vs_computed[time] = self._is_close(authored_extent, computed_extent)

        # Get all timestamps where values differ
        time_codes: list[Usd.TimeCode] = []
        for time, flag in authored_vs_computed.items():
            if not flag:
                time_codes.append(time)

        if Usd.TimeCode.Default() in time_codes:
            self._AddFailedCheck(
                "Prim has incorrect extent value",
                at=prim,
                requirement=cap.Requirements.VG_002,
                suggestion=Suggestion(
                    message="Recompute the extents",
                    callable=partial(self._compute_extents, extent_time_samples=extent_time_samples),
                    at=self._layers_to_apply(prim),
                ),
            )
        elif len(time_codes) == 1:
            self._AddFailedCheck(
                f"Incorrect extent value for prim at time {time_codes[0].GetValue()}",
                at=prim,
                requirement=cap.Requirements.VG_002,
                suggestion=Suggestion(
                    message="Recompute the extents",
                    callable=partial(self._compute_extents, extent_time_samples=extent_time_samples),
                    at=self._layers_to_apply(prim),
                ),
            )
        elif len(time_codes) > 1:
            values = ", ".join(map(lambda time_code: str(time_code.GetValue()), time_codes[: self._MAX_TIME_SAMPLES]))
            if len(time_codes) > self._MAX_TIME_SAMPLES:
                values = f"{values}, ..."
            self._AddFailedCheck(
                f"Incorrect extent value for prim at multiple times (i.e. {values})",
                at=prim,
                requirement=cap.Requirements.VG_002,
                suggestion=Suggestion(
                    message="Recompute the extents",
                    callable=partial(self._compute_extents, extent_time_samples=extent_time_samples),
                    at=self._layers_to_apply(prim),
                ),
            )

    def _check_skel(self, skel_root_prim: Usd.Prim) -> None:
        """Check the extent of a UsdSkel.SkelRoot and all the UsdSkel.Skeleton prims underneath it"""
        skel_root_cache = UsdSkel.Cache()
        skel_root_cache.Populate(UsdSkel.Root(skel_root_prim), Usd.PrimAllPrimsPredicate)
        skel_root_time_samples: list[float] = []

        for child_prim in Usd.PrimRange(skel_root_prim):
            if child_prim.IsA(UsdSkel.Skeleton):
                # Get the extent time samples from the SkelAnimation binding
                skel_query = skel_root_cache.GetSkelQuery(UsdSkel.Skeleton(child_prim))
                anim_query = skel_query.GetAnimQuery()
                if anim_query:
                    time_samples = [Usd.TimeCode(time) for time in anim_query.GetJointTransformTimeSamples()]
                    skel_root_time_samples.extend(time_samples)
                    self._check_extent(child_prim, extent_time_samples=time_samples)
                else:
                    # No SkelAnimation binding. Get the extent time samples directly from the extent attribute.
                    self._check_extent(child_prim)
                self._checked_prims.add(child_prim)

        # The time samples of a SkelRoot are all the time samples of the Skeletons underneath it.
        self._check_extent(skel_root_prim, extent_time_samples=sorted(list(skel_root_time_samples)))

    def ResetCaches(self):
        self._checked_prims: set[Usd.Prim] = set()


@register_rule("Basic")
class TypeChecker(BaseRuleChecker):
    """
    All prims must have a type defined.
    """

    def CheckPrim(self, prim):
        # Ignore specific prim.
        if prim.GetPath().HasPrefix(Sdf.Path("/Render")):
            return
        if prim.IsDefined() and not prim.GetTypeName():
            self._AddFailedCheck(
                f"Missing type for Prim <{prim.GetPath()}>",
                at=prim,
            )
