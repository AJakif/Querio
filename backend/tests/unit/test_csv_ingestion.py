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


class TestColumnStats:
    def test_numeric_stats(self):
        content = b"value\n10\n20\n30\n40\n50"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.inferred_type == "integer"
        assert col.stats["null_percentage"] == 0.0
        assert col.stats["min_value"] == 10.0
        assert col.stats["max_value"] == 50.0
        assert col.stats["mean_value"] == 30.0
        assert col.stats["top_values"] is None

    def test_numeric_with_nulls(self):
        content = b"value,label\n10,a\n,b\n30,c\n,d\n50,e"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.stats["null_percentage"] == 40.0
        assert col.stats["min_value"] == 10.0
        assert col.stats["max_value"] == 50.0
        assert col.stats["mean_value"] == 30.0

    def test_numeric_no_nulls(self):
        content = b"value\n10\n20\n30"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.stats["null_percentage"] == 0.0
        assert col.stats["min_value"] == 10.0
        assert col.stats["max_value"] == 30.0
        assert col.stats["mean_value"] == 20.0

    def test_text_top_values(self):
        content = b"cat\napple\nbanana\napple\ncherry\nbanana\napple"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.inferred_type == "text"
        assert col.stats["null_percentage"] == 0.0
        assert col.stats["min_value"] is None
        assert col.stats["max_value"] is None
        assert col.stats["mean_value"] is None
        top = col.stats["top_values"]
        assert top is not None
        assert top[0]["value"] == "apple"
        assert top[0]["count"] == 3
        assert top[1]["value"] == "banana"
        assert top[1]["count"] == 2

    def test_text_with_nulls(self):
        content = b"name,val\napple,1\n,2\nbanana,3\n,4"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.inferred_type == "text"
        assert col.stats["null_percentage"] == 50.0

    def test_json_all_nulls_empty_top_values(self):
        content = json.dumps([{"a": None}, {"a": None}, {"a": None}]).encode()
        result = parse_json(content)
        col = result.columns[0]
        assert col.stats["null_percentage"] == 100.0
        assert col.stats["top_values"] == []

    def test_date_column_no_numeric_stats(self):
        content = b"dt\n2024-01-01\n2024-01-02\n2024-01-03"
        result = parse_csv(content)
        col = result.columns[0]
        assert col.inferred_type == "date"
        assert col.stats["min_value"] is None
        assert col.stats["max_value"] is None
        assert col.stats["mean_value"] is None
        top = col.stats["top_values"]
        assert top is not None
        assert len(top) == 3

    def test_top_values_max_five(self):
        values = "\n".join([f"val{i}" for i in range(10)] * 3)
        content = f"x\n{values}".encode()
        result = parse_csv(content)
        col = result.columns[0]
        assert len(col.stats["top_values"]) == 5

    def test_json_numeric_stats(self):
        content = json.dumps([{"a": 10}, {"a": 20}, {"a": 30}]).encode()
        result = parse_json(content)
        col = result.columns[0]
        assert col.stats["min_value"] == 10.0
        assert col.stats["max_value"] == 30.0
        assert col.stats["mean_value"] == 20.0

    def test_json_text_top_values(self):
        content = json.dumps([{"x": "a"}, {"x": "b"}, {"x": "a"}]).encode()
        result = parse_json(content)
        col = result.columns[0]
        top = col.stats["top_values"]
        assert top is not None
        assert top[0]["value"] == "a"
        assert top[0]["count"] == 2


class TestParseCsvNoFlattening:
    def test_csv_unchanged(self):
        content = b"a,b\n1,x\n2,y"
        result = parse_csv(content)
        assert result.total_rows == 2
        assert [c.name for c in result.columns] == ["a", "b"]
