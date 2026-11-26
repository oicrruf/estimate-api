"""Standalone AT-224 pricing entry point with entirely fictitious policies."""

from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from estimate_api.pricing import (
    CurrencyPolicy,
    Discount,
    LineKind,
    Money,
    PriceBasis,
    PriceLine,
    PriceStatus,
    QuoteInput,
    TaxPolicy,
    TaxTreatment,
    price_line,
    price_quote,
)

USD = CurrencyPolicy("USD", 2)
NO_TAX = TaxPolicy(TaxTreatment.NOT_APPLICABLE, None, "RULE-FICT-NO-TAX")
EXCLUDED = TaxPolicy(TaxTreatment.EXCLUDED, Decimal("0.13"), "RULE-FICT-13")
INCLUDED = TaxPolicy(TaxTreatment.INCLUDED, Decimal("0.13"), "RULE-FICT-INC-13")


def _line(
    line_id: str = "LINE-FICT-1",
    *,
    amount: str = "40.00",
    kind: LineKind = LineKind.LABOR,
    basis: PriceBasis = PriceBasis.NET,
    tax: TaxPolicy = EXCLUDED,
    quantity: int = 3,
    contingency: str = "0.05",
    discount: Discount | None = None,
    currency: CurrencyPolicy = USD,
) -> PriceLine:
    return PriceLine(
        line_id,
        kind,
        basis,
        Money(Decimal(amount), currency),
        quantity,
        tax,
        f"PRICE-FICT-{line_id}",
        Decimal(contingency),
        discount,
    )


def test_labor_stipulated_example_uses_unit_rounding() -> None:
    result = price_quote(QuoteInput(USD, (_line(),)))
    assert result.status == PriceStatus.PRICED
    assert result.total == Decimal("142.38")
    line = result.lines[0]
    assert line.contingency_unit == Decimal("2.0000")
    assert line.tax_added_unit == Decimal("5.460000")
    assert line.rounded_unit == Decimal("47.46")
    assert line.line_total == Decimal("142.38")
    assert line.input.tax.source_ref == "RULE-FICT-13"


def test_tax_included_equipment_adds_contingency_once_without_second_tax() -> None:
    equipment = _line(
        "EQUIP-FICT",
        amount="100.00",
        kind=LineKind.EQUIPMENT,
        basis=PriceBasis.TAX_INCLUDED,
        tax=INCLUDED,
        quantity=2,
    )
    first = price_line(equipment)
    assert first.rounded_unit == Decimal("105.00")
    assert first.line_total == Decimal("210.00")
    assert first.tax_added_unit == 0
    assert price_line(equipment) == first
    discounted = price_line(
        replace(equipment, discount=Discount("DISC-FICT-INC", rate=Decimal("0.10")))
    )
    assert discounted.rounded_unit == Decimal("94.50")
    assert discounted.tax_added_unit == 0


def test_final_price_and_documented_shipping_are_passthrough() -> None:
    final = _line(
        "FINAL-FICT",
        amount="99.99",
        kind=LineKind.EQUIPMENT,
        basis=PriceBasis.CONFIRMED_FINAL,
        tax=INCLUDED,
        contingency="0",
        quantity=3,
    )
    shipping = _line(
        "SHIP-FICT",
        amount="12.34",
        kind=LineKind.SHIPPING,
        basis=PriceBasis.CONFIRMED_FINAL,
        tax=TaxPolicy(TaxTreatment.UNKNOWN, None, None),
        contingency="0",
        quantity=1,
    )
    priced = price_quote(QuoteInput(USD, (final, shipping)))
    assert priced.status == PriceStatus.PRICED
    assert [item.rounded_unit for item in priced.lines] == [Decimal("99.99"), Decimal("12.34")]
    assert priced.total == Decimal("312.31")
    assert all(item.tax_added_unit == 0 for item in priced.lines)
    with pytest.raises(ValueError, match="final prices"):
        replace(final, contingency_rate=Decimal("0.05"))
    with pytest.raises(ValueError, match="shipping"):
        replace(shipping, basis=PriceBasis.NET)


def test_documented_percentage_and_fixed_discounts_before_excluded_tax() -> None:
    percent = _line(
        "DISC-PCT",
        amount="100.00",
        kind=LineKind.EQUIPMENT,
        quantity=2,
        discount=Discount("DISC-FICT-PCT", rate=Decimal("0.10")),
    )
    fixed = _line(
        "DISC-FIX",
        amount="100.00",
        kind=LineKind.EQUIPMENT,
        quantity=1,
        discount=Discount("DISC-FICT-FIX", amount_per_unit=Money(Decimal(10), USD)),
    )
    result = price_quote(QuoteInput(USD, (percent, fixed)))
    assert result.lines[0].discount_unit == Decimal("10.500000")
    assert result.lines[0].rounded_unit == Decimal("106.79")
    assert result.lines[0].line_total == Decimal("213.58")
    assert result.lines[1].rounded_unit == Decimal("107.35")
    assert result.total == Decimal("320.93")


def test_import_tax_unknown_keeps_line_and_quote_pending() -> None:
    import_line = _line(
        "IMPORT-FICT",
        amount="80.00",
        kind=LineKind.IMPORT,
        tax=TaxPolicy(TaxTreatment.UNKNOWN, None, None),
        contingency="0",
    )
    quote = price_quote(QuoteInput(USD, (_line(), import_line)))
    assert quote.status == PriceStatus.PENDING
    assert quote.total is None
    assert quote.pending_line_ids == ("IMPORT-FICT",)
    assert quote.lines[1].missing_fields == ("tax_policy",)
    assert quote.lines[1].rounded_unit is None
    missing_rate = replace(
        import_line, tax=TaxPolicy(TaxTreatment.EXCLUDED, None, "RULE-FICT-PENDING")
    )
    assert price_line(missing_rate).missing_fields == ("tax_rate",)
    assert price_line(missing_rate).line_total is None


def test_rounding_per_unit_and_declared_currency_precision() -> None:
    line = _line("ROUND-FICT", amount="0.335", tax=NO_TAX, contingency="0", quantity=3)
    result = price_line(line)
    assert result.rounded_unit == Decimal("0.34")
    assert result.line_total == Decimal("1.02")
    whole = CurrencyPolicy("XYZ", 0)
    whole_line = _line(
        "WHOLE-FICT",
        amount="1.5",
        tax=NO_TAX,
        contingency="0",
        quantity=2,
        currency=whole,
    )
    assert price_line(whole_line).line_total == Decimal("4")
    even = CurrencyPolicy("XYZ", 0, ROUND_HALF_EVEN)
    assert price_line(replace(whole_line, unit_price=Money(Decimal("2.5"), even))).rounded_unit == 2


def test_reject_malformed_numbers_and_ambiguous_policy() -> None:
    for bad in (
        float("nan"),
        float("inf"),
        1.0,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-1"),
    ):
        with pytest.raises(ValueError):
            Money(bad, USD)  # type: ignore[arg-type]
    for bad in (True, 0, -1, 1.5):
        with pytest.raises(ValueError):
            replace(_line(), quantity=bad)  # type: ignore[arg-type]
    for bad in (Decimal("-0.01"), Decimal("1.01"), Decimal("NaN")):
        with pytest.raises(ValueError):
            replace(_line(), contingency_rate=bad)
        with pytest.raises(ValueError):
            TaxPolicy(TaxTreatment.EXCLUDED, bad, "RULE-FICT")
    with pytest.raises(ValueError, match="currencies"):
        price_quote(QuoteInput(USD, (_line(currency=CurrencyPolicy("EUR", 2)),)))
    with pytest.raises(ValueError, match="currencies differ"):
        _line(
            discount=Discount(
                "DISC-FICT", amount_per_unit=Money(Decimal(1), CurrencyPolicy("EUR", 2))
            )
        )
    with pytest.raises(ValueError, match="currencies"):
        price_quote(QuoteInput(USD, (_line(currency=CurrencyPolicy("USD", 0)),)))
    with pytest.raises(ValueError, match="requires included"):
        _line(basis=PriceBasis.TAX_INCLUDED, tax=EXCLUDED)
    with pytest.raises(ValueError, match="policy source"):
        TaxPolicy(TaxTreatment.EXCLUDED, Decimal("0.13"), None)
    with pytest.raises(ValueError, match="discount exceeds"):
        price_line(_line(discount=Discount("DISC-FICT", amount_per_unit=Money(Decimal(1000), USD))))
    with pytest.raises(ValueError, match="unique"):
        price_quote(QuoteInput(USD, (_line(), _line())))
    with pytest.raises(ValueError, match="uppercase"):
        CurrencyPolicy("usd", 2)
    with pytest.raises(ValueError, match="supported precision"):
        Money(Decimal("1e-1001"), USD)
    with pytest.raises(ValueError, match="positive bounded"):
        replace(_line(), quantity=1_000_000_001)
    with pytest.raises(ValueError, match="policy source"):
        TaxPolicy(TaxTreatment.INCLUDED, Decimal("0.13"), " ")
    with pytest.raises(ValueError, match="discount source"):
        Discount(" ", rate=Decimal("0.05"))
    with pytest.raises(ValueError, match="added tax"):
        _line(basis=PriceBasis.CONFIRMED_FINAL, tax=EXCLUDED, contingency="0")
