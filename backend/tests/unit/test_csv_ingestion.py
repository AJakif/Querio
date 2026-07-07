import json
import pytest

from app.services.csv_ingestion import parse_json, parse_csv, _flatten_item


class TestFlattenItem:
    def test_flat_object(self):
        item = {"order_id": 1, "amount": 50.0}
        assert _flatten_item(item) == {"order_id": 1, "amount": 50.0}

    def test_one_level_nesting(self):
        item = {"order_id": 1, "customer": {"name": "Alice", "age": 30}}
        result = _flatten_item(item)
        assert result == {"order_id": 1, "customer_name": "Alice", "customer_age": 30}

    def test_multiple_nested_keys(self):
        item = {
            "id": 1,
            "billing": {"street": "123 Main", "city": "NYC"},
            "shipping": {"street": "456 Oak", "city": "LA"},
        }
        result = _flatten_item(item)
        assert result == {
            "id": 1,
            "billing_street": "123 Main",
            "billing_city": "NYC",
            "shipping_street": "456 Oak",
            "shipping_city": "LA",
        }

    def test_deep_nesting_raises(self):
        item = {"order": {"customer": {"name": "Alice"}}}
        with pytest.raises(ValueError) as exc:
            _flatten_item(item)
        msg = str(exc.value)
        assert "more than one level deep" in msg
        assert "order.customer" in msg

    def test_deep_nesting_three_levels(self):
        item = {"a": {"b": {"c": {"d": 1}}}}
        with pytest.raises(ValueError) as exc:
            _flatten_item(item)
        msg = str(exc.value)
        assert "more than one level deep" in msg
        assert "a.b" in msg

    def test_mixed_flat_and_nested(self):
        item = {"flat_col": "x", "obj": {"inner": 42}}
        result = _flatten_item(item)
        assert result == {"flat_col": "x", "obj_inner": 42}

    def test_empty_nested_dict(self):
        item = {"id": 1, "meta": {}}
        result = _flatten_item(item)
        assert result == {"id": 1}

    def test_none_value_in_nested(self):
        item = {"customer": {"name": None}}
        result = _flatten_item(item)
        assert result == {"customer_name": None}

    def test_list_value_not_flattened(self):
        item = {"id": 1, "items": [{"x": 1}, {"x": 2}]}
        result = _flatten_item(item)
        assert result == {"id": 1, "items": [{"x": 1}, {"x": 2}]}


class TestParseJsonFlattening:
    def test_flat_array_no_nesting(self):
        content = json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]).encode()
        result = parse_json(content)
        assert result.total_rows == 2
        assert [c.name for c in result.columns] == ["a", "b"]

    def test_one_level_nesting_flattened(self):
        content = json.dumps([
            {"id": 1, "customer": {"name": "Alice", "age": 30}},
            {"id": 2, "customer": {"name": "Bob", "age": 25}},
        ]).encode()
        result = parse_json(content)
        col_names = [c.name for c in result.columns]
        assert "customer_name" in col_names
        assert "customer_age" in col_names
        assert "id" in col_names
        assert "customer" not in col_names
        assert result.total_rows == 2
        assert result.all_rows[0]["customer_name"] == "Alice"
        assert result.all_rows[0]["customer_age"] == 30

    def test_inconsistent_nesting_across_rows(self):
        content = json.dumps([
            {"id": 1, "customer": {"name": "Alice"}},
            {"id": 2, "customer": {"name": "Bob", "age": 30}},
        ]).encode()
        result = parse_json(content)
        col_names = [c.name for c in result.columns]
        assert "customer_name" in col_names
        assert "customer_age" in col_names
        assert result.all_rows[1]["customer_age"] == 30
        assert result.all_rows[0]["customer_age"] is None

    def test_deep_nesting_rejected(self):
        content = json.dumps([
            {"id": 1, "order": {"customer": {"name": "Alice"}}}
        ]).encode()
        with pytest.raises(ValueError) as exc:
            parse_json(content)
        msg = str(exc.value)
        assert "more than one level deep" in msg

    def test_deep_nesting_three_levels_rejected(self):
        content = json.dumps([
            {"a": {"b": {"c": 1}}}
        ]).encode()
        with pytest.raises(ValueError) as exc:
            parse_json(content)
        msg = str(exc.value)
        assert "more than one level deep" in msg
        assert "a.b" in msg

    def test_flattened_values_maintain_type_for_inference(self):
        content = json.dumps([
            {"id": 1, "customer": {"age": 30, "score": 99.5}},
            {"id": 2, "customer": {"age": 25, "score": 87.0}},
        ]).encode()
        result = parse_json(content)
        col_map = {c.name: c for c in result.columns}
        assert col_map["id"].inferred_type == "integer"
        assert col_map["customer_age"].inferred_type == "integer"
        assert col_map["customer_score"].inferred_type == "numeric"

    def test_flattened_nulls_handled(self):
        content = json.dumps([
            {"id": 1, "customer": {"name": "Alice"}},
            {"id": 2, "customer": {"name": "Bob"}},
        ]).encode()
        result = parse_json(content)
        col_names = [c.name for c in result.columns]
        assert "customer_name" in col_names
        assert result.all_rows[1]["customer_name"] == "Bob"
        assert result.total_rows == 2

    def test_inconsistent_nesting_with_null(self):
        content = json.dumps([
            {"id": 1, "customer": {"name": "Alice"}},
            {"id": 2, "customer": None},
        ]).encode()
        result = parse_json(content)
        col_names = [c.name for c in result.columns]
        assert "customer_name" in col_names
        assert "customer" in col_names
        assert result.all_rows[0]["customer_name"] == "Alice"
        assert result.all_rows[0]["customer"] is None
        assert result.all_rows[1]["customer_name"] is None
        assert result.all_rows[1]["customer"] is None

    def test_nested_array_value_preserved(self):
        content = json.dumps([
            {"id": 1, "tags": ["a", "b"], "meta": {"source": "web"}}
        ]).encode()
        result = parse_json(content)
        col_names = [c.name for c in result.columns]
        assert "tags" in col_names
        assert "meta_source" in col_names
        assert "meta" not in col_names


class TestParseJsonNoFlattening:
    def test_flat_json_no_change(self):
        content = json.dumps([{"a": 1, "b": "hello"}]).encode()
        result = parse_json(content)
        assert result.total_rows == 1
        assert [c.name for c in result.columns] == ["a", "b"]


class TestParseCsvNoFlattening:
    def test_csv_unchanged(self):
        content = b"a,b\n1,x\n2,y"
        result = parse_csv(content)
        assert result.total_rows == 2
        assert [c.name for c in result.columns] == ["a", "b"]
