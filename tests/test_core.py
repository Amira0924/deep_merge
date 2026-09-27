import unittest
from collections import OrderedDict

from deep_merge import merge, deep_merge, MergeConfig


class TestHappyPath(unittest.TestCase):
    def test_flat_disjoint_keys(self):
        result = merge({"a": 1}, {"b": 2})
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_flat_source_overrides_destination(self):
        result = merge({"a": 1}, {"a": 2})
        self.assertEqual(result, {"a": 2})

    def test_nested_dicts_merge(self):
        result = merge({"outer": {"a": 1, "b": 2}}, {"outer": {"b": 3, "c": 4}})
        self.assertEqual(result, {"outer": {"a": 1, "b": 3, "c": 4}})

    def test_deeply_nested(self):
        result = merge(
            {"l1": {"l2": {"l3": {"a": 1}}}},
            {"l1": {"l2": {"l3": {"b": 2}}}},
        )
        self.assertEqual(result, {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}})


class TestDestinationNotMutated(unittest.TestCase):
    def test_destination_unchanged(self):
        dest = {"a": {"b": 1}}
        merge(dest, {"a": {"c": 2}})
        self.assertEqual(dest, {"a": {"b": 1}})

    def test_result_independent_of_destination(self):
        dest = {"a": {"b": 1}}
        result = merge(dest, {"a": {"c": 2}})
        result["a"]["b"] = 999
        self.assertEqual(dest["a"]["b"], 1)


class TestListsAreScalars(unittest.TestCase):
    def test_list_replaces_list(self):
        result = merge({"items": [1, 2, 3]}, {"items": [4, 5]})
        self.assertEqual(result, {"items": [4, 5]})

    def test_list_replaces_dict(self):
        result = merge({"items": {"a": 1}}, {"items": [1, 2]})
        self.assertEqual(result, {"items": [1, 2]})

    def test_dict_replaces_list(self):
        result = merge({"items": [1, 2]}, {"items": {"a": 1}})
        self.assertEqual(result, {"items": {"a": 1}})


class TestNullSemantics(unittest.TestCase):
    def test_none_deletes_existing_key(self):
        result = merge({"a": 1, "b": 2}, {"a": None})
        self.assertEqual(result, {"b": 2})

    def test_none_deletes_nested_key(self):
        result = merge({"a": {"b": 1, "c": 2}}, {"a": {"b": None}})
        self.assertEqual(result, {"a": {"c": 2}})

    def test_none_on_absent_key_is_noop(self):
        result = merge({"a": 1}, {"b": None})
        self.assertEqual(result, {"a": 1})

    def test_none_deletes_even_when_destination_is_dict(self):
        result = merge({"a": {"b": 1}}, {"a": None})
        self.assertEqual(result, {})

    def test_null_deletes_false_overwrites_with_none(self):
        config = MergeConfig(null_deletes=False)
        result = merge({"a": 1}, {"a": None}, config=config)
        self.assertEqual(result, {"a": None})

    def test_null_deletes_false_inserts_none(self):
        config = MergeConfig(null_deletes=False)
        result = merge({}, {"a": None}, config=config)
        self.assertEqual(result, {"a": None})


class TestNonDictMappings(unittest.TestCase):
    def test_ordered_dict_inputs(self):
        dest = OrderedDict([("a", 1), ("b", OrderedDict([("c", 2)]))])
        src = OrderedDict([("b", OrderedDict([("d", 3)]))])
        result = merge(dest, src)
        self.assertEqual(result, {"a": 1, "b": {"c": 2, "d": 3}})
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["b"], dict)

    def test_output_is_always_plain_dict(self):
        result = merge(OrderedDict([("a", 1)]), OrderedDict([("b", 2)]))
        self.assertIs(type(result), dict)


class TestTypeErrors(unittest.TestCase):
    def test_non_mapping_destination(self):
        with self.assertRaises(TypeError):
            merge([1, 2], {"a": 1})

    def test_non_mapping_source(self):
        with self.assertRaises(TypeError):
            merge({"a": 1}, [1, 2])


class TestAlias(unittest.TestCase):
    def test_deep_merge_is_merge(self):
        dest = {"a": {"b": 1}}
        src = {"a": {"c": 2}}
        self.assertEqual(deep_merge(dest, src), merge(dest, src))


class TestConfigReplace(unittest.TestCase):
    def test_replace_returns_independent_config(self):
        base = MergeConfig()
        derived = base.replace(null_deletes=False)
        self.assertFalse(derived.null_deletes)
        self.assertTrue(base.null_deletes)
        self.assertIsNot(base, derived)


class TestEmptyInputs(unittest.TestCase):
    def test_empty_source(self):
        self.assertEqual(merge({"a": 1}, {}), {"a": 1})

    def test_empty_destination(self):
        self.assertEqual(merge({}, {"a": 1}), {"a": 1})

    def test_both_empty(self):
        self.assertEqual(merge({}, {}), {})


class TestSharedReferenceSemantics(unittest.TestCase):
    def test_list_value_is_shared_reference(self):
        src_list = [1, 2, 3]
        result = merge({}, {"items": src_list})
        self.assertIs(result["items"], src_list)

    def test_nested_dict_result_is_not_shared_with_destination(self):
        dest = {"a": {"b": 1}}
        result = merge(dest, {"a": {"c": 2}})
        self.assertIsNot(result["a"], dest["a"])


class TestConfigEqualityAndRepr(unittest.TestCase):
    def test_config_equality(self):
        self.assertEqual(MergeConfig(), MergeConfig())
        self.assertNotEqual(MergeConfig(null_deletes=True), MergeConfig(null_deletes=False))

    def test_config_repr(self):
        self.assertEqual(repr(MergeConfig()), "MergeConfig(null_deletes=True)")


if __name__ == "__main__":
    unittest.main()
