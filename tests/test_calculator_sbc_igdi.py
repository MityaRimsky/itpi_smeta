import pytest

from bot.services.database import DatabaseService


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, _cols="*"):
        return self

    def like(self, field, pattern):
        # very small LIKE support: prefix/suffix %
        def _match(row):
            val = str(row.get(field, ""))
            pat = pattern.replace("%", "")
            return pat in val
        self._filters.append(_match)
        return self

    def eq(self, field, value):
        self._filters.append(lambda row: row.get(field) == value)
        return self

    def in_(self, field, values):
        self._filters.append(lambda row: row.get(field) in values)
        return self

    def execute(self):
        rows = self._rows
        for f in self._filters:
            rows = [r for r in rows if f(r)]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self, data):
        self._data = data

    def table(self, name):
        return FakeTable(self._data.get(name, []))


class FakeDB(DatabaseService):
    def __init__(self, data):
        # bypass real supabase client
        self.client = FakeClient(data)


def test_match_bool_none_param_does_not_match_explicit_condition():
    assert DatabaseService._match_bool(None, True) is False
    assert DatabaseService._match_bool(None, False) is False
    assert DatabaseService._match_bool(None, None) is True


@pytest.mark.asyncio
async def test_internal_transport_addon():
    data = {
        "norm_addons": [
            {
                "code": "INTERNAL_T4_0_10_0_75",
                "name": "Internal",
                "calc_type": "percent",
                "value": 0.10,
                "base_type": "field",
                "conditions": {
                    "distance_from_base_km_min": 0,
                    "distance_from_base_km_max": 10,
                    "field_cost_thousand_min": 0,
                    "field_cost_thousand_max": 75,
                },
                "source_ref": {},
            }
        ]
    }
    db = FakeDB(data)
    addons = await db.get_addons_by_conditions(
        params={"distance_to_base_km": 8},
        field_cost=70000,
    )
    assert addons
    assert addons[0]["amount"] == pytest.approx(7000, rel=1e-6)


@pytest.mark.asyncio
async def test_external_transport_addon():
    data = {
        "norm_addons": [
            {
                "code": "EXTERNAL_T5_0_100_0_3",
                "name": "External",
                "calc_type": "percent",
                "value": 0.20,
                "base_type": "field_plus_internal",
                "conditions": {
                    "distance_oneway_km_min": 0,
                    "distance_oneway_km_max": 100,
                    "duration_months_min": 0,
                    "duration_months_max": 3,
                },
                "source_ref": {},
            }
        ]
    }
    db = FakeDB(data)
    addons = await db.get_addons_by_conditions(
        params={"external_distance_km": 80, "expedition_duration_months": 2},
        field_cost=100000,
        internal_transport_cost=10000,
    )
    assert addons
    assert addons[0]["amount"] == pytest.approx(22000, rel=1e-6)


@pytest.mark.asyncio
async def test_org_liq_duration_coeff():
    data = {
        "norm_addons": [
            {
                "code": "ORG_LIQ_6PCT",
                "name": "Org/Liq",
                "calc_type": "percent",
                "value": 0.06,
                "base_type": "field_plus_internal",
                "conditions": {},
                "source_ref": {},
            }
        ],
        "norm_coeffs": [
            {
                "code": "ORG_LIQ_DURATION_12_16",
                "name": "Duration",
                "value": 0.8,
                "apply_to": "total",
                "conditions": {"applies_to_addon": "ORG_LIQ_6PCT", "duration_months_min": 12, "duration_months_max": 16},
                "source_ref": {},
            }
        ],
    }
    db = FakeDB(data)
    addons = await db.get_addons_by_conditions(
        params={"include_org_liq": True, "expedition_duration_months": 12},
        field_cost=40000,
        internal_transport_cost=0,
    )
    assert addons
    # base 0.06 * cost_coeff(2.0) * duration_coeff(0.8) = 0.096
    assert addons[0]["amount"] == pytest.approx(3840, rel=1e-6)


@pytest.mark.asyncio
async def test_piecewise_addon_formula():
    data = {
        "norm_addons": [
            {
                "code": "PROGRAM_T78_100_250",
                "name": "Program",
                "calc_type": "percent",
                "value": 0.03,
                "base_type": "subtotal",
                "conditions": {
                    "base_cost_thousand_min": 100,
                    "base_cost_thousand_max": 250,
                    "fixed_amount": 4300,
                    "percent_over": 0.03,
                },
                "source_ref": {},
            }
        ]
    }
    db = FakeDB(data)
    addons = await db.get_addons_by_conditions(
        params={"base_cost_thousand": 250},
        field_cost=0,
        internal_transport_cost=0,
    )
    assert addons
    # 4300 + (250-100)*1000*0.03 = 8800
    assert addons[0]["amount"] == pytest.approx(8800, rel=1e-6)


@pytest.mark.asyncio
async def test_k1_scale_height_territory_match():
    data = {
        "norm_coeffs": [
            {
                "code": "T9_TEST",
                "name": "Test",
                "value": 1.2,
                "apply_to": "price",
                "conditions": {"table_no": 9, "scale": "1:500", "height_section": 0.5, "territory": "застроенная"},
                "source_ref": {"table": 9},
            }
        ]
    }
    db = FakeDB(data)
    coeffs = await db.get_k1_coefficients(9, {"scale": "1:500", "height_section": 0.5, "territory": "застроенная"})
    assert coeffs


@pytest.mark.asyncio
async def test_k2_color_plan_match():
    data = {
        "norm_coeffs": [
            {
                "code": "COLOR_PLAN_1_1",
                "name": "Color",
                "value": 1.1,
                "apply_to": "office",
                "exclusive_group": "COLOR_OR_COMPUTER",
                "conditions": {"color_plan": True},
                "source_ref": {},
            }
        ]
    }
    db = FakeDB(data)
    coeffs = await db.get_k2_coefficients({"color_plan": True})
    assert coeffs


@pytest.mark.asyncio
async def test_k1_ignores_coeff_without_table_binding():
    data = {
        "norm_coeffs": [
            {
                "code": "UNBOUND_PRICE_COEFF",
                "name": "Unbound",
                "value": 1.1,
                "apply_to": "price",
                "conditions": {"scale": "1:500"},
                "source_ref": {},
            },
            {
                "code": "BOUND_T9_COEFF",
                "name": "Bound",
                "value": 1.2,
                "apply_to": "price",
                "conditions": {"table_no": 9, "scale": "1:500"},
                "source_ref": {"table": 9},
            },
        ]
    }
    db = FakeDB(data)
    coeffs = await db.get_k1_coefficients(9, {"scale": "1:500"})
    assert len(coeffs) == 1
    assert coeffs[0]["code"] == "BOUND_T9_COEFF"


@pytest.mark.asyncio
async def test_k2_only_from_section_15():
    data = {
        "norm_coeffs": [
            {
                "code": "OFFICE_FIELD_CAMP_1_15",
                "name": "Камеральные в экспедиционных условиях",
                "value": 1.15,
                "apply_to": "office",
                "conditions": {"office_in_field_camp": True},
                "source_ref": {"section": "п.14"},
            },
            {
                "code": "COLOR_PLAN_1_1",
                "name": "План в цвете",
                "value": 1.1,
                "apply_to": "office",
                "conditions": {"color_plan": True},
                "source_ref": {"section": "п.15г"},
            },
        ]
    }
    db = FakeDB(data)
    coeffs = await db.get_k2_coefficients({"office_in_field_camp": True, "color_plan": True})
    assert len(coeffs) == 1
    assert coeffs[0]["code"] == "COLOR_PLAN_1_1"


@pytest.mark.asyncio
async def test_k2_missing_param_does_not_activate_false_condition():
    data = {
        "norm_coeffs": [
            {
                "code": "COLOR_PLAN_FALSE",
                "name": "Без цветного плана",
                "value": 0.95,
                "apply_to": "office",
                "conditions": {"color_plan": False},
                "source_ref": {"section": "п.15г"},
            }
        ]
    }
    db = FakeDB(data)
    coeffs = await db.get_k2_coefficients({})
    assert coeffs == []
