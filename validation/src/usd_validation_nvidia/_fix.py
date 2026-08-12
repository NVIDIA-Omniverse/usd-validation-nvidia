# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
Auto fix framework.

The idea behind an Auto Fix should be simple. Users should be able to `validate`, get the `Results` object,
get the `autofixes` and apply them (prior filtering).

A simple use case is as follows:

.. code-block:: python

    import usd_validation_nvidia

    engine = usd_validation_nvidia.ValidationEngine()
    results = engine.validate('foo.usd')
    issues = results.issues()

    fixer = usd_validation_nvidia.IssueFixer('foo.usd')
    fixer.fix(issues)
    fixer.save()

Auto Fixes may or may not be applied at all, this depends completely on the user. As such Auto Fixes may be applied
post factum (i.e. after Validation), as such we need to take the following into account:

- All USD objects accessed during validation may lose references, we need to keep the references somehow.
- We need to keep track of the actions we would have performed on the those references.

To keep references to all prims we visited we create multiple `Identifiers`. Identifiers contain the key of the
object to be accessed. Callables will tell us what action perform on those references. The idea is to create an AST
of post mortum actions.

See Also `BaseRuleChecker`
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import singledispatch
from typing import Any

from pxr import Pcp, Sdf, Usd, UsdGeom

from ._assets import AssetType
from ._context_managers import DelegateContextManager
from ._identifiers import AtType, EditTargetId, LayerId, VariantIdMixin
from ._issues import Issue, Suggestion

__all__ = [
    "AuthoringLayers",
    "FixResult",
    "FixResultList",
    "FixStatus",
    "IssueFixer",
]


class FixStatus(Enum):
    """
    Result of fix status.
    """

    NO_LOCATION = 0
    """
    A fix could not be performed as there was no location where to apply a suggestion.
    """

    NO_SUGGESTION = 1
    """
    A fix could not be performed as there was no suggestion to apply.
    """

    FAILURE = 2
    """
    A fix was applied, however it resulted into a failure (i.e. Exception). Check stack trace for more information.
    """

    SUCCESS = 3
    """
    A fix was successfully applied.
    """

    NO_LAYER = 4
    """
    A fix was applied at a specific layer, however the layer is not found in the layer stack.
    """

    INVALID_LOCATION = 5
    """
    A fix could not be performed as the location is no longer valid.
    """


@dataclass
class FixResult:
    """
    FixResult is a combination of input and output to the :py:class:`IssueFixer`.

    Attributes:
        issue (Issue): The issue originating this result. Useful for back tracing.
        status (FixStatus): The status of processing the issue, See `FixStatus`.
        exception (Exception): Optional. If the status is a Failure, it will contain the thrown exception.
    """

    issue: Issue
    status: FixStatus
    exception: Exception | None = None


@dataclass
class FixResultList(Sequence[FixResult]):
    """A list wrapper. Mostly output."""

    items: list[FixResult] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, item: int) -> FixResult:
        return self.items[item]

    def __str__(self):
        tokens = []
        for item in self.items:
            tokens.append(
                f"""
                    FixResult(
                        Issue(
                            message="{item.issue.message}",
                            severity={item.issue.severity},
                            rule={item.issue.rule.__name__ if item.issue.rule else None},
                            at={item.issue.at},
                            suggestion={item.issue.suggestion if item.issue.suggestion else None}
                        ),
                        status={item.status},
                        exception={item.exception.__class__.__name__ if item.exception else None}
                    )"""
            )
        text = ",".join(tokens)
        return inspect.cleandoc(
            f"""
            FixResultList(
                results=[
                    {text.lstrip()}
                ]
            )"""
        )


@singledispatch
def _convert_to_stage(stage: AssetType) -> Usd.Stage:
    """
    Args:
        stage: Either str or Usd.Stage.
    Returns:
        A Usd.Stage or throws error.
    """
    raise ValueError(f"stage must be of type str or Usd.Stage, {type(stage)}.")


@_convert_to_stage.register
def _(stage: Usd.Stage) -> Usd.Stage:
    return stage


@_convert_to_stage.register
def _(stage: str) -> Usd.Stage:
    return Usd.Stage.Open(Sdf.Layer.FindOrOpen(stage))


@singledispatch
def _to_edit_target(at: Any | None, stage: Usd.Stage) -> Usd.EditTarget:
    """
    Converts a location into an edit target.

    Args:
        at: A different composition arc for the object.
        stage: An USD Stage.
        obj: An object.

    Returns:
        An edit target for the location `at`.
    """
    raise ValueError(f"Unexpected type {type(at)}")


@_to_edit_target.register(type(None))
def _(at: None, stage: Usd.Stage) -> Usd.EditTarget:
    return Usd.EditTarget(stage.GetRootLayer())


@_to_edit_target.register(Sdf.Layer)
def _(at: Sdf.Layer, stage: Usd.Stage) -> Usd.EditTarget:
    return Usd.EditTarget(at)


@_to_edit_target.register(LayerId)
def _(at: LayerId, stage: Usd.Stage) -> Usd.EditTarget:
    layer: Sdf.Layer = at.restore(stage)  # Hold the ref.
    return Usd.EditTarget(layer)


@_to_edit_target.register(EditTargetId)
def _(at: EditTargetId, stage: Usd.Stage) -> Usd.EditTarget:
    """
    Converts an EditTargetId to an EditTarget.

    There are three cases to consider:
    1. The EditTargetId is a layer, in which case the EditTarget is the layer.
    2. The EditTargetId is a path in a layer, in which case the EditTarget is the layer (the path will be found in the layer).
    3. The EditTargetId is a composition arc, in which case the EditTarget is the layer and the node providing the spec.
    """
    # Case 1 and 2.
    layer: Sdf.Layer = at.layer_id.restore(stage)  # Hold the ref.
    if not layer:
        raise ValueError(f"No layer at path {at.layer_id}")
    elif at.path is None:
        return Usd.EditTarget(layer)
    elif at.path.IsAbsoluteRootPath():
        return Usd.EditTarget(layer)
    elif at.composed is None:
        return Usd.EditTarget(layer)

    # Case 3.
    spec: Sdf.Spec | None = at.restore(stage)
    if not spec:
        raise ValueError(f"No spec at path {at.path}")
    prim_spec: Sdf.PrimSpec | None
    if isinstance(spec, Sdf.PrimSpec):
        prim_spec = spec
    elif isinstance(spec, Sdf.PropertySpec):
        prim_spec = layer.GetPrimAtPath(spec.path.GetPrimPath())
    else:
        raise ValueError(f"Unknown spec type {type(spec)}")

    obj: Usd.Object = at.composed.restore(stage)
    prim: Usd.Prim = obj.GetPrim()
    if not prim.IsValid():
        raise ValueError(f"Invalid prim {prim.GetPrimPath()}")
    node_ref: Pcp.NodeRef = prim.GetPrimIndex().GetNodeProvidingSpec(prim_spec)
    if not node_ref:
        raise ValueError(f"No node providing spec {prim_spec.path}")
    return Usd.EditTarget(layer, node_ref)


@contextmanager
def _restore_variant_selections(stage: Usd.Stage, issue: Issue):
    if isinstance(issue.at, tuple):
        locations = [location for location in issue.at if isinstance(location, VariantIdMixin)]
    elif isinstance(issue.at, VariantIdMixin):
        locations = [issue.at]
    else:
        locations = []
    if not locations:
        yield None
        return
    # Create an anonymous layer to hold the variant changes
    anon_layer = Sdf.Layer.CreateAnonymous()

    try:
        # Insert the anonymous layer at the top of the stage's sublayers
        stage.GetSessionLayer().subLayerPaths.insert(0, anon_layer.identifier)
        with Usd.EditContext(stage, Usd.EditTarget(anon_layer)):
            # Set variant selections
            for location in locations:
                location.restore_variant_selection(stage)
            # Yield the anon_layer
            yield anon_layer
    finally:
        # Remove the anonymous layer from the stage once the context exits
        stage.GetSessionLayer().subLayerPaths.remove(anon_layer.identifier)


@dataclass
class IssueFixer:
    """Fixes issues for the given Asset.

    Attributes:
        asset (Usd.Stage): An in-memory `Usd.Stage`, either provided directly or opened
            from a URI pointing to a Usd layer file.

    .. code-block:: python

        import usd_validation_nvidia

        # validate a layer file
        engine = usd_validation_nvidia.ValidationEngine()
        results = engine.validate('foo.usd')
        issues = results.issues()

        # fix that layer file
        fixer = usd_validation_nvidia.IssueFixer('foo.usd')
        fixer.fix(issues)
        fixer.save()

        # fix a live stage directly
        stage = Usd.Stage.Open('foo.usd')
        engine = usd_validation_nvidia.ValidationEngine()
        results = engine.validate(stage)
        issues = results.issues()

        # fix that same stage in-memory
        fixer = usd_validation_nvidia.IssueFixer(stage)
        fixer.fix(issues)
        fixer.save()

    """

    asset: AssetType
    layers: set[Sdf.Layer] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        object.__setattr__(self, "asset", _convert_to_stage(self.asset))

    def apply(self, issue: Issue, at: EditTargetId | None = None, suggestion: Suggestion | None = None) -> FixResult:
        """Fix the specified issue.

        ``at`` and ``suggestion`` are coupled: each suggestion may constrain which layers
        it can be applied in (via ``suggestion.at``). When both are provided, ``at`` must
        be a valid fix site for the chosen suggestion. When ``at`` is omitted, it is
        derived from ``issue.fix_sites_for(suggestion)``.

        Args:
            issue (Issue): The issue to fix.
            at (EditTargetId | None): Optional. Where to author the fix (which layer).
            suggestion (Suggestion | None): Optional. Which fix strategy to apply.
                If None, uses issue.suggestion (the default).

        Returns:
            The resulting status (i.e. FixResult) of the fix.
        """
        fix_suggestion = suggestion or issue.suggestion

        # Validate
        if not issue.at:
            return FixResult(issue, FixStatus.NO_LOCATION)
        if not fix_suggestion:
            return FixResult(issue, FixStatus.NO_SUGGESTION)
        elif fix_suggestion not in issue.suggestions:
            raise ValueError(f"suggestion '{fix_suggestion.message}' is not one of the issue's suggestions.")

        # Derive fix site from the chosen suggestion
        fix_sites = issue.fix_sites_for(fix_suggestion)
        if not fix_sites and fix_suggestion.at:
            return FixResult(issue, FixStatus.NO_LOCATION)
        fix_at = at or (fix_sites[0] if fix_sites else None)

        # Validate at/suggestion coupling when both are explicitly provided.
        # Note: only when suggestion is given — fix_at() passes Sdf.Layer as at
        # without a suggestion, which must not be validated against EditTargetId list.
        if suggestion is not None and at is not None and fix_sites and at not in fix_sites:
            raise ValueError(f"at '{at}' is not a valid fix site for suggestion '{fix_suggestion.message}'.")

        # Run fix in variants with a lock to avoid races with concurrent fixes
        with self.lock:
            with _restore_variant_selections(self.asset, issue):
                # Restore state
                try:
                    if isinstance(issue.at, tuple):
                        obj = [loc.restore(self.asset) for loc in issue.at]
                    else:
                        obj = issue.at.restore(self.asset)
                except Exception as error:
                    return FixResult(issue, FixStatus.INVALID_LOCATION, error)

                # Find edit target
                try:
                    edit_target = _to_edit_target(fix_at, self.asset)
                except Exception as error:
                    return FixResult(issue, FixStatus.INVALID_LOCATION, error)

                # Keep the target layer
                self.layers.add(edit_target.GetLayer())

                # Apply fix
                with DelegateContextManager(), Usd.EditContext(self.asset, edit_target):
                    try:
                        fix_suggestion(self.asset, obj)
                        return FixResult(issue, FixStatus.SUCCESS)
                    except Exception as error:
                        return FixResult(issue, FixStatus.FAILURE, error)

    def fix(self, issues: list[Issue]) -> Sequence[FixResult]:
        """Fix the specified issues in the default layer of each issue.

        Args:
            issues (List[Issue]): The list of issues to fix.

        Returns:
            An array with the resulting status (i.e. FixResult) of each issue.
        """
        return FixResultList([self.apply(issue, at=None) for issue in issues])

    def fix_at(self, issues: list[Issue], layer: Sdf.Layer) -> Sequence[FixResult]:
        """Fix the specified issues persisting on a provided layer.

        Args:
            issues (List[Issue]): The list of issues to fix.
            layer (Sdf.Layer): Layer where to persist the changes.

        Returns:
            An array with the resulting status (i.e. FixResult) of each issue.
        """
        return FixResultList([self.apply(issue, at=layer) for issue in issues])

    @property
    def fixed_layers(self) -> list[Sdf.Layer]:
        """
        Returns:
            The layers affected by `fix` or `fix_at` methods.
        """
        return list(self.layers)

    def save(self) -> None:
        """Save the Asset to disk.

        Raises:
            OSError: If writing permissions are not granted.
        """
        # TODO: Add metadata of the changes.
        # Check the logical model.
        for layer in self.fixed_layers:
            autoptr: Sdf.Layer = Sdf.Layer.FindOrOpen(layer.identifier)
            if not autoptr:
                raise OSError(f"Layer does not exist: {layer}")
            if not layer.permissionToEdit:
                raise OSError(f"Cannot edit layer {layer}")
            if not layer.permissionToSave:
                raise OSError(f"Cannot save layer {layer}")
            layer.Save()

        # Save
        self.layers.clear()
        self.asset.Save()


# Utilities


@singledispatch
def AuthoringLayers(at: AtType | list[AtType]) -> list[Sdf.Layer]:
    """
    Args:
        at (AtType | list[AtType]): The location to compute the authoring layers.

    Returns:
        The layers (from stronger to weaker) where the `at` is authored.
    """
    raise NotImplementedError(f"Unsupported type: {type(at)}")


@AuthoringLayers.register(Usd.Property)
@AuthoringLayers.register(Usd.Attribute)
@AuthoringLayers.register(Usd.Relationship)
def _(prop: Usd.Property | Usd.Attribute | Usd.Relationship) -> list[Sdf.Layer]:
    layers: list[Sdf.Layer] = []
    for spec in prop.GetPropertyStack(time=Usd.TimeCode.Default()):
        layers.append(spec.layer)
    return layers


@AuthoringLayers.register(UsdGeom.Primvar)
def _(primvar: UsdGeom.Primvar) -> list[Sdf.Layer]:
    return AuthoringLayers(primvar.GetAttr())


@AuthoringLayers.register(list)
def _(at_list: list[AtType]) -> list[Sdf.Layer]:
    layers: list[Sdf.Layer] = []
    for item in at_list:
        layers.extend(AuthoringLayers(item))
    return layers
