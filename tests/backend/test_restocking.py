"""
Tests for restocking endpoints (recommendations and submitted orders).
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Submitted orders live in memory; reset them around every test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestRestockRecommendations:
    """Test suite for budget-based restock recommendations."""

    def test_zero_budget_recommends_nothing(self, client):
        """A zero budget yields no recommendations but still reports the full need."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["total_needed_cost"] > 0

    def test_recommendations_stay_within_budget(self, client):
        """Total cost never exceeds the budget and line totals add up."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        assert 0 < data["total_cost"] <= 10000
        assert round(data["total_cost"] + data["remaining_budget"], 2) == 10000
        line_sum = round(sum(r["line_total"] for r in data["recommendations"]), 2)
        assert line_sum == data["total_cost"]

        for rec in data["recommendations"]:
            assert 0 < rec["recommended_quantity"] <= rec["quantity_needed"]
            assert rec["line_total"] == round(rec["recommended_quantity"] * rec["unit_cost"], 2)

    def test_increasing_trend_comes_first(self, client):
        """Items with increasing demand are prioritised over stable and decreasing ones."""
        response = client.get("/api/restocking/recommendations?budget=1000000")
        trends = [r["trend"] for r in response.json()["recommendations"]]

        order = {"increasing": 0, "stable": 1, "decreasing": 2}
        assert trends == sorted(trends, key=order.get)

    def test_full_budget_covers_all_needs(self, client):
        """With a budget equal to the full need, every candidate is fully recommended."""
        need = client.get("/api/restocking/recommendations?budget=0").json()["total_needed_cost"]
        data = client.get(f"/api/restocking/recommendations?budget={need}").json()

        assert data["total_cost"] == need
        for rec in data["recommendations"]:
            assert rec["recommended_quantity"] == rec["quantity_needed"]

    def test_items_with_enough_stock_are_skipped(self, client):
        """PSU-501 has more stock on hand than its forecasted demand."""
        data = client.get("/api/restocking/recommendations?budget=1000000").json()
        skus = [r["item_sku"] for r in data["recommendations"]]
        assert "PSU-501" not in skus

    def test_budget_is_required_and_non_negative(self, client):
        """Missing or negative budget is rejected."""
        assert client.get("/api/restocking/recommendations").status_code == 422
        assert client.get("/api/restocking/recommendations?budget=-5").status_code == 422


class TestRestockOrders:
    """Test suite for submitting and listing restocking orders."""

    def test_no_orders_initially(self, client):
        """The list starts empty."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_place_order(self, client):
        """Submitting an order prices it server-side and sets lead time from the slowest item."""
        payload = {
            "budget": 10000,
            "items": [
                {"item_sku": "GSK-203", "quantity": 100},
                {"item_sku": "BRG-102", "quantity": 10},
            ],
        }
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert order["total_cost"] == round(100 * 3.75 + 10 * 45.0, 2)
        assert order["lead_time_days"] == 21
        assert order["expected_delivery"] > order["submitted_at"]

        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [order["id"]]

    def test_orders_listed_newest_first(self, client):
        """The most recent order comes first."""
        for qty in (1, 2):
            client.post("/api/restocking/orders", json={"budget": 1000, "items": [{"item_sku": "GSK-203", "quantity": qty}]})

        listed = client.get("/api/restocking/orders").json()
        assert [o["items"][0]["quantity"] for o in listed] == [2, 1]

    def test_order_over_budget_rejected(self, client):
        """An order costing more than its budget is refused."""
        payload = {"budget": 100, "items": [{"item_sku": "MTR-304", "quantity": 1}]}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    def test_unknown_sku_rejected(self, client):
        """SKUs not in the demand forecast cannot be ordered."""
        payload = {"budget": 1000, "items": [{"item_sku": "NOPE-000", "quantity": 1}]}
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_invalid_payload_rejected(self, client):
        """Empty item lists and non-positive quantities fail validation."""
        assert client.post("/api/restocking/orders", json={"budget": 100, "items": []}).status_code == 422
        bad_qty = {"budget": 100, "items": [{"item_sku": "GSK-203", "quantity": 0}]}
        assert client.post("/api/restocking/orders", json=bad_qty).status_code == 422
