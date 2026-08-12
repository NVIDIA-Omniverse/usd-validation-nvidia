# Testing

USD Validation NVIDIA comes with two classes to help you test your rules.

- ValidationTestCaseMixin: A mixin for test cases to simplify testing of individual Validation Rules.
- AsyncioValidationTestCaseMixin: A mixin for asyncio test cases to simplify testing of individual Validation Rules.

## ValidationTestCaseMixin

You could mix `ValidationTestCaseMixin` with `TestCase` as follows:

```python
from unittest import TestCase

from usd_validation_nvidia.tests import ValidationTestCaseMixin


class ValidationTestCase(TestCase, ValidationTestCaseMixin): ...
```

An example to implement a test case would look like:

```python
class RuleTest(ValidationTestCase):

    def test_rule(self):
        self.assertSuccess(
            asset=get_url("pass.usda"),
            rule=MyRule,
        )
        self.assertFailure(
            asset=get_url("fail.usda"),
            rule=MyRule,
        )
```

## AsyncioValidationTestCaseMixin

You could mix `AsyncioValidationTestCaseMixin` with `IsolatedAsyncioTestCase` as follows:

```python
from unittest import IsolatedAsyncioTestCase

from usd_validation_nvidia.tests import AsyncioValidationTestCaseMixin


class AsyncioValidationTestCase(IsolatedAsyncioTestCase, AsyncioValidationTestCaseMixin): ...
```

An example to implement a test case would look like:

```python
class RuleTest(AsyncioValidationTestCase):

    async def test_rule(self):
        await self.assertSuccessAsync(
            asset=get_url("pass.usda"),
            rule=MyRule,
        )
        await self.assertFailureAsync(
            asset=get_url("fail.usda"),
            rule=MyRule,
        )
```

## Assertions

Additionally you could verify for specific issues, for example:

```python
class RuleTest(AsyncioValidationTestCase):

    async def test_rule(self):
        await self.assertRuleAsync(
            asset=get_url("fail.usda"),
            rule=MyRule,
            asserts=[
                IsAFailure("Invalid condition"),
            ],
        )
```

`IsAFailure` can match to multiple attributes, like message, rule, requirement, location, etc.

## Fixes

```python
class RuleTest(AsyncioValidationTestCase):

    async def test_rule(self):
        await self.assertSuggestionAsync(
            asset=get_url("fail.usda"),
            rule=MyRule,
        )
```
