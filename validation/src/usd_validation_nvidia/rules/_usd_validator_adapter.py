# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from abc import abstractmethod
from dataclasses import replace
from functools import cache, cached_property
from typing import Any, Protocol, final, runtime_checkable

from pxr import Sdf, Tf, Usd

from .._base_rule_checker import BaseRuleChecker
from .._issues import Issue, IssueSeverity
from .._requirements import Requirement, RequirementsRegistry

__all__ = [
    "UsdValidatorAdapter",
    "ValidatorErrorProtocol",
    "ValidatorErrorSiteProtocol",
    "ValidatorProtocol",
]


@runtime_checkable
class ValidatorErrorSiteProtocol(Protocol):
    """
    Temporary protocol for backward compatibility with UsdValidation.
    """

    def GetPrim(self) -> Usd.Prim | None: ...
    def GetProperty(self) -> Usd.Property | None: ...
    def GetPrimSpec(self) -> Sdf.PrimSpec | None: ...
    def GetPropertySpec(self) -> Sdf.PropertySpec | None: ...
    def GetLayer(self) -> Sdf.Layer | None: ...
    def GetStage(self) -> Usd.Stage | None: ...


@runtime_checkable
class ValidatorErrorProtocol(Protocol):
    """
    Temporary protocol for backward compatibility with UsdValidation.
    """

    def GetName(self) -> str: ...
    def GetMessage(self) -> str: ...
    def GetSites(self) -> list[ValidatorErrorSiteProtocol]: ...


@runtime_checkable
class ValidatorProtocol(Protocol):
    """
    Temporary protocol for backward compatibility with UsdValidation.
    """

    def Validate(self, obj: Any) -> list[ValidatorErrorProtocol]: ...
    def GetMetadata(self) -> Any: ...


class UsdValidatorAdapterMeta(type):
    """
    Metaclass for UsdValidatorAdapter.
    """

    @cache
    def __contains__(cls, validator_name: str) -> bool:
        """
        Returns
            True if the validator is registered and loadable from a plugin. False otherwise.
        """
        try:
            from pxr import UsdValidation
        except ImportError:
            return False
        try:
            registry = UsdValidation.ValidationRegistry()
            return registry.GetOrLoadValidatorByName(validator_name) is not None
        except Tf.ErrorException:
            return False


class UsdValidatorAdapter(BaseRuleChecker, metaclass=UsdValidatorAdapterMeta):

    @classmethod
    @abstractmethod
    def validator_name(cls) -> str: ...

    @final
    @classmethod
    @cache
    def is_implemented(cls) -> bool:
        return cls.validator_name() in UsdValidatorAdapter

    @final
    @classmethod
    def _base_validator(cls) -> ValidatorProtocol | None:
        """
        Returns
            Gets the registered validator or load it from a plugin. None if not registered or not loadable.
        """
        try:
            from pxr import UsdValidation
        except ImportError:
            return None
        try:
            registry = UsdValidation.ValidationRegistry()
            return registry.GetOrLoadValidatorByName(cls.validator_name())
        except Tf.ErrorException:
            return None

    @final
    @classmethod
    def GetDescription(cls) -> str:
        validator = cls._base_validator()
        if validator is None:
            return super().GetDescription()
        return validator.GetMetadata().doc

    @final
    @cached_property
    def base_validator(self) -> ValidatorProtocol | None:
        """
        Returns:
            The underlying validator implementation, or None if the validator is not implemented.
        """
        return self._base_validator()

    @final
    def _AddValidatorError(self, error: ValidatorErrorProtocol) -> None:
        issues: list[Issue] = self._transform(error)
        self._issues.extend(issues)

    @final
    def _Validate(self, obj: Any) -> None:
        if self.base_validator is None:
            raise ValueError(f"Validator {self.validator_name()} not implemented")
        errors: list[ValidatorErrorProtocol] = list(self.base_validator.Validate(obj))
        for error in errors:
            self._AddValidatorError(error)

    @classmethod
    def _has_fallbacks(cls) -> bool:
        return (
            cls._CheckPrim is not UsdValidatorAdapter._CheckPrim
            or cls._CheckStage is not UsdValidatorAdapter._CheckStage
            or cls._CheckLayer is not UsdValidatorAdapter._CheckLayer
        )

    @final
    def CheckStage(self, stage: Usd.Stage) -> None:
        if self.is_implemented():
            self._Validate(stage)
        elif type(self)._CheckStage is not UsdValidatorAdapter._CheckStage:
            self._CheckStage(stage)
        elif not self._has_fallbacks():
            raise ValueError(f"Validator {self.validator_name()} not implemented")

    @final
    def CheckLayer(self, layer: Sdf.Layer) -> None:
        if self.is_implemented():
            self._Validate(layer)
        elif type(self)._CheckLayer is not UsdValidatorAdapter._CheckLayer:
            self._CheckLayer(layer)
        elif not self._has_fallbacks():
            raise ValueError(f"Validator {self.validator_name()} not implemented")

    @final
    def CheckPrim(self, prim: Usd.Prim) -> None:
        if self.is_implemented():
            self._Validate(prim)
        elif type(self)._CheckPrim is not UsdValidatorAdapter._CheckPrim:
            self._CheckPrim(prim)
        elif not self._has_fallbacks():
            raise ValueError(f"Validator {self.validator_name()} not implemented")

    def _CheckStage(self, stage: Usd.Stage) -> None: ...

    def _CheckLayer(self, layer: Sdf.Layer) -> None: ...

    def _CheckPrim(self, prim: Usd.Prim) -> None: ...

    @final
    def _transform(self, error: ValidatorErrorProtocol) -> list[Issue]:
        """
        Transforms a validator error into issues.

        Args:
            error (ValidatorErrorProtocol): The validator error to transform.

        Returns:
            The issues corresponding to the validator error.
        """
        issue: Issue = Issue(
            message=error.GetMessage(),
            severity=IssueSeverity.FAILURE,
            rule=self.__class__,
            requirement=self._get_requirement(error),
        )
        issues: list[Issue] = [
            replace(issue, at=at)
            for site in error.GetSites()
            if (
                at := (
                    site.GetPrim()
                    or site.GetProperty()
                    or site.GetPrimSpec()
                    or site.GetPropertySpec()
                    or site.GetLayer()
                    or site.GetStage()
                )
            )
        ]
        return issues or [issue]

    def _get_requirement(self, error: ValidatorErrorProtocol) -> Requirement | None:
        """
        Returns the requirement corresponding to the validator error.

        Args:
            error (ValidatorErrorProtocol): The validator error.

        Returns:
            The requirement corresponding to the validator error.
        """
        registry: RequirementsRegistry = RequirementsRegistry()
        requirements: list[Requirement] = registry.get_requirements(self.__class__)
        return requirements[0] if requirements else None
