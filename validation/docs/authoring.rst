Authoring rules
###############

``usd-validation-nvidia`` is rule-based: each check is a class that inspects a
``Usd.Stage`` (or its layers, prims, or package contents) and reports
:py:class:`~usd_validation_nvidia.Issue` objects. This page shows how to write, register,
and distribute your own rules.

The rule interface
==================

A rule subclasses :py:class:`~usd_validation_nvidia.BaseRule` and overrides one or
more ``Check*`` callbacks. The engine invokes them as it walks an asset, so a rule only
implements the callbacks it needs:

``BaseRuleChecker`` remains available as a backward-compatible alias, but new rules should
subclass ``BaseRule``.

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
    from usd_validation_nvidia import BaseRule, register_rule


    @register_rule("MyStudio")
    class VisibilityAttributeChecker(BaseRule):
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

Running rules asynchronously
=============================

Validation can also work asynchronously, to avoid blocking the calling thread:

.. code-block:: python

    import asyncio
    from usd_validation_nvidia import ValidationEngine

    async def run_validation():
        engine = ValidationEngine()
        results = await engine.validate_async("asset.usda")

    asyncio.run(run_validation())

``validate_async`` also recursively validates folder/container URIs, which the blocking
``validate()`` method does not support. For per-asset and progress callbacks while a folder is
being validated, use :py:meth:`~usd_validation_nvidia.ValidationEngine.validate_with_callbacks`,
which returns an ``asyncio.Task``:

.. code-block:: python

    import asyncio
    from usd_validation_nvidia import AssetProgress, Results, ValidationEngine

    async def run_validation():
        engine = ValidationEngine()

        def on_progress(progress: AssetProgress) -> None:
            print(f"{progress.asset}: {progress.progress:.0%}")

        def on_validated(results: Results) -> None:
            for issue in results.issues():
                print(f"{results.asset} - {issue.severity}: {issue.message}")

        task = engine.validate_with_callbacks(
            "path/to/assets/",
            asset_progress_fn=on_progress,
            asset_validated_fn=on_validated,
        )
        await task

    asyncio.run(run_validation())

A ``Check*`` callback can also be declared ``async def`` directly, for example to await an
async lookup from inside the callback itself:

.. code-block:: python

    import asyncio

    from pxr import UsdGeom
    from usd_validation_nvidia import BaseRule, register_rule


    @register_rule("MyStudio")
    class VisibilityAttributeChecker(BaseRule):
        """Meshes should author a 'visibility' attribute."""

        async def CheckPrim(self, prim):
            if not prim.IsA(UsdGeom.Mesh):
                return
            if not prim.GetAttribute("visibility").IsValid():
                # await an async lookup here, e.g. a studio license/asset service call
                await asyncio.sleep(0)
                self._AddWarning(
                    message=f"Mesh <{prim.GetPath()}> does not author 'visibility'.",
                    at=prim,
                )

The engine detects coroutine callbacks automatically, so no special handling is needed to run
this rule: it works under the blocking ``engine.validate("asset.usda")`` just as well as under
``validate_async()``, and sync and async callbacks can be freely mixed on the same rule.

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

Running a callback in a process pool
====================================

By default every rule callback runs in the calling process. Decorate a callback with
:py:func:`~usd_validation_nvidia.multiprocess_safe` to declare it eligible for the
process pool that ``--process COUNT`` enables:

.. code-block:: python

    from usd_validation_nvidia import BaseRule, multiprocess_safe, register_rule


    @register_rule("Basic")
    class MyLayerRule(BaseRule):
        @multiprocess_safe
        def CheckLayer(self, layer):
            ...

The decorator is a declaration, not a request: marked callbacks run in the pool only
when process execution is enabled, and behave exactly as before when it is not. This
feature is experimental.

A callback is only safe to mark if it holds to both of these:

- **Its arguments and results survive pickling.** Work crosses a process boundary, so
  anything the callback receives or reports must be picklable. Validation identifiers
  and layer compliance events already are.
- **It shares no mutable state with the parent process.** Accumulating results on
  ``self`` across calls does not work — a worker mutates its own copy, and the parent
  never sees it. Report findings through the usual issue helpers instead.

``CheckStage`` and ``CheckPrim`` callbacks that traverse a live stage are generally not
safe to mark, because the stage does not cross the process boundary.

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

Loading authored specs and loose rules
======================================

For applications that load authored profile/specification content at runtime, use
``usd_profiles_nvidia.SpecificationsLoader`` to parse the content and
:py:func:`~usd_validation_nvidia.register_content` to register its requirement
definitions, capabilities, features, and profiles. Loose Python validator modules have a
separate lifecycle token from :py:func:`~usd_validation_nvidia.register_validation_modules`:

.. code-block:: python

    from usd_profiles_nvidia import SpecificationsLoader
    from usd_validation_nvidia import (
        register_content,
        register_validation_modules,
        unregister_content,
        unregister_validation_modules,
    )

    content = SpecificationsLoader(
        root_dir="specs",
        reverse_domain="com.example.assets",
    ).load()

    registered_modules = None
    try:
        register_content(content)
        registered_modules = register_validation_modules(["specs/capabilities/geometry/validation.py"])
        ...
    finally:
        if registered_modules is not None:
            unregister_validation_modules(registered_modules)
        unregister_content(content)

The loaded ``content`` object is the lifecycle token for documentation/specification
content. The ``registered_modules`` token owns imported rule modules, so reload and
shutdown code can unregister exactly what it previously loaded.
