# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import asyncio
import gettext
import inspect
import logging
import os
import sys
from collections import Counter
from functools import lru_cache

from pxr import Tf

from ._assets import AssetProgress
from ._base_rule_checker import BaseRuleChecker
from ._capabilities import Capability, CapabilityRegistry
from ._categories import CategoryRuleRegistry
from ._csv_reports import IssueCSVData
from ._engine import ValidationEngine
from ._features import Feature, FeatureRegistry
from ._fix import IssueFixer
from ._issues import Issue, IssueGroupBy, IssueGroupsBy, IssuePredicate, IssuePredicates, IssueSeverity, IssuesList
from ._json_reports import export_json_file
from ._parameters import ParameterMapping, UserParameter
from ._registry import VersionedRegistry
from ._requirements import Requirement, RequirementsRegistry
from ._results import Results, ResultsList
from ._semver import SemVer
from ._version import __version__

__all__ = [
    "ValidationArgsExec",
    "ValidationNamespaceExec",
    "cli_main",
    "create_validation_parser",
]

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class _ArgFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


class _ArgParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        args = {"prog": self.prog, "message": message}
        self.exit(2, gettext.gettext("%(prog)s: error: %(message)s\n") % args)


class _ExplainAction(argparse.Action):
    def __init__(
        self,
        option_strings,
        dest=argparse.SUPPRESS,
        default=argparse.SUPPRESS,
        help="Provide descriptions for each argument provided and exit.",
    ):
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        registry = CategoryRuleRegistry()
        for rule_name in namespace.rule:
            if rule := registry.find_rule(rule_name):
                print(f"{rule.__name__} : {rule.GetDescription()}\n")
        for rule_name in namespace.disable_rule:
            if rule := registry.find_rule(rule_name):
                print(f"{rule.__name__} : {rule.GetDescription()}\n")
        for category in namespace.category:
            for rule in registry.get_rules(category):
                print(f"{rule.__name__} : {rule.GetDescription()}\n")
        for category in namespace.disable_category:
            for rule in registry.get_rules(category):
                print(f"{rule.__name__} : {rule.GetDescription()}\n")
        parser.exit()


def _create_options(registry: VersionedRegistry) -> list[str]:
    """
    Create options for the CLI argument parser from a versioned registry.
    """
    options: list[str] = []
    # Options without version
    for key in registry.latest_keys():
        id: str = key.id
        options.append(id)
    # Options with version
    for key in registry.latest_keys():
        id: str = key.id
        version: SemVer = key.version
        options.append(f"{id}@{version}")
    options.sort()
    return options


def _parse_parameter_pair(arg: str) -> tuple[str, int | float | bool | str]:
    if "=" not in arg:
        raise argparse.ArgumentTypeError(f"Invalid format '{arg}'. Expected NAME=VALUE")

    name, _, value = arg.partition("=")
    name = name.strip()
    value = value.strip()

    if not name:
        raise argparse.ArgumentTypeError(f"Invalid parameter '{arg}': missing name")

    if value.lower() == "true":
        return (name, True)
    elif value.lower() == "false":
        return (name, False)
    else:
        try:
            return (name, int(value))
        except ValueError:
            try:
                return (name, float(value))
            except ValueError:
                return (name, value)


def create_validation_parser() -> argparse.ArgumentParser:
    """
    Creates an argument parser with common options, this includes:

    For ValidationEngine:

    - init-rules/no-init-rules: Optional. Default True. Sets ValidationEngine, init_rules argument.
    - variants/no-variants: Optional. Default True. Sets ValidationEngine, variants argument.
    - rule/disable-rule: Optional. Enables/Disable rules in ValidationEngine.
    - category/disable-category. Optional. Enable/Disable categories in ValidationEngine.
    - asset. Required. The asset in which to perform validation.

    `enable-rule` and `enable-category` are alias for `rule` and `category` respectively.

    For IssueFixer:

    - predicate: Optional. Issues to filter for IssueFixer.
    - fix/no-fix: Optional. Whether to apply IssueFixer after ValidationEngine.

    Other options:
    - version: Print the version of omni.asset_validator.
    """
    parser = _ArgParser(allow_abbrev=False)
    parser.prog = "validate"
    parser.formatter_class = _ArgFormatter
    parser.description = inspect.cleandoc(
        """
        Utility for USD validation to ensure assets run smoothly across all OpenUSD
        products. Validation is based on the USD ComplianceChecker (i.e. the same
        backend as the usdchecker commandline tool), and has been extended with
        additional rules as follows:

        - Additional rules applicable in the broader OpenUSD ecosystem.
        - Configurable end-user rules that can be specific to individual company
          and/or team workflows.

        Note this level of configuration requires setting the environment,
        prior to launching this tool.
        """
    )
    parser.epilog = "See https://tinyurl.com/omni-asset-validator for more details."
    parser.add_argument(
        "asset",
        metavar="ASSET",
        type=str,
        nargs=1,
        help=inspect.cleandoc(
            """
            A single OpenUSD Asset.
            Note: This can be a file or folder.
            """
        ),
    )
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    # Explain
    parser.add_argument(
        "-e",
        "--explain",
        action=_ExplainAction,
    )
    # Rules
    rules: str = "\n".join(cls.__name__ for cls in CategoryRuleRegistry().rules)
    parser.add_argument(
        "-r",
        "--rule",
        "--enable-rule",
        metavar="RULE",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=[cls.__name__ for cls in CategoryRuleRegistry().rules],
        help=inspect.cleandoc(f"Rule to select. Valid options include:\n{rules}"),
    )
    parser.add_argument(
        "-D",  # For backwards compatibility
        "--disable-rule",
        "--disableRules",  # For backwards compatibility
        metavar="RULE",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=[cls.__name__ for cls in CategoryRuleRegistry().rules],
        help=inspect.cleandoc(f"Rule to disable. Valid options include:\n{rules}"),
    )
    # Categories
    categories: str = "\n".join(category for category in CategoryRuleRegistry().categories)
    parser.add_argument(
        "-c",
        "--category",
        "--enable-category",
        metavar="CATEGORY",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=list(CategoryRuleRegistry().categories),
        help=inspect.cleandoc(f"Category to select. Valid options include:\n{categories}"),
    )
    parser.add_argument(
        "--disable-category",
        metavar="CATEGORY",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=list(CategoryRuleRegistry().categories),
        help=inspect.cleandoc(f"Category to disable. Valid options include:\n{categories}"),
    )
    requirements: list[str] = _create_options(RequirementsRegistry())
    parser.add_argument(
        "--requirement",
        metavar="REQUIREMENT",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=requirements,
        help=inspect.cleandoc(f"Requirement to add. Valid options include:\n{os.linesep.join(requirements)}"),
    )
    capabilities: list[str] = _create_options(CapabilityRegistry())
    parser.add_argument(
        "--capability",
        metavar="CAPABILITY",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=capabilities,
        help=inspect.cleandoc(f"Capability to add. Valid options include:\n{os.linesep.join(capabilities)}"),
    )
    features: list[str] = _create_options(FeatureRegistry())
    parser.add_argument(
        "--feature",
        "--enable-feature",
        metavar="FEATURE",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=features,
        help=inspect.cleandoc(f"Feature to enable. Valid options include:\n{os.linesep.join(features)}"),
    )
    parser.add_argument(
        "--disable-feature",
        metavar="FEATURE",
        required=False,
        type=str,
        default=[],
        action="append",
        choices=features,
        help=inspect.cleandoc(f"Feature to disable. Valid options include:\n{os.linesep.join(features)}"),
    )
    # Parameters
    parser.add_argument(
        "--parameter",
        metavar="PARAMETER",
        required=False,
        type=_parse_parameter_pair,
        default=[],
        action="append",
        help="Parameter to override in NAME=VALUE format. Can be specified multiple times.",
    )
    # Fixes
    parser.add_argument(
        "-f",  # For backwards compatibility
        "--fix",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Whether to fix issues.",
    )
    # Predicates
    issue_predicates = [
        IssuePredicates.Any.__name__,
        IssuePredicates.IsFailure.__name__,
        IssuePredicates.IsWarning.__name__,
        IssuePredicates.IsError.__name__,
        IssuePredicates.HasRootLayer.__name__,
    ]
    issue_predicates.sort()
    issue_predicates_help = "\n".join(issue_predicates)
    parser.add_argument(
        "-p",
        "--predicate",
        metavar="PREDICATE",
        required=False,
        type=str,
        choices=issue_predicates,
        help=inspect.cleandoc(f"Predicate to select. Valid options include:\n{issue_predicates_help}"),
    )
    # Group by
    issue_groups_by = [
        IssueGroupsBy.rule_name.__name__,
        IssueGroupsBy.requirement.__name__,
    ]
    issue_groups_by.sort()
    issue_groups_by_help = "\n".join(issue_groups_by)
    parser.add_argument(
        "--group-by",
        metavar="GROUP_BY",
        required=False,
        type=str,
        choices=issue_groups_by,
        help=inspect.cleandoc(f"Group by. Valid options include:\n{issue_groups_by_help}"),
    )
    # Init rules
    parser.add_argument(
        "-d",  # For backwards compatibility
        "--init-rules",
        "--defaultRules",  # For backwards compatibility
        default=True,
        action=argparse.BooleanOptionalAction,
        help=inspect.cleandoc(
            """
            Whether to use the default enabled validation rules.
            Opt-out of this behavior to gain finer control over
            the rules using the --categories and --rules flags.
            """
        ),
    )
    # Variants
    parser.add_argument(
        "--variants",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Whether to set variants. Note: This can be expensive.",
    )
    # CSV Output
    parser.add_argument(
        "--csv-output",
        metavar="CSV",
        required=False,
        type=str,
        help="Path to the CSV output file.",
    )
    # JSON Output
    parser.add_argument(
        "--json-output",
        metavar="JSON",
        required=False,
        type=str,
        help="Path to the JSON output file.",
    )
    return parser


class ValidationNamespaceExec:
    """
    Uses Argument Parser Namespace to run validation. Useful for CLI tools.
    """

    def __init__(self, namespace: argparse.Namespace):
        self._namespace = namespace

    @property
    def variants(self) -> bool:
        """
        Returns:
            The `variants` option value.
        """
        return self._namespace.variants

    @property
    def init_rules(self) -> bool:
        """
        Returns:
            The `init_rules` option value.
        """
        return (
            self._namespace.init_rules
            and not self.category_rules
            and not self.rules
            and not self.requirements
            and not self.capabilities
            and not self.features
        )

    @property
    def asset(self) -> str | None:
        """
        Returns:
            The `asset` option value.
        """
        return self._namespace.asset[0] if self._namespace.asset else None

    @property
    def fix(self) -> bool:
        """
        Returns:
            The `fix` option value.
        """
        return self._namespace.fix

    @property
    def predicate(self) -> IssuePredicate:
        return (
            getattr(IssuePredicates, self._namespace.predicate)()
            if self._namespace.predicate
            else IssuePredicates.Any()
        )

    @property
    def group_by(self) -> IssueGroupBy:
        if self.requirements or self.capabilities or self.features:
            default = IssueGroupsBy.requirement()
        else:
            default = IssueGroupsBy.rule_name()
        return getattr(IssueGroupsBy, self._namespace.group_by)() if self._namespace.group_by else default

    @property
    def rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `rules` option value.
        """
        return self.enabled_rules

    def _key_to_values(self, keys: list[str], registry: VersionedRegistry) -> list:
        """
        Convert a list of keys to values.
        """
        values = []
        for key in keys:
            if "@" in key:
                key, version = key.split("@", 1)
            else:
                key, version = key, None
            if value := registry.find(key, version):
                values.append(value)
        return values

    @property
    def requirements(self) -> list[Requirement]:
        """
        Returns:
            The `requirements` option value.
        """
        return self._key_to_values(self._namespace.requirement, RequirementsRegistry())

    @property
    def capabilities(self) -> list[Capability]:
        """
        Returns:
            The `capabilities` option value.
        """
        return self._key_to_values(self._namespace.capability, CapabilityRegistry())

    @property
    def features(self) -> list[Feature]:
        """
        Returns:
            The `features` option value (enabled features).
        """
        return self.enabled_features

    @property
    def enabled_features(self) -> list[Feature]:
        """
        Returns:
            The `enabled_features` option value.
        """
        return self._key_to_values(self._namespace.feature, FeatureRegistry())

    @property
    def disabled_features(self) -> list[Feature]:
        """
        Returns:
            The `disabled_features` option value.
        """
        return self._key_to_values(self._namespace.disable_feature, FeatureRegistry())

    @property
    def enabled_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `enable_rules` option value.
        """
        registry = CategoryRuleRegistry()
        rules = []
        for rule_name in self._namespace.rule:
            rule: type[BaseRuleChecker] | None = registry.find_rule(rule_name)
            if rule:
                rules.append(rule)
        return rules

    @property
    def disabled_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `disable_rules` option value.
        """
        registry = CategoryRuleRegistry()
        rules = []
        for rule_name in self._namespace.disable_rule:
            rule: type[BaseRuleChecker] | None = registry.find_rule(rule_name)
            if rule:
                rules.append(rule)
        return rules

    @property
    def category_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `category` options value.
        """
        return self.enabled_category_rules

    @property
    def enabled_category_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `enable_category` options value.
        """
        registry = CategoryRuleRegistry()
        rules = []
        for category in self._namespace.category:
            for rule in registry.get_rules(category):
                rules.append(rule)
        return rules

    @property
    def disable_category_rules(self) -> list[type[BaseRuleChecker]]:
        """
        Returns:
            The `disable_category` option value.
        """
        registry = CategoryRuleRegistry()
        rules = []
        for category in self._namespace.disable_category:
            for rule in registry.get_rules(category):
                rules.append(rule)
        return rules

    @property
    def csv_output(self) -> str | None:
        """
        Returns:
            The `csv-output` option value.
        """
        return self._namespace.csv_output

    @property
    def json_output(self) -> str | None:
        """
        Returns:
            The `json-output` option value.
        """
        return self._namespace.json_output

    @property
    def parameters(self) -> dict[str, int | float | bool | str]:
        """
        Returns:
            A dictionary of parameter names to values parsed from the `--parameter` option.
        """
        return dict(self._namespace.parameter)

    def _create_engine(self) -> ValidationEngine:
        return ValidationEngine(init_rules=self.init_rules, variants=self.variants)

    def _populate_engine(self, engine: ValidationEngine) -> None:
        for rule in self.rules:
            engine.enable_rule(rule)
        for rule in self.enabled_category_rules:
            engine.enable_rule(rule)
        for requirement in self.requirements:
            engine.enable_requirement(requirement)
        for capability in self.capabilities:
            engine.enable_capability(capability)
        for feature in self.enabled_features:
            engine.enable_feature(feature)
        for rule in self.disabled_rules:
            engine.disable_rule(rule)
        for rule in self.disable_category_rules:
            engine.disable_rule(rule)
        for feature in self.disabled_features:
            engine.disable_feature(feature)
        engine_parameters: ParameterMapping = engine.parameters
        for name, value in self.parameters.items():
            if name not in engine_parameters:
                continue  # Parameter is not referenced by any rule or requirement, skip it.
            engine.add_parameter(UserParameter(parameter=engine_parameters[name], assigned_value=value))

    def create_engine(self) -> ValidationEngine:
        if not self.asset:
            raise ValueError("Asset not given")
        engine = self._create_engine()
        self._populate_engine(engine)
        return engine

    @classmethod
    def _asset_progress_fn(cls, progress: AssetProgress) -> None:
        logger = logging.getLogger(__name__)

        @lru_cache(maxsize=16)
        def func(asset, percent) -> None:
            logger.info(f"Processing {asset}........{percent}%")

        func(progress.asset, int(progress.progress * 100))

    @classmethod
    def _log_issue(cls, group_name: str | None, issue: Issue) -> None:
        logger = logging.getLogger(__name__)
        tokens: list[str] = []
        tokens.append(f"[{group_name if group_name else 'other'}]")
        tokens.append(issue.message)
        if issue.at:
            tokens.append("At")
            if isinstance(issue.at, tuple):
                tokens.append(", ".join([at.as_str() for at in issue.at]))
            else:
                tokens.append(issue.at.as_str())
        message: str = " ".join(tokens)
        match issue.severity:
            case IssueSeverity.ERROR:
                logger.exception(message, exc_info=False)
            case IssueSeverity.FAILURE:
                logger.error(message)
            case IssueSeverity.WARNING:
                logger.warning(message)
            case IssueSeverity.INFO:
                logger.info(message)
            case _:
                logger.debug(message)

    @classmethod
    def _group_key_fn(cls, group: IssuesList) -> tuple[str, ...]:
        name: str = group.name or ""
        return tuple(name.split("."))

    def _asset_validated_fn(self, result: Results) -> None:
        logger = logging.getLogger(__name__)
        logger.info(f"Results for Asset '{result.asset}'")
        groups: list[IssuesList] = result.issues.filter_by(self.predicate).group_by(self.group_by)
        for group in sorted(groups, key=self._group_key_fn):
            for issue in group.issues:
                self._log_issue(group.name, issue)
        if self.fix:
            fixer = IssueFixer(result.asset)
            for item in fixer.fix(result.issues.filter_by(self.predicate)):
                logger.warning(f"{item.issue.message}........{item.status}")
            try:
                fixer.save()
            except (OSError, Tf.ErrorException) as e:
                logger.error(f"Failed to save fixes: {e}")

    def _assets_summary(self, results: ResultsList) -> None:
        logger = logging.getLogger(__name__)
        for group in results.issues().filter_by(self.predicate).group_by(self.group_by):
            mapper = Counter()
            for subgroup in group.group_by(IssueGroupsBy.severity()):
                mapper[subgroup.name] += len(subgroup)
            logger.info(
                f"{group.name if group.name else 'Others'}: "
                f"{mapper[IssueSeverity.FAILURE]} Failures / "
                f"{mapper[IssueSeverity.WARNING]} Warnings / "
                f"{mapper[IssueSeverity.ERROR]} Errors / "
                f"{mapper[IssueSeverity.INFO]} Infos "
            )
        # Group by severity
        logger.info("-" * 128)
        logger.info("Summary per Severity:")
        mapper = Counter()
        for group in results.issues().filter_by(self.predicate).group_by(IssueGroupsBy.severity()):
            mapper[group.name] += len(group)
        logger.info(f"Failures: {mapper[IssueSeverity.FAILURE]}")
        logger.info(f"Warnings: {mapper[IssueSeverity.WARNING]}")
        logger.info(f"Errors: {mapper[IssueSeverity.ERROR]}")
        logger.info(f"Infos: {mapper[IssueSeverity.INFO]}")

    def _export_csv(self, results: ResultsList) -> None:
        csv_data = IssueCSVData.from_(results)
        csv_data.export_csv(self.csv_output)

    def _export_json(self, results: ResultsList) -> None:
        export_json_file(self.json_output, results)

    async def _validate(self) -> bool:
        logger = logging.getLogger(__name__)
        engine = self.create_engine()
        asset: str = self.asset

        task: asyncio.Task = engine.validate_with_callbacks(
            asset=asset,
            asset_progress_fn=self._asset_progress_fn,
            asset_validated_fn=self._asset_validated_fn,
        )
        await task
        results: ResultsList = task.result()

        logger.info("-" * 128)
        has_issues: bool = results.issues()
        if not has_issues:
            logger.info("No issues found.")
        else:
            self._assets_summary(results)

        # Time per rule
        logger.debug("-" * 128)
        logger.debug("Time per Rule:")
        total_time: float = 0.0
        for rule, time in engine.stats.get_rule_times():
            logger.debug(f"{rule.__name__}: {round(time, 3)} s.")
            total_time += time
        logger.debug(f"Total Time: {round(total_time, 3)} s.")

        # Saving reports
        if self.csv_output:
            self._export_csv(results)
        if self.json_output:
            self._export_json(results)
        return not has_issues

    def run_validation(self) -> bool:
        return asyncio.run(self._validate())


ValidationArgsExec = ValidationNamespaceExec
"""
For backwards compatibility.
"""


def cli_main(args: list[str] | None = None):
    """
    Main method in command line interface.
    """
    parser = create_validation_parser()
    args = ValidationNamespaceExec(parser.parse_args(args))
    successful: bool = args.run_validation()
    if not successful:
        sys.exit(1)
