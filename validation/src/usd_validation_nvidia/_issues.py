# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from abc import abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from functools import cache, partial, singledispatch
from typing import (
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pxr import Usd

from ._identifiers import (
    AtType,
    EditTargetId,
    EditTargetIdList,
    Identifier,
    LayerId,
    PrimId,
    PropertyId,
    StageId,
    to_identifier,
)
from ._requirements import Requirement, RequirementsRegistry
from .capabilities import RequirementProtocol, RequirementRefProtocol
from .utils import DedupeMetaclass, _PatternTree, deprecated

__all__ = [
    "AssetFix",
    "Issue",
    "IssueGroupBy",
    "IssueGroupsBy",
    "IssuePredicate",
    "IssuePredicates",
    "IssueSeverity",
    "IssuesList",
    "Suggestion",
]

RuleType = TypeVar("RuleType")
"""Any Checker is a subclass of BaseRuleChecker."""


class IssueSeverity(Enum):
    """
    Defines the severity of an issue.
    """

    ERROR = 0
    """
    The issue is the result of an actual exception/failure in the code.
    """
    FAILURE = 1
    """
    An indication that it is failing to comply with a specific rule.
    """
    WARNING = 2
    """
    A warning is a suggestion to improve USD, it could be related to performance or memory.
    """
    INFO = 3
    """
    Information that needs to be reported by the validation rules.
    """
    NONE = 4
    """
    No issue.
    """


@runtime_checkable
class AssetFix(Protocol):
    """Protocol for fix callables passed to :class:`Suggestion`.

    Implementors may accept a single object or a list of objects, allowing
    multi-location fixes without breaking existing single-location callables.
    """

    def __call__(self, stage: Usd.Stage, obj: AtType | list[AtType]) -> None: ...


@dataclass(frozen=True, repr=False)
class Suggestion(metaclass=DedupeMetaclass):
    """
    A suggestion is a combination of a callable and a message describing the suggestion.

    Use ``Suggestion(at=[site1, site2])`` when the **same fix** can be applied at multiple
    locations (e.g. different layers). The user picks **which layer** to apply the fix in.

    Attributes:
        callable (Callable[[Usd.Stage, AtType], None]): A proposed fix to an issue.
        message (str): A proposed solution to an issue.
        at (List[Identifier[AtType]] | None): Optional. A layer constraint that restricts WHERE
            this fix can be applied. Acts as a filter on ``Issue.at.get_spec_ids()`` — not the
            fix location itself. If None, the fix can be applied at any layer in the spec stack.
    """

    callable: AssetFix
    message: str
    at: AtType | list[AtType] | list[EditTargetId] | None = field(default=None, hash=False)

    def __post_init__(self):
        if not callable(self.callable):
            raise ValueError("callable must be a Callable.")
        object.__setattr__(self, "at", EditTargetIdList.from_(self.at))

    def __contains__(self, item: EditTargetId) -> bool:
        """
        If :py:attr:`Suggestion.at` is provided, check if item is a potential location to fix. If not, it will always
        return True.

        .. code-block:: python

            import usd_validation_nvidia

            suggestion = usd_validation_nvidia.Suggestion(
                callable=lambda stage, at: None,
                message="A suggestion",
                at=Sdf.Layer.FindOrOpen("helloworld.usda"),
            )
            target_id = usd_validation_nvidia.EditTargetId(
                layer_id=LayerId(identifier="helloworld.usda"),
                path=Sdf.Path("/World/Cube"),
            )
            print(target_id in suggestion) # Will print True

            target_id = usd_validation_nvidia.EditTargetId(
                layer_id=LayerId(identifier="goodbye.usda"),
                path=Sdf.Path("/World/Cube"),
            )
            print(target_id in suggestion) # Will print False

        Args:
            item (EditTargetId): An identifier representing a potential location to fix.

        Returns:
            True if the item could be a potential location to fix.
        """
        if self.at is None:
            return True

        lh: set[LayerId] = set()
        for fix_at in self.at:
            lh.update(target_id.layer_id for target_id in fix_at.get_spec_ids())

        rh: set[LayerId] = set(target_id.layer_id for target_id in item.get_spec_ids())
        return len(lh & rh) > 0

    def __call__(self, stage: Usd.Stage, obj: AtType | list[AtType]) -> None:
        self.callable(stage, obj)

    def __repr__(self):
        callable_name = (
            self.callable.func.__name__
            if isinstance(self.callable, partial)
            else getattr(self.callable, "__name__", "unknown")
        )
        at = self.at if self.at else None
        return f"{self.__class__.__name__}(callable={callable_name}, message='{self.message}', at={at})"


@singledispatch
def _to_stage_id(asset: Any) -> StageId | None:
    """
    Args:
        asset: An identifier to asset.

    Returns:
        The StageId representing the stage.
    """
    raise NotImplementedError(f"Unknown type {type(asset)}")


@_to_stage_id.register(type(None))
def _(asset: None) -> None:
    return None


@_to_stage_id.register(StageId)
def _(asset: StageId) -> StageId:
    return asset


@_to_stage_id.register(Usd.Stage)
def _(asset: Usd.Stage) -> StageId:
    return StageId.from_(asset)


@_to_stage_id.register(str)
def _(asset: str) -> StageId:
    return StageId(root_layer=LayerId(identifier=asset))


@dataclass(frozen=True)
class Issue:
    """Issues capture information related to Validation Rules:

    Use ``Issue(suggestions=[s1, s2])`` when there are **different fix strategies** for the
    same issue (e.g. move body0 vs. move body1). The user picks **which fix** to apply.

    Note: ``at`` is where the issue was found — it is independent of which suggestion is
    selected. All suggestions operate on the same ``at``. Each suggestion may have its own
    layer constraints (``Suggestion.at``) that filter which fix sites are valid.
    Use ``fix_sites_for(suggestion)`` to compute valid fix sites for a specific suggestion.

    Attributes:
        message (str | None): The reason this issue is mentioned.
        severity (IssueSeverity | None): The severity associated with the issue.
        rule (Type[BaseRuleChecker] | None): Optional. The class of rule detecting this issue.
        at (Identifier[AtType] | None): Optional. The Prim/Stage/Layer/SdfLayer/SdfPrim/etc.. where this issue arises.
        suggestion (Suggestion | None): Optional. The default (first) suggestion to apply. Cannot be
            combined with ``suggestions``; use one or the other. After construction, always equals
            ``suggestions[0]`` (or ``None``). Suggestion evaluation (i.e. suggestion()) could raise
            exception, in which case they will be handled by IssueFixer and mark as failed.
        suggestions (tuple[Suggestion, ...]): Optional. Multiple fix strategies for the same issue.
            Cannot be combined with ``suggestion``; use one or the other. The first suggestion
            is always the default used by ``IssueFixer.fix()``.
        asset (StageId | None): Optional. The asset where this Issue happens.
        requirement (Requirement | None): Optional. The requirement that this issue belongs to. When requirement is
            provided, code and message are ignored.


    The following exemplifies the expected arguments of an issue:

    .. code-block:: python

        import usd_validation_nvidia

        class MyRule(BaseRuleChecker):
            pass

        stage = Usd.Stage.Open('foo.usd')
        prim = stage.GetPrimAtPath("/");

        def my_suggestion(stage: Usd.Stage, at: Usd.Prim):
            pass

        issue = usd_validation_nvidia.Issue(
            identifier=Requirements.SL_001.code,
            message=Requirements.SL_001.message,
            severity=IssueSeverity.ERROR,
            rule=MyRule,
            at=stage,
            suggestion=Suggestion(my_suggestion, "A good suggestion"),
        )

    """

    message: str | None = None
    severity: IssueSeverity | None = None
    rule: RuleType | None = None
    at: AtType | Identifier[AtType] | list[AtType] | list[Identifier[AtType]] | None = None
    suggestion: Suggestion | None = None
    suggestions: tuple[Suggestion, ...] = ()
    asset: StageId | None = None
    code: str | None = None  # Deprecated, use requirement instead
    requirement: Requirement | RequirementRefProtocol | None = None

    def __post_init__(self):
        if self.requirement is not None:
            if not self.code:
                object.__setattr__(self, "code", self.requirement.code)
            if not self.message and isinstance(self.requirement, RequirementProtocol):
                object.__setattr__(self, "message", self.requirement.message)

        if self.message is None:
            raise ValueError("Invalid message value.")

        if self.severity is None:
            raise ValueError("Invalid severity value.")

        if self.rule is not None:
            if not hasattr(self.rule, "__name__"):
                raise ValueError("Invalid rule value.")

        if self.rule is not None and self.requirement is not None:
            if not RequirementsRegistry().is_registered(self.rule, self.requirement):
                raise ValueError(
                    f"Rule {self.rule.__name__} is not registered to requirement {self.requirement.code}@{self.requirement.version}."
                )

        if self.suggestion is not None:
            if not isinstance(self.suggestion, Suggestion):
                raise TypeError("suggestion must be an instance of Suggestion.")

        if self.suggestion is not None and self.suggestions:
            raise ValueError("Use suggestion or suggestions, not both.")

        # Normalize to a canonical tuple
        if self.suggestions:
            for s in self.suggestions:
                if not isinstance(s, Suggestion):
                    raise TypeError("All items in suggestions must be Suggestion instances.")
            merged = tuple(self.suggestions)
        elif self.suggestion is not None:
            merged = (self.suggestion,)
        else:
            merged = ()
        object.__setattr__(self, "suggestions", merged)
        object.__setattr__(self, "suggestion", merged[0] if merged else None)

        object.__setattr__(self, "at", to_identifier(self.at))
        object.__setattr__(self, "asset", _to_stage_id(self.asset))

    @classmethod
    @deprecated("Use Issue constructor instead")
    def from_message(cls, severity: IssueSeverity, message: str) -> Issue:
        return Issue(
            message=message,
            severity=severity,
        )

    @classmethod
    @deprecated("Use Issue constructor instead")
    def from_(cls, severity: IssueSeverity, rule: RuleType, message: str) -> Issue:
        return Issue(
            message=message,
            severity=severity,
            rule=rule,
        )

    @classmethod
    @cache
    def none(cls) -> Issue:
        """
        Returns: Singleton object representing no Issue.
        """
        return Issue(message="No Issue", severity=IssueSeverity.NONE)

    @property
    def tags(self) -> tuple[str, ...] | None:
        if self.requirement is not None:
            return self.requirement.tags
        return None

    def fix_sites_for(self, suggestion: Suggestion | None = None) -> list[EditTargetId]:
        """Compute valid fix sites filtered through a specific suggestion.

        ``issue.at`` is where the issue was found — the same base set for all suggestions.
        ``suggestion.at`` is a layer constraint that filters which of those locations
        this particular suggestion can be applied at. Results are ordered with matching
        (preferred) sites first, then non-matching sites.

        Args:
            suggestion: The suggestion to filter by. If None, uses self.suggestion.

        Returns:
            A list of fix sites, preferred sites first.
        """
        s = suggestion or self.suggestion
        if self.at is None:
            return []
        if isinstance(self.at, tuple):
            spec_ids: list[EditTargetId] = [spec_id for location in self.at for spec_id in location.get_spec_ids()]
        else:
            spec_ids: list[EditTargetId] = self.at.get_spec_ids()
        if s is None:
            return spec_ids
        included = list(filter(lambda node_id: node_id in s, spec_ids))
        excluded = list(filter(lambda node_id: node_id not in s, spec_ids))
        return included + excluded

    @property
    def all_fix_sites(self) -> list[EditTargetId]:
        """
        Returns:
            A list of all possible fix sites for the default suggestion.
        """
        return self.fix_sites_for(self.suggestion)

    @property
    def default_fix_site(self) -> EditTargetId | None:
        """
        Returns:
            The default fix site. The default fix site is generally the Node at root layer.
            Rules can override this behavior by supplying ``Suggestion.at`` locations.
        """
        return next(iter(self.all_fix_sites), None)


@runtime_checkable
class IssuePredicate(Protocol):
    """
    An IssuePredicate is a callable that returns True or False for a specific Issue.

    Args:
        issue (Issue): The issue to check.

    Returns:
        (bool): True if the issue matches the predicate, False otherwise.
    """

    __slots__ = ()

    @abstractmethod
    def __call__(self, issue: Issue) -> bool:
        pass


@runtime_checkable
class IssueGroupBy(Protocol):
    """
    An IssueGroupBy is a callable that returns a list linking an Issue to a specific group.

    Args:
        issues (list[Issue]): The issues to group.

    Returns:
        (list[tuple[Any, Issue]]): A list of tuples, where the first element is the group name and the second element is the issue.
    """

    __slots__ = ()

    @abstractmethod
    def __call__(self, issues: list[Issue]) -> list[tuple[Any, Issue]]:
        pass


@dataclass(frozen=True)
class _Predicate(IssuePredicate):
    """Internal: An IssuePredicate with representation."""

    name: str
    func: IssuePredicate
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[Any, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"IssuePredicates.{self.name}{self.args}{self.kwargs}"

    def __call__(self, issue: Issue) -> bool:
        return self.func(issue)


class IssuePredicates:
    """
    Convenient methods to filter issues. Additionally, provides :py:meth:`IssuePredicates.And` and
    :py:meth:`IssuePredicates.Or` predicates to chain multiple predicates, see example below.

    .. code-block:: python

        import usd_validation_nvidia

        issues = [
            usd_validation_nvidia.Issue(
                severity=usd_validation_nvidia.IssueSeverity.ERROR, message="This is an error"),
            usd_validation_nvidia.Issue(
                severity=usd_validation_nvidia.IssueSeverity.WARNING, message="Important warning!"),
        ]
        filtered = list(filter(
            usd_validation_nvidia.IssuePredicates.And(
                usd_validation_nvidia.IssuePredicates.IsError(),
                usd_validation_nvidia.IssuePredicates.ContainsMessage("Important"),
            ),
            issues
        ))
    """

    @staticmethod
    @cache
    def Any() -> IssuePredicate:
        """
        Returns:
            A dummy filter that does not filter.
        """
        return _Predicate(IssuePredicates.Any.__name__, lambda issue: True)

    @staticmethod
    @cache
    def IsFailure() -> IssuePredicate:
        """
        Returns:
            A filter for Issues marked as failure.
        """
        return _Predicate(IssuePredicates.IsFailure.__name__, lambda issue: issue.severity is IssueSeverity.FAILURE)

    @staticmethod
    @cache
    def IsWarning() -> IssuePredicate:
        """
        Returns:
            A filter for Issues marked as warnings.
        """
        return _Predicate(IssuePredicates.IsWarning.__name__, lambda issue: issue.severity is IssueSeverity.WARNING)

    @staticmethod
    @cache
    def IsError() -> IssuePredicate:
        """
        Returns:
            A filter for Issues marked as errors.
        """
        return _Predicate(IssuePredicates.IsError.__name__, lambda issue: issue.severity is IssueSeverity.ERROR)

    @staticmethod
    @cache
    def IsInfo() -> IssuePredicate:
        """
        Returns:
            A filter for Issues marked as infos.
        """
        return _Predicate(IssuePredicates.IsInfo.__name__, lambda issue: issue.severity is IssueSeverity.INFO)

    @staticmethod
    @cache
    def IsSuccess() -> IssuePredicate:
        """
        Returns:
            A filter for Issues marked as success, i.e. IssueSeverity.NONE.
        """
        return _Predicate(IssuePredicates.IsSuccess.__name__, lambda issue: issue.severity is IssueSeverity.NONE)

    @staticmethod
    def ContainsMessage(text: str) -> IssuePredicate:
        """
        Args:
            text: A specific text to filter the message in issues.
        Returns:
            A filter for messages containing ``text``.
        """
        return _Predicate(IssuePredicates.ContainsMessage.__name__, lambda issue: text in issue.message, args=(text,))

    @staticmethod
    def IsRule(rule: str | RuleType) -> IssuePredicate:
        """
        Args:
            rule (str | RuleType): The rule to filter.

        Returns:
            A filter for issues with the rule.
        """
        return _Predicate(
            IssuePredicates.IsRule.__name__,
            lambda issue: issue.rule.__name__ == rule if isinstance(rule, str) else issue.rule is rule,
            args=(rule,),
        )

    @staticmethod
    @cache
    def HasLocation() -> IssuePredicate:
        """
        Returns:
            A filter for issues with location, i.e. `at`
        """
        return _Predicate(IssuePredicates.HasLocation.__name__, lambda issue: issue.at is not None)

    @staticmethod
    @cache
    def HasFix() -> IssuePredicate:
        """
        Returns:
            A filter for issues with a fix.
        """
        return _Predicate(IssuePredicates.HasFix.__name__, lambda issue: issue.suggestion is not None)

    @staticmethod
    @cache
    def HasRootLayer() -> IssuePredicate:
        """
        Returns:
            A filter for issues with a root layer.
        """

        def wrapper(issue: Issue) -> bool:
            if isinstance(issue.at, StageId | PrimId | PropertyId):
                return issue.default_fix_site and issue.default_fix_site.layer_id == issue.at.stage_id.root_layer
            else:
                return False

        return _Predicate(IssuePredicates.HasRootLayer.__name__, wrapper)

    @staticmethod
    def And(*predicates) -> IssuePredicate:
        """
        Args:
            predicates: One or more IssuePredicate.

        Returns:
            A predicate joining predicates by ``and`` condition.
        """
        if len(predicates) == 0:
            return IssuePredicates.Any()
        elif len(predicates) == 1:
            return predicates[0]
        else:
            return _Predicate(
                IssuePredicates.And.__name__,
                lambda issue: all(predicate(issue) for predicate in predicates),
                args=predicates,
            )

    @staticmethod
    def Or(*predicates) -> IssuePredicate:
        """
        Args:
            predicates: One or more IssuePredicate.

        Returns:
            A predicate joining predicates by ``or`` condition.
        """
        if len(predicates) == 0:
            return IssuePredicates.Any()
        elif len(predicates) == 1:
            return predicates[0]
        else:
            return _Predicate(
                IssuePredicates.Or.__name__,
                lambda issue: any(predicate(issue) for predicate in predicates),
                args=predicates,
            )

    @staticmethod
    def Not(predicate: IssuePredicate) -> IssuePredicate:
        """
        Returns:
            A predicate joining predicates by ``not`` condition.
        """
        return _Predicate(
            IssuePredicates.Not.__name__,
            lambda issue: not predicate(issue),
            args=(predicate,),
        )

    @staticmethod
    def HasCode() -> IssuePredicate:
        """
        Returns:
            A filter for issues with requirement identifier.
        """
        return _Predicate(IssuePredicates.HasCode.__name__, lambda issue: issue.code is not None)

    # matchcode
    @staticmethod
    def MatchesCode(code: str) -> IssuePredicate:
        """
        Returns:
            A filter for issues with matching code.
        """
        return _Predicate(
            IssuePredicates.MatchesCode.__name__,
            lambda issue: issue.code == code,
            args=(code,),
        )

    @staticmethod
    def MatchesAnyCode(codes: Sequence[str]) -> IssuePredicate:
        """
        Returns:
            A filter for issues with matching code.
        """
        return _Predicate(
            IssuePredicates.MatchesAnyCode.__name__,
            lambda issue: issue.code in codes,
            args=(codes,),
        )

    @staticmethod
    def MatchesToken(token: str) -> IssuePredicate:
        """
        Returns:
            A filter for issues with matching token.
        """

        def wrapper(issue: Issue) -> bool:
            if issue.message is not None and token in issue.message:
                return True
            elif issue.code is not None and token in issue.code:
                return True
            elif issue.rule is not None and token in issue.rule.__name__:
                return True
            elif issue.asset is not None and token in issue.asset.as_str():
                return True
            elif isinstance(issue.at, tuple) and any(token in loc.as_str() for loc in issue.at):
                return True
            elif isinstance(issue.at, Identifier) and token in issue.at.as_str():
                return True
            elif issue.suggestion is not None and token in issue.suggestion.message:
                return True
            else:
                return False

        return _Predicate(IssuePredicates.MatchesToken.__name__, wrapper, args=(token,))

    @staticmethod
    @cache
    def HasTag(tag: str) -> IssuePredicate:
        """
        Returns:
            A filter for issues with specific tag.
        """
        return _Predicate(
            IssuePredicates.HasTag.__name__,
            lambda issue: tag.lower() in map(str.lower, issue.tags or ()),
            args=(tag,),
        )


class IssueGroupsBy:
    """
    Convenient methods to group issues.

    Examples:

        Group by messages.

        .. code-block:: python

            import collections
            import usd_validation_nvidia

            issues = [
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim1",
                    rule=usd_validation_nvidia.TypeChecker),
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim2",
                    rule=usd_validation_nvidia.TypeChecker),
            ]
            groups = set()
            for group, issue in usd_validation_nvidia.IssueGroupsBy.message()(issues):
                groups.add(group)
            print(groups)

        Output

        .. code-block:: bash

            {'This is an error at .*'}

        Groups by rule.

        .. code-block:: python

            import collections
            import usd_validation_nvidia

            issues = [
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim1",
                    rule=usd_validation_nvidia.TypeChecker),
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim2",
                    rule=usd_validation_nvidia.TypeChecker),
            ]
            groups = set()
            for group, issue in usd_validation_nvidia.IssueGroupsBy.rule()(issues):
                groups.add(group)
            print(groups)

        Output

        .. code-block:: bash

            {<class 'usd_validation_nvidia.TypeChecker'>}

        Groups by severity.

        .. code-block:: python

            import collections
            import usd_validation_nvidia

            issues = [
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim1",
                    rule=usd_validation_nvidia.TypeChecker),
                usd_validation_nvidia.Issue(
                    severity=usd_validation_nvidia.IssueSeverity.ERROR,
                    message="This is an error at Prim2",
                    rule=usd_validation_nvidia.TypeChecker),
            ]
            groups = set()
            for group, issue in usd_validation_nvidia.IssueGroupsBy.severity()(issues):
                groups.add(group)
            print(groups)

        .. code-block:: bash

            {<IssueSeverity.ERROR: 0>}

    """

    @classmethod
    @cache
    def asset(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue asset and the issue.
        """
        return lambda issues: [(issue.asset, issue) for issue in issues]

    @classmethod
    @cache
    def rule(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue rule and the issue.
        """
        return lambda issues: [(issue.rule, issue) for issue in issues]

    @classmethod
    @cache
    def rule_name(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue rule name and the issue.
        """
        return lambda issues: [(issue.rule.__name__ if issue.rule else "", issue) for issue in issues]

    @classmethod
    @cache
    def severity(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue severity and the issue.
        """
        return lambda issues: [(issue.severity, issue) for issue in issues]

    @classmethod
    @cache
    def message(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue message and the issue.
        """

        def wrapper(issues: list[Issue]) -> list[tuple[Any, Issue]]:
            reorder: dict[Any, list[Issue]] = defaultdict(list)
            for issue in issues:
                reorder[issue.rule].append(issue)

            message_to_pattern: dict[str, str] = {}
            for key, value in reorder.items():
                tree: _PatternTree = _PatternTree()
                for issue in value:
                    tree.insert(issue.message)
                for pattern, messages in tree.as_dict().items():
                    for message in messages:
                        message_to_pattern[message] = pattern

            return [(message_to_pattern[issue.message], issue) for issue in issues]

        return wrapper

    @classmethod
    @cache
    def code(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue code and the issue.
        """
        return lambda issues: [(issue.code or "", issue) for issue in issues]

    @classmethod
    @cache
    def requirement(cls) -> IssueGroupBy:
        """
        Returns a list of tuples with the issue requirement code and the issue.
        """
        return lambda issues: [(issue.code or "", issue) for issue in issues]


@dataclass(frozen=True)
class IssuesList(Sequence[Issue]):
    """
    A list of issues, provides convenient features to filter/group by issues.

    Attributes:
        issues (list[Issue]): The issues in the list.
        success (list[Issue]): The issues that are not issues.
        name (Any | None): The name of the list.
    """

    issues: list[Issue] = field(default_factory=list)
    success: list[Issue] = field(default_factory=list)
    name: Any | None = field(default=None)

    def __len__(self) -> int:
        return len(self.issues)

    def __getitem__(self, item: int) -> Issue:
        return self.issues[item]

    def filter_by(self, predicate: IssuePredicate | None = None) -> IssuesList:
        """
        Args:
            predicate: The predicate to filter issues.

        Returns:
            A subset of the issues for which the predicate is True.
        """
        return IssuesList(
            name=self.name,
            issues=list(filter(predicate, self.issues)),
            success=list(filter(predicate, self.success)),
        )

    def count_if(self, predicate: IssuePredicate | None = None) -> int:
        """
        Args:
            predicate: The predicate to count issues.

        Returns:
            The number of issues for which the predicate is True.
        """
        return sum(1 for _ in filter(predicate, self.issues))

    def group_by(self, group_by: IssueGroupBy | None = None) -> list[IssuesList]:
        """
        Args:
            group_by: A grouping function.

        Returns:
            All groups generated by the grouping function.
        """
        grouping: dict[Any, IssuesList] = {}
        for group, issue in group_by(self.issues + self.success):
            if group not in grouping:
                grouping[group] = IssuesList(name=group, issues=[], success=[])
            if issue.severity is IssueSeverity.NONE:
                grouping[group].success.append(issue)
            else:
                grouping[group].issues.append(issue)
        return list(grouping.values())

    def merge(self, other: IssuesList) -> IssuesList:
        """
        Args:
            other: Another issue group.

        Returns:
            A new group that combines both existing groups.
        """
        return IssuesList(
            name=None,
            issues=self.issues + other.issues,
            success=self.success + other.success,
        )

    def __call__(
        self,
        predicate: IssuePredicate | None = None,
    ) -> IssuesList:
        """Filter Issues using an option IssuePredicate.

        Args:
            predicate: Optional. A predicate to filter the issues.

        Returns:
            An issue group.
        """
        return self.filter_by(predicate)
