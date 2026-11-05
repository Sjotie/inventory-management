"""
Tests for report API endpoints.
"""
import pytest


def _orders(client, **params):
    return client.get("/api/orders", params=params).json()


class TestQuarterlyReports:
    def test_shape(self, client):
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200
        data = response.json()
        assert [q["quarter"] for q in data] == ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]
        for q in data:
            for field in ["total_orders", "total_revenue", "delivered_orders", "avg_order_value", "fulfillment_rate"]:
                assert field in q
            assert 0 <= q["fulfillment_rate"] <= 100

    def test_totals_match_orders(self, client):
        data = client.get("/api/reports/quarterly").json()
        all_orders = _orders(client)
        assert sum(q["total_orders"] for q in data) == len(all_orders)
        assert sum(q["total_revenue"] for q in data) == pytest.approx(sum(o["total_value"] for o in all_orders), rel=1e-6)

    def test_avg_order_value(self, client):
        for q in client.get("/api/reports/quarterly").json():
            assert q["avg_order_value"] == pytest.approx(q["total_revenue"] / q["total_orders"], abs=0.01)

    def test_quarter_filter(self, client):
        data = client.get("/api/reports/quarterly", params={"month": "Q2-2025"}).json()
        assert [q["quarter"] for q in data] == ["Q2-2025"]
        assert data[0]["total_orders"] == len(_orders(client, month="Q2-2025"))

    def test_month_filter(self, client):
        data = client.get("/api/reports/quarterly", params={"month": "2025-05"}).json()
        assert len(data) == 1 and data[0]["quarter"] == "Q2-2025"
        assert data[0]["total_orders"] == len(_orders(client, month="2025-05"))

    def test_warehouse_category_status_filters(self, client):
        params = {"warehouse": "Tokyo", "category": "sensors", "status": "delivered"}
        data = client.get("/api/reports/quarterly", params=params).json()
        expected = _orders(client, **params)
        assert sum(q["total_orders"] for q in data) == len(expected)
        assert all(q["fulfillment_rate"] == 100 for q in data)

    def test_all_values_behave_like_no_filter(self, client):
        base = client.get("/api/reports/quarterly").json()
        allp = client.get("/api/reports/quarterly", params={"warehouse": "all", "category": "all", "status": "all", "month": "all"}).json()
        assert base == allp

    def test_no_match_returns_empty_list(self, client):
        response = client.get("/api/reports/quarterly", params={"warehouse": "Nowhere"})
        assert response.status_code == 200
        assert response.json() == []


class TestMonthlyTrends:
    def test_shape_and_order(self, client):
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200
        data = response.json()
        months = [m["month"] for m in data]
        assert months == sorted(months)
        assert len(months) == len(set(months)) == 12
        for m in data:
            for field in ["month", "order_count", "revenue", "delivered_count"]:
                assert field in m
            assert m["delivered_count"] <= m["order_count"]

    def test_totals_match_orders(self, client):
        data = client.get("/api/reports/monthly-trends").json()
        all_orders = _orders(client)
        assert sum(m["order_count"] for m in data) == len(all_orders)
        assert sum(m["revenue"] for m in data) == pytest.approx(sum(o["total_value"] for o in all_orders), rel=1e-6)

    def test_consistent_with_quarterly(self, client):
        monthly = client.get("/api/reports/monthly-trends").json()
        for q in client.get("/api/reports/quarterly").json():
            n = int(q["quarter"][1])
            in_q = [m for m in monthly if (int(m["month"][5:7]) - 1) // 3 + 1 == n]
            assert sum(m["order_count"] for m in in_q) == q["total_orders"]

    def test_quarter_filter(self, client):
        data = client.get("/api/reports/monthly-trends", params={"month": "Q1-2025"}).json()
        assert [m["month"] for m in data] == ["2025-01", "2025-02", "2025-03"]

    def test_month_filter(self, client):
        data = client.get("/api/reports/monthly-trends", params={"month": "2025-08"}).json()
        assert len(data) == 1 and data[0]["order_count"] == len(_orders(client, month="2025-08"))

    def test_other_filters(self, client):
        params = {"warehouse": "London", "category": "actuators"}
        data = client.get("/api/reports/monthly-trends", params=params).json()
        assert sum(m["order_count"] for m in data) == len(_orders(client, **params))
