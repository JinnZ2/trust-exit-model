"""Tests for community amplification model."""

import pytest
from src.community_amplification import CommunityAmplificationModel


@pytest.fixture
def model():
    return CommunityAmplificationModel()


class TestFirstOrderDefections:
    def test_zero_exits_zero_defections(self, model):
        result = model.first_order_defections(0, 5, 12)
        assert result == 0.0

    def test_grows_over_time(self, model):
        d1 = model.first_order_defections(10, 5, 1)
        d12 = model.first_order_defections(10, 5, 12)
        assert d12 > d1

    def test_scales_with_exits(self, model):
        d10 = model.first_order_defections(10, 5, 12)
        d20 = model.first_order_defections(20, 5, 12)
        assert d20 == pytest.approx(d10 * 2)


class TestTotalDefections:
    def test_second_order_positive(self, model):
        result = model.total_defections(10, 5, 12)
        assert result["second_order"] > 0
        assert result["total"] > result["first_order"]

    def test_returns_all_keys(self, model):
        result = model.total_defections(10, 5, 12)
        assert "first_order" in result
        assert "second_order" in result
        assert "total" in result


class TestCacImpact:
    def test_positive_cost(self, model):
        cost = model.cac_impact(10, 5, 12, cac_per_customer=50.0)
        assert cost > 0

    def test_scales_with_cac(self, model):
        c50 = model.cac_impact(10, 5, 12, 50.0)
        c100 = model.cac_impact(10, 5, 12, 100.0)
        assert c100 == pytest.approx(c50 * 2)
