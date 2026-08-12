# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["UnicodeNameChecker"]

import itertools
import unicodedata
from collections import defaultdict

from pxr import Sdf, Usd

from .._base_rule_checker import BaseRuleChecker
from .._categories import register_rule


@register_rule("Other")
class UnicodeNameChecker(BaseRuleChecker):
    """Checks prim, property, variant set, and variant names for ambiguities related to UTF encoding.

    UTF-8 encoded strings may have sequences of code points that describe equivalent text rendered to the user.
    While USD does not enforce a normalization form, Unicode "Normalization Form C" (NFC) is preferred when
    creating new tokens and paths. This validator is implemented to strictly check the encoded strings to see if
    they are in NFC form. See https://unicode.org/reports/tr15/ for more information about Unicode Normalization
    forms.

    In this validator, the following conditions are checked for interested objects:
    * Object names should be NFC normalized. That means no ambiguities will be presented when comparing two names.
    * Objects should not have ambiguous children when normalized using NFC, NFKC, NFKD, or NFD forms.
    """

    def CheckStage(self, usdStage: Usd.Stage):
        # Check children of pseudo-root also since CheckPrim won't iterate it.
        root = usdStage.GetPseudoRoot()
        self._check_ambiguous_children(root)

    def _check_ambiguous_children(self, prim: Usd.Prim):
        # Colisions are identified by (normalized name, original name)
        collisions: dict[tuple[str, str], list[str]] = defaultdict(list)

        # Get all name pairs.
        child_identifiers = [child.GetName() for child in prim.GetAllChildren()]
        nfc_pairs = [(unicodedata.normalize("NFC", identifier), identifier) for identifier in child_identifiers]
        nfd_pairs = [(unicodedata.normalize("NFD", identifier), identifier) for identifier in child_identifiers]
        nfkc_pairs = [(unicodedata.normalize("NFKC", identifier), identifier) for identifier in child_identifiers]
        nfkd_pairs = [(unicodedata.normalize("NFKD", identifier), identifier) for identifier in child_identifiers]

        def update_collisions(pairs: list, form: str):
            # Sort by normalized name
            sorted_pairs = sorted(pairs, key=lambda pair: pair[0])

            # Group by normalized name and collect all collisions
            groups = itertools.groupby(sorted_pairs, lambda pair: pair[0])
            for _, grouped in groups:
                group_iterator = iter(grouped)
                primary = next(group_iterator)
                # Iterate over the rest of the siblings and add (sibling, primary) as a collision.
                for group_collision in group_iterator:
                    collisions[(group_collision[1], primary[1])].append(form)

        update_collisions(nfc_pairs, "NFC")
        update_collisions(nfd_pairs, "NFD")
        update_collisions(nfkc_pairs, "NFKC")
        update_collisions(nfkd_pairs, "NFKD")

        for (collider, primary), colliding_forms in collisions.items():
            primary_child = prim.GetChild(primary)
            self._AddWarning(
                f"Prim '{collider}' is ambiguous with sibling prim '{primary}' under the following forms: {colliding_forms}.",
                at=primary_child,
            )

    def CheckPrim(self, prim: Usd.Prim):
        if prim.IsInstanceProxy():
            return

        self._check_ambiguous_children(prim)

    def CheckLayer(self, layer):
        type_name_mapping = {
            Sdf.PrimSpec: "prim",
            Sdf.AttributeSpec: "attribute",
            Sdf.VariantSpec: "variant",
            Sdf.VariantSetSpec: "variant set",
            Sdf.RelationshipSpec: "relationship",
        }

        def on_prim_spec_path(spec_path):
            spec: Sdf.Spec = layer.GetObjectAtPath(spec_path)
            if not spec:
                return

            if not unicodedata.is_normalized("NFC", spec.name):
                type_name = type_name_mapping.get(type(spec), None)
                if type_name:
                    self._AddWarning(f"The name ({spec.name}) of {type_name} spec is not NFC normalized.", at=spec)
                else:
                    self._AddWarning(f"Object name ({spec.name}) is not NFC normalized.", at=spec)

        layer.Traverse(Sdf.Path.absoluteRootPath, on_prim_spec_path)
