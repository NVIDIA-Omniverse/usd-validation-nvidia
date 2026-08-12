Authoring rules
###############

``usd-validation-nvidia`` is rule-based: each check is a class that inspects a
``Usd.Stage`` (or its layers, prims, or package contents) and reports
:py:class:`~usd_validation_nvidia.Issue` objects. This page shows how to write, register,
and distribute your own rules.

The rule interface
==================

A rule subclasses :py:class:`~usd_validation_nvidia.BaseRuleChecker` and overrides one or
more ``Check*`` callbacks. The engine invokes them as it walks an asset, so a rule only
implements the callbacks it needs:

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Callback
      - Invoked with
    * - ``CheckStage(usdStage)``
      - The composed ``Usd.Stage`` (whole-stage checks).
    * - ``CheckPrim(prim)``
      - Each ``Usd.Prim`` on the stage.
    * - ``CheckLayer(layer)``
      - Each ``Sdf.Layer`` used by the asset.
    * - ``CheckDependencies(usdStage, layerDeps, assetDeps)``
      - The stage together with its layer and asset dependencies.
    * - ``CheckUnresolvedPaths(unresolvedPaths)``
      - Asset paths that did not resolve.
    * - ``CheckDiagnostics(diagnostics)``
      - Diagnostics emitted while opening/composing the stage.
    * - ``CheckZipFile(zipFile, packagePath)``
      - Each ``Usd.ZipFile`` for ``.usdz`` packages.
    * - ``CheckFormatDependency(dependency)``
      - Each format-specific dependency (a ``FormatDependency``).
    * - ``ResetCaches()``
      - Hook to clear any per-asset state the rule caches between runs.

Report findings from inside a callback with the helper methods, in increasing severity:

- ``self._AddInfo(message, ...)`` - informational only.
- ``self._AddWarning(message, ...)`` - a non-blocking concern.
- ``self._AddFailedCheck(message, ...)`` - a normative failure.
- ``self._AddError(message, ...)`` - the rule itself could not run.

Each accepts an ``at=`` location (a prim, property, layer, or other
:py:class:`~usd_validation_nvidia.Identifier`), an optional ``code``, and an optional
``requirement``. ``_AddFailedCheck``, ``_AddError``, and ``_AddWarning`` also take one or
more ``suggestion``\ s used for auto-fixing (see below); ``_AddInfo`` does not.

Registering a rule
==================

Decorate the class with :py:func:`~usd_validation_nvidia.register_rule` and a category
name. Registered rules become part of every default ``ValidationEngine``:

.. code-block:: python

    from pxr import UsdGeom
    from usd_validation_nvidia import BaseRuleChecker, register_rule


    @register_rule("MyStudio")
    class VisibilityAttributeChecker(BaseRuleChecker):
        """Meshes should author a 'visibility' attribute."""

        def CheckPrim(self, prim):
            if not prim.IsA(UsdGeom.Mesh):
                return
            if not prim.GetAttribute("visibility").IsValid():
                self._AddWarning(
                    message=f"Mesh <{prim.GetPath()}> does not author 'visibility'.",
                    at=prim,
                )

Run it like any other rule; an engine created with no arguments discovers all registered
rules:

.. code-block:: python

    from usd_validation_nvidia import ValidationEngine

    engine = ValidationEngine()
    results = engine.validate("asset.usda")

``register_rule`` also accepts ``skip=`` (register conditionally, for example in tests) and
``overwrite=`` (replace an existing rule in a category). Categories group related rules:
the CLI's ``--category`` flag and ``register_rule`` use them. To turn individual rules on or
off on an engine, use :py:meth:`enable_rule` / :py:meth:`disable_rule`.

Providing an auto-fix
=====================

Attach a :py:class:`~usd_validation_nvidia.Suggestion` to an issue to make it fixable.
:py:class:`~usd_validation_nvidia.IssueFixer` applies the suggestion to the stage and
writes the result back:

.. code-block:: python

    from usd_validation_nvidia import IssueFixer

    fixer = IssueFixer("asset.usda")
    fixer.fix(results.issues())
    fixer.save()

See :doc:`api` for the ``Suggestion``, ``IssueFixer``, and ``Issue`` signatures.

Wrapping a native USD validator
===============================

OpenUSD ships its own ``UsdValidation`` validators. Rather than reimplement one, subclass
:py:class:`~usd_validation_nvidia.UsdValidatorAdapter` and name the validator to expose it
as a rule:

.. code-block:: python

    from usd_validation_nvidia import register_rule, UsdValidatorAdapter


    @register_rule("Basic", skip="usdUtilsValidators:UsdzPackageValidator" not in UsdValidatorAdapter)
    class UsdzPackageValidator(UsdValidatorAdapter):
        @classmethod
        def validator_name(cls):
            return "usdUtilsValidators:UsdzPackageValidator"

Distributing rules as a plugin
==============================

Rules register when their module is imported. To ship rules in your own package so they
load automatically, expose a plugin through the ``usd_validation_nvidia`` entry-point group;
the plugin manager discovers it at startup:

.. code-block:: toml

    # pyproject.toml of your rule package
    [project.entry-points."usd_validation_nvidia"]
    my_studio_rules = "my_studio_rules:Plugin"

The referenced object implements :py:class:`~usd_validation_nvidia.PluginProtocol`: an
``on_startup()`` hook, where you import or register your rule modules, and an
``on_shutdown()`` hook. :py:class:`~usd_validation_nvidia.DefaultPlugin` is the built-in
reference implementation. The legacy ``omni.asset_validator`` group is also scanned for
backward compatibility, but new plugins should use ``usd_validation_nvidia``.
