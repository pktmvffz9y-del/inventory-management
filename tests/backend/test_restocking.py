"""
Tests for restocking recommendations and restocking order endpoints.
"""
import pytest
from datetime import datetime, timedelta


class TestRestockingRecommendations:
    def test_get_recommendations_returns_list(self, client):
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_recommendations_have_required_fields(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        assert len(data) > 0
        item = data[0]
        for field in ["item_sku", "item_name", "quantity_on_hand", "reorder_point",
                      "forecasted_demand", "quantity_to_order", "unit_cost", "total_cost",
                      "trend", "priority"]:
            assert field in item, f"Missing field: {field}"

    def test_recommendations_exclude_items_with_zero_quantity_to_order(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        # All returned items must have quantity_to_order > 0
        for item in data:
            assert item["quantity_to_order"] > 0, \
                f"Item {item['item_sku']} has quantity_to_order=0 but should be excluded"

    def test_recommendations_sorted_by_priority_descending(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        priorities = [item["priority"] for item in data]
        assert priorities == sorted(priorities, reverse=True), \
            "Recommendations should be sorted by priority descending"

    def test_total_cost_equals_quantity_times_unit_cost(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        for item in data:
            expected = round(item["quantity_to_order"] * item["unit_cost"], 2)
            assert abs(item["total_cost"] - expected) < 0.01, \
                f"total_cost mismatch for {item['item_sku']}: {item['total_cost']} != {expected}"

    def test_increasing_trend_items_have_higher_priority(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        increasing = [i for i in data if i["trend"] == "increasing"]
        non_increasing = [i for i in data if i["trend"] != "increasing"]
        if increasing and non_increasing:
            assert min(i["priority"] for i in increasing) >= max(i["priority"] for i in non_increasing), \
                "Increasing trend items should have higher priority than non-increasing"

    def test_priority_values_are_valid(self, client):
        response = client.get("/api/restocking/recommendations")
        data = response.json()
        for item in data:
            assert item["priority"] in (0, 1, 2, 3), \
                f"Priority {item['priority']} is outside expected range 0-3"


class TestCreateRestockingOrder:
    def test_create_order_returns_201(self, client):
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 100, "unit_price": 25.00}
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

    def test_created_order_has_correct_fields(self, client):
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 10, "unit_price": 50.00}
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("REST-")
        assert "order_date" in order
        assert "expected_delivery" in order
        assert "id" in order

    def test_expected_delivery_is_14_days_after_order_date(self, client):
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A",
                 "quantity": 5, "unit_price": 20.00}
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        order = response.json()
        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        delta = expected_delivery - order_date
        assert delta.days == 14, f"Expected 14-day lead time, got {delta.days} days"

    def test_total_value_is_sum_of_items(self, client):
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Widget A", "quantity": 10, "unit_price": 25.00},
                {"sku": "GSK-203", "name": "Gasket B", "quantity": 20, "unit_price": 15.00},
            ]
        }
        response = client.post("/api/restocking-orders", json=payload)
        order = response.json()
        expected_total = round(10 * 25.00 + 20 * 15.00, 2)
        assert abs(order["total_value"] - expected_total) < 0.01

    def test_submitted_order_appears_in_get_restocking_orders(self, client):
        payload = {
            "items": [
                {"sku": "SNR-420", "name": "Temperature Sensor",
                 "quantity": 50, "unit_price": 89.50}
            ]
        }
        post_response = client.post("/api/restocking-orders", json=payload)
        created_id = post_response.json()["id"]

        get_response = client.get("/api/restocking-orders")
        ids = [o["id"] for o in get_response.json()]
        assert created_id in ids, "Created order should appear in GET /api/restocking-orders"


class TestGetRestockingOrders:
    def test_get_restocking_orders_returns_list(self, client):
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_restocking_orders_have_required_fields(self, client):
        # Create one first so the list is non-empty
        client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "name": "Widget", "quantity": 1, "unit_price": 10.0}]
        })
        response = client.get("/api/restocking-orders")
        data = response.json()
        assert len(data) > 0
        order = data[0]
        for field in ["id", "order_number", "status", "order_date",
                      "expected_delivery", "total_value", "items"]:
            assert field in order, f"Missing field: {field}"
