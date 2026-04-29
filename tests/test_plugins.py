# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
Tests for the plugin management system.
"""

import unittest
from unittest.mock import Mock, patch

from nvidia_usd_validation import (
    BaseRuleChecker,
    CategoryRuleRegistry,
    PluginManager,
    PluginProtocol,
    register_rule,
)
from nvidia_usd_validation._default_plugin import DefaultPlugin

DEFAULT_PLUGIN_ENTRYPOINT = "nvidia_usd_validation:DefaultPlugin"


def _make_ep(name, value, dist_name, plugin_instance):
    """Create a mock entrypoint that behaves like importlib.metadata.EntryPoint."""
    ep = Mock()
    ep.name = name
    ep.value = value
    ep.dist = Mock()
    ep.dist.name = dist_name
    ep.load = Mock(return_value=plugin_instance)
    return ep


def _mock_entry_points(eps):
    """Patch importlib.metadata.entry_points to return the given entrypoints."""
    mock_eps = Mock()
    mock_eps.select = Mock(return_value=eps)
    return patch("importlib.metadata.entry_points", return_value=mock_eps)


def _mock_no_deps():
    """Patch importlib.metadata.requires to return no dependencies."""
    return patch("importlib.metadata.requires", return_value=None)


class MockPluginWithRule:
    """Mock plugin that registers a validation rule."""

    def __init__(self):
        self.rule_registered = False

    def on_startup(self) -> None:
        @register_rule("TestPluginCategory")
        class TestPluginRule(BaseRuleChecker):
            pass

        self.test_rule_class = TestPluginRule
        self.rule_registered = True

    def on_shutdown(self) -> None:
        if hasattr(self, "test_rule_class"):
            CategoryRuleRegistry().remove(self.test_rule_class)


class IncompletePlugin:
    """Plugin missing required methods."""

    def on_startup(self) -> None:
        pass

    # Missing on_shutdown()


class TestPluginManager(unittest.TestCase):
    """
    Tests for the PluginManager class.

    Tests use public APIs (initialize/shutdown/loaded_plugins) and mock at the
    importlib.metadata boundary to simulate real plugin discovery.
    """

    def setUp(self):
        PluginManager().shutdown()

    def tearDown(self):
        PluginManager().shutdown()

    # -- Singleton --

    def test_singleton_behavior(self):
        """PluginManager() always returns the same instance."""
        manager1 = PluginManager()
        manager2 = PluginManager()
        self.assertIs(manager1, manager2)
        self.assertTrue(hasattr(manager1, "initialize"))
        self.assertTrue(hasattr(manager1, "shutdown"))
        self.assertTrue(hasattr(manager1, "loaded_plugins"))

    # -- Protocol --

    def test_protocol_compliance_valid(self):
        """Valid plugins pass runtime protocol check."""
        self.assertIsInstance(Mock(spec=PluginProtocol), PluginProtocol)

    def test_protocol_compliance_missing_on_startup(self):
        """Objects missing on_startup fail protocol check."""

        class NoStartup:
            def on_shutdown(self) -> None:
                pass

        self.assertNotIsInstance(NoStartup(), PluginProtocol)

    def test_protocol_compliance_missing_on_shutdown(self):
        """Objects missing on_shutdown fail protocol check."""

        class NoShutdown:
            def on_startup(self) -> None:
                pass

        self.assertNotIsInstance(NoShutdown(), PluginProtocol)

    # -- Initialize / loaded_plugins --

    def test_initialize_default_plugin(self):
        """Default plugin loads via fallback when not discovered via entrypoints."""
        with _mock_entry_points([]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()
            self.assertEqual(len(manager.loaded_plugins), 1)
            self.assertEqual(manager.loaded_plugins[0].name, "default")

    def test_initialize_loads_plugin(self):
        """initialize() discovers, loads, and starts a plugin."""
        plugin = Mock(spec=PluginProtocol)
        ep = _make_ep("my_plugin", "my_pkg:plugin", "my-package", plugin)

        with _mock_entry_points([ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            loaded = manager.get_loaded_plugin("my_pkg:plugin")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.distribution_name, "my-package")
            plugin.on_startup.assert_called_once()

    def test_initialize_loads_plugin_class(self):
        """initialize() instantiates and starts a plugin class."""
        started = Mock()

        class PluginClass:
            def on_startup(self) -> None:
                started()

            def on_shutdown(self) -> None: ...

        ep = _make_ep("cls_plugin", "my_pkg:PluginClass", "my-package", PluginClass)
        with _mock_entry_points([ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            self.assertTrue(manager.is_plugin_loaded("my_pkg:PluginClass"))
            started.assert_called_once()

    def test_initialize_idempotent(self):
        """Calling initialize() twice only discovers plugins once."""
        plugin = Mock(spec=PluginProtocol)
        ep = _make_ep("p1", "mod1:P", "pkg1", plugin)

        with _mock_entry_points([ep]) as mock_ep, _mock_no_deps():
            manager = PluginManager()
            manager.initialize()
            manager.initialize()
            self.assertEqual(mock_ep.return_value.select.call_count, 1)

    def test_initialize_skips_broken_plugin(self):
        """Plugins that raise during startup are skipped."""
        broken_plugin = Mock(spec=PluginProtocol)
        broken_plugin.on_startup.side_effect = RuntimeError("Plugin startup failed")
        broken_ep = _make_ep("broken", "broken_pkg:plugin", "broken-pkg", broken_plugin)
        good_plugin = Mock(spec=PluginProtocol)
        good_ep = _make_ep("good", "good_pkg:plugin", "good-pkg", good_plugin)

        with _mock_entry_points([broken_ep, good_ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            self.assertTrue(manager.is_plugin_loaded("good_pkg:plugin"))
            self.assertFalse(manager.is_plugin_loaded("broken_pkg:plugin"))
            good_plugin.on_startup.assert_called_once()

    def test_initialize_skips_import_error(self):
        """Plugins that fail to import are skipped."""
        bad_ep = Mock()
        bad_ep.name = "bad"
        bad_ep.value = "bad_pkg:plugin"
        bad_ep.dist = Mock()
        bad_ep.dist.name = "bad-pkg"
        bad_ep.load = Mock(side_effect=ImportError("Module not found"))

        good_plugin = Mock(spec=PluginProtocol)
        good_ep = _make_ep("good", "good_pkg:plugin", "good-pkg", good_plugin)

        with _mock_entry_points([bad_ep, good_ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            self.assertTrue(manager.is_plugin_loaded("good_pkg:plugin"))
            self.assertFalse(manager.is_plugin_loaded("bad_pkg:plugin"))

    def test_initialize_skips_incomplete_plugin(self):
        """Plugins missing on_shutdown() are skipped."""
        ep = _make_ep("incomplete", "inc_pkg:plugin", "inc-pkg", IncompletePlugin())

        with _mock_entry_points([ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            self.assertFalse(manager.is_plugin_loaded("inc_pkg:plugin"))

    def test_initialize_skips_missing_on_startup(self):
        """Plugins missing on_startup() are skipped."""

        class NoStartupPlugin:
            def on_shutdown(self) -> None:
                pass

        ep = _make_ep("no_startup", "ns_pkg:plugin", "ns-pkg", NoStartupPlugin())

        with _mock_entry_points([ep]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()

            self.assertFalse(manager.is_plugin_loaded("ns_pkg:plugin"))

    def test_initialize_discovery_error(self):
        """If entry_points() raises, initialize() succeeds with no plugins."""
        with patch("importlib.metadata.entry_points", side_effect=ImportError("fail")):
            manager = PluginManager()
            manager.initialize()
            self.assertEqual(len(manager.loaded_plugins), 0)

    # -- omni namespace patch --

    @unittest.skip("Omniverse-specific behavior: does not apply to standalone package")
    def test_omni_namespace_patched_before_on_startup(self):
        """nvidia_usd_validation is set on the omni namespace before on_startup() runs."""
        
        observed = []

        class OmniAccessPlugin:
            def on_startup(self) -> None:
                try:
                    _ = nvidia_usd_validation
                    observed.append(True)
                except AttributeError:
                    observed.append(False)

            def on_shutdown(self) -> None:
                pass

        ep = _make_ep("p1", "mod1:P", "pkg1", OmniAccessPlugin())

        # Simulate the partial-init state where nvidia_usd_validation is not yet
        # set as an attribute on the omni namespace package.
        original = getattr(omni, "asset_validator", None)
        try:
            if hasattr(omni, "asset_validator"):
                delattr(omni, "asset_validator")
            with _mock_entry_points([ep]), _mock_no_deps():
                manager = PluginManager()
                manager.initialize()
        finally:
            if original is not None:
                nvidia_usd_validation = original

        self.assertEqual(observed, [True])

    # -- Topological sort (via initialize) --

    def test_dependency_order(self):
        """Plugins are loaded after their dependencies."""
        p1 = Mock(spec=PluginProtocol)
        p2 = Mock(spec=PluginProtocol)
        ep1 = _make_ep("base", "base_mod:P", "base-pkg", p1)
        ep2 = _make_ep("child", "child_mod:P", "child-pkg", p2)

        def mock_requires(dist_name):
            if dist_name == "child-pkg":
                return ["base-pkg>=1.0"]
            return None

        with _mock_entry_points([ep2, ep1]):  # Out of order
            with patch("importlib.metadata.requires", side_effect=mock_requires):
                manager = PluginManager()
                manager.initialize()

                self.assertTrue(manager.is_plugin_loaded("base_mod:P"))
                self.assertTrue(manager.is_plugin_loaded("child_mod:P"))
                names = [p.name for p in manager.loaded_plugins]
                self.assertLess(names.index("base"), names.index("child"))

    def test_diamond_dependency_order(self):
        """Diamond dependency pattern loads in correct order: A -> B,C -> D."""
        plugins = {name: Mock(spec=PluginProtocol) for name in ["a", "b", "c", "d"]}
        ep_a = _make_ep("a", "a_mod:P", "pkg-a", plugins["a"])
        ep_b = _make_ep("b", "b_mod:P", "pkg-b", plugins["b"])
        ep_c = _make_ep("c", "c_mod:P", "pkg-c", plugins["c"])
        ep_d = _make_ep("d", "d_mod:P", "pkg-d", plugins["d"])

        def mock_requires(dist_name):
            deps = {
                "pkg-b": ["pkg-a>=1.0"],
                "pkg-c": ["pkg-a>=1.0"],
                "pkg-d": ["pkg-b>=1.0", "pkg-c>=1.0"],
            }
            return deps.get(dist_name)

        with _mock_entry_points([ep_d, ep_b, ep_c, ep_a]):  # Scrambled
            with patch("importlib.metadata.requires", side_effect=mock_requires):
                manager = PluginManager()
                manager.initialize()

                for ep_val in ("a_mod:P", "b_mod:P", "c_mod:P", "d_mod:P"):
                    self.assertTrue(manager.is_plugin_loaded(ep_val))
                indices = {p.name: i for i, p in enumerate(manager.loaded_plugins)}

                self.assertLess(indices["a"], indices["b"])
                self.assertLess(indices["a"], indices["c"])
                self.assertLess(indices["b"], indices["d"])
                self.assertLess(indices["c"], indices["d"])

    def test_circular_dependency_logs_warning(self):
        """Circular dependencies are handled gracefully with a warning."""
        p1 = Mock(spec=PluginProtocol)
        p2 = Mock(spec=PluginProtocol)
        ep1 = _make_ep("p1", "mod1:P", "pkg1", p1)
        ep2 = _make_ep("p2", "mod2:P", "pkg2", p2)

        def mock_requires(dist_name):
            # Circular: pkg1 -> pkg2 -> pkg1
            return {"pkg1": ["pkg2>=1.0"], "pkg2": ["pkg1>=1.0"]}.get(dist_name)

        with _mock_entry_points([ep1, ep2]):
            with patch("importlib.metadata.requires", side_effect=mock_requires):
                with self.assertLogs("nvidia_usd_validation._plugins", level="WARNING") as log:
                    manager = PluginManager()
                    manager.initialize()

                    self.assertTrue(manager.is_plugin_loaded("mod1:P"))
                    self.assertTrue(manager.is_plugin_loaded("mod2:P"))
                    self.assertTrue(any("Circular dependency" in m for m in log.output))

    # -- Shutdown --

    def test_shutdown_calls_on_shutdown(self):
        """shutdown() calls on_shutdown for all loaded plugins."""
        p1 = Mock(spec=PluginProtocol)
        p2 = Mock(spec=PluginProtocol)
        ep1 = _make_ep("p1", "mod1:P", "pkg1", p1)
        ep2 = _make_ep("p2", "mod2:P", "pkg2", p2)

        with _mock_entry_points([ep1, ep2]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()
            manager.shutdown()

            p1.on_shutdown.assert_called_once()
            p2.on_shutdown.assert_called_once()
            self.assertEqual(len(manager.loaded_plugins), 0)

    def test_shutdown_error_does_not_prevent_others(self):
        """One plugin's shutdown error doesn't prevent others from shutting down."""
        error_plugin = Mock(spec=PluginProtocol)
        error_plugin.on_shutdown.side_effect = RuntimeError("Shutdown error")
        good_plugin = Mock(spec=PluginProtocol)
        ep1 = _make_ep("error", "err_mod:P", "err-pkg", error_plugin)
        ep2 = _make_ep("good", "good_mod:P", "good-pkg", good_plugin)

        with _mock_entry_points([ep1, ep2]), _mock_no_deps():
            manager = PluginManager()
            manager.initialize()
            manager.shutdown()

            error_plugin.on_shutdown.assert_called_once()
            good_plugin.on_shutdown.assert_called_once()

    def test_loaded_plugins_immutable(self):
        """loaded_plugins returns a tuple."""
        manager = PluginManager()
        self.assertIsInstance(manager.loaded_plugins, tuple)

    # -- Context manager --

    def test_context_initializes_and_shuts_down(self):
        """Context initializes on entry and shuts down on exit."""
        plugin = Mock(spec=PluginProtocol)
        ep = _make_ep("p1", "mod1:P", "pkg1", plugin)

        with _mock_entry_points([ep]), _mock_no_deps():
            with PluginManager() as manager:
                self.assertTrue(manager.is_plugin_loaded("mod1:P"))
                plugin.on_startup.assert_called_once()

            plugin.on_shutdown.assert_called_once()
            self.assertEqual(len(manager.loaded_plugins), 0)

    def test_context_shuts_down_on_exception(self):
        """Context calls shutdown even if body raises."""
        plugin = Mock(spec=PluginProtocol)
        ep = _make_ep("p1", "mod1:P", "pkg1", plugin)

        with _mock_entry_points([ep]), _mock_no_deps():
            with self.assertRaises(ValueError):
                with PluginManager():
                    raise ValueError("test error")

            plugin.on_shutdown.assert_called_once()

    # -- Query APIs --

    def test_is_plugin_loaded(self):
        """is_plugin_loaded() returns True after initialize, False after shutdown."""
        plugin = Mock(spec=PluginProtocol)
        ep = _make_ep("p1", "mod1:P", "pkg1", plugin)

        with _mock_entry_points([ep]), _mock_no_deps():
            manager = PluginManager()
            self.assertFalse(manager.is_plugin_loaded("mod1:P"))

            manager.initialize()
            self.assertTrue(manager.is_plugin_loaded("mod1:P"))

    def test_is_plugin_loaded_not_loaded(self):
        """is_plugin_loaded() returns False for unknown plugin."""
        manager = PluginManager()
        self.assertFalse(manager.is_plugin_loaded("nonexistent:X"))


class TestDefaultPlugin(unittest.TestCase):
    """Tests for the DefaultPlugin."""

    def setUp(self):
        PluginManager().shutdown()

    def tearDown(self):
        PluginManager().shutdown()

    def test_default_plugin_conforms_to_protocol(self):
        """DefaultPlugin conforms to the PluginProtocol."""
        self.assertIsInstance(DefaultPlugin(), PluginProtocol)

    def test_default_plugin_registers_rules(self):
        """DefaultPlugin.on_startup() registers built-in validation rules."""
        plugin = DefaultPlugin()
        plugin.on_startup()

        registry = CategoryRuleRegistry()
        expected_categories = {
            "Basic",
            "Geometry",
            "Material",
            "Layer",
            "Layout",
            "Physics",
            "Other",
        }
        registered_categories = set(registry.categories)
        self.assertTrue(
            expected_categories.issubset(registered_categories),
            f"Missing categories: {expected_categories - registered_categories}",
        )

        # Verify a sampling of rules are registered
        self.assertIsNotNone(registry.find_rule("MissingReferenceChecker"))
        self.assertIsNotNone(registry.find_rule("ManifoldChecker"))
        self.assertIsNotNone(registry.find_rule("MaterialPathChecker"))
        self.assertIsNotNone(registry.find_rule("RigidBodyChecker"))

        plugin.on_shutdown()

    def test_default_plugin_entrypoint_value(self):
        """DEFAULT_PLUGIN_ENTRYPOINT matches the expected format."""
        self.assertEqual(DEFAULT_PLUGIN_ENTRYPOINT, "nvidia_usd_validation:DefaultPlugin")

    def test_default_plugin_shutdown_unregisters_rules(self):
        """on_shutdown() removes all rules registered by on_startup()."""
        plugin = DefaultPlugin()
        plugin.on_startup()

        registry = CategoryRuleRegistry()
        self.assertIsNotNone(registry.find_rule("MissingReferenceChecker"))

        plugin.on_shutdown()

        self.assertIsNone(registry.find_rule("MissingReferenceChecker"))
        self.assertIsNone(registry.find_rule("ManifoldChecker"))
        self.assertIsNone(registry.find_rule("MaterialPathChecker"))
        self.assertIsNone(registry.find_rule("RigidBodyChecker"))

    def test_default_plugin_shutdown_idempotent(self):
        """Calling on_shutdown() twice does not raise."""
        plugin = DefaultPlugin()
        plugin.on_startup()
        plugin.on_shutdown()
        plugin.on_shutdown()  # Should not raise

    def test_default_plugin_startup_shutdown_roundtrip(self):
        """on_startup() -> on_shutdown() -> on_startup() re-registers rules."""
        plugin = DefaultPlugin()
        registry = CategoryRuleRegistry()

        plugin.on_startup()
        self.assertIsNotNone(registry.find_rule("MissingReferenceChecker"))

        plugin.on_shutdown()
        self.assertIsNone(registry.find_rule("MissingReferenceChecker"))

        plugin.on_startup()
        self.assertIsNotNone(registry.find_rule("MissingReferenceChecker"))

        plugin.on_shutdown()


class TestPluginIntegration(unittest.TestCase):
    """Integration tests for plugin system."""

    def setUp(self):
        PluginManager().shutdown()

    def tearDown(self):
        PluginManager().shutdown()

    def test_plugin_registers_rule(self):
        """A plugin can register a validation rule via on_startup."""
        plugin_instance = MockPluginWithRule()
        plugin_instance.on_startup()

        self.assertTrue(plugin_instance.rule_registered)
        self.assertIn("TestPluginCategory", CategoryRuleRegistry().categories)
        self.assertIn(plugin_instance.test_rule_class, CategoryRuleRegistry().get_rules("TestPluginCategory"))

        plugin_instance.on_shutdown()

    def test_dependency_parsing(self):
        """Package dependencies are correctly extracted from requires() output."""
        mock_reqs = ["package-one>=1.0", "package-two[extra]", "package-three>=2.0;python_version>='3.8'"]

        with patch("importlib.metadata.requires", return_value=mock_reqs):
            manager = PluginManager()
            deps = manager._get_package_dependencies("test-package")

            self.assertEqual(deps, {"package-one", "package-two", "package-three"})

    def test_dependency_parsing_not_found(self):
        """Non-existent packages return empty dependencies."""
        from importlib.metadata import PackageNotFoundError

        with patch("importlib.metadata.requires", side_effect=PackageNotFoundError("not found")):
            manager = PluginManager()
            deps = manager._get_package_dependencies("nonexistent")

            self.assertEqual(deps, set())

    def test_dependency_parsing_no_deps(self):
        """Packages with no dependencies return empty set."""
        with patch("importlib.metadata.requires", return_value=None):
            manager = PluginManager()
            deps = manager._get_package_dependencies("standalone")

            self.assertEqual(deps, set())
