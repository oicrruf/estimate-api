"""Pure Decimal pricing from explicit, synthetic or caller-approved policies.

This module neither discovers tax rules nor computes prices with an AI model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from enum import StrEnum

MAX_UNIT_AMOUNT = Decimal("1000000000000000000")
MAX_QUANTITY = 1_000_000_000
MAX_QUOTE_LINES = 1_000_000

# Accepted inputs have <=1000 coefficient digits and |exponent|<=1000.
# Unit amount <=10^18; contingency, discount and tax rates <=1. The deepest
# multiplication is (price * contingency * discount * tax), so its scale can
# reach 4000 places. Every intermediate is <=4*10^18, hence <4020 digits.
# 4096 significant digits and exponent limits wider than +/-4000 guarantee
# exact intermediates before the one intentional currency quantization.
# A quote has <=10^6 lines of <=10^9 units, bounding its total below 4*10^33.
_CALC_CONTEXT = Context(
    prec=4096,
    rounding=ROUND_HALF_EVEN,
    Emin=-10000,
    Emax=10000,
    traps=[InvalidOperation, DivisionByZero, Overflow],
)


def _ref(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _decimal(value: object, name: str, *, maximum: Decimal | None = None) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be a finite, nonnegative Decimal")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} exceeds the supported bound")
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or len(value.as_tuple().digits) > 1000 or abs(exponent) > 1000:
        raise ValueError(f"{name} exceeds the supported precision")
    return value


@dataclass(frozen=True)
class CurrencyPolicy:
    code: str
    minor_units: int
    rounding: str = ROUND_HALF_UP

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not re.fullmatch(r"[A-Z]{3}", self.code):
            raise ValueError("currency code must be three uppercase letters")
        if isinstance(self.minor_units, bool) or not isinstance(self.minor_units, int):
            raise ValueError("minor_units must be an integer")
        if not 0 <= self.minor_units <= 4:
            raise ValueError("minor_units must be between zero and four")
        if self.rounding not in (ROUND_HALF_UP, ROUND_HALF_EVEN):
            raise ValueError("rounding mode must be explicit and supported")

    @property
    def quantum(self) -> Decimal:
        return Decimal((0, (1,), -self.minor_units))


def _fits_currency_precision(amount: Decimal, currency: CurrencyPolicy) -> bool:
    """Check final-price precision from coefficient/exponent without arithmetic context."""
    if amount.is_zero():
        return True
    digits = amount.as_tuple().digits
    exponent = amount.as_tuple().exponent
    assert isinstance(exponent, int)
    trailing_needed = -currency.minor_units - exponent
    return trailing_needed <= 0 or (
        trailing_needed <= len(digits) and all(digit == 0 for digit in digits[-trailing_needed:])
    )


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: CurrencyPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.currency, CurrencyPolicy):
            raise ValueError("currency policy is required")
        _decimal(self.amount, "amount", maximum=MAX_UNIT_AMOUNT)


class LineKind(StrEnum):
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SHIPPING = "shipping"
    IMPORT = "import"


class PriceBasis(StrEnum):
    NET = "net"
    TAX_INCLUDED = "tax_included"
    CONFIRMED_FINAL = "confirmed_final"


class TaxTreatment(StrEnum):
    EXCLUDED = "excluded"
    INCLUDED = "included"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class PriceStatus(StrEnum):
    PRICED = "priced"
    PENDING = "pending"


@dataclass(frozen=True)
class TaxPolicy:
    treatment: TaxTreatment
    rate: Decimal | None
    source_ref: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.treatment, TaxTreatment):
            raise ValueError("invalid tax treatment")
        if self.rate is not None:
            _decimal(self.rate, "tax rate", maximum=Decimal(1))
        if self.treatment in (TaxTreatment.UNKNOWN, TaxTreatment.NOT_APPLICABLE):
            if self.rate is not None:
                raise ValueError("unknown or non-applicable tax cannot have a rate")
        if self.treatment != TaxTreatment.UNKNOWN:
            _ref(self.source_ref, "known tax treatment policy source")


@dataclass(frozen=True)
class Discount:
    source_ref: str
    rate: Decimal | None = None
    amount_per_unit: Money | None = None

    def __post_init__(self) -> None:
        _ref(self.source_ref, "discount source")
        if (self.rate is None) == (self.amount_per_unit is None):
            raise ValueError("discount requires exactly one rate or unit amount")
        if self.rate is not None:
            _decimal(self.rate, "discount rate", maximum=Decimal(1))
        if self.amount_per_unit is not None and not isinstance(self.amount_per_unit, Money):
            raise ValueError("discount amount must be Money")


@dataclass(frozen=True)
class PriceLine:
    line_id: str
    kind: LineKind
    basis: PriceBasis
    unit_price: Money
    quantity: int
    tax: TaxPolicy
    price_source_ref: str
    contingency_rate: Decimal = Decimal(0)
    discount: Discount | None = None

    def __post_init__(self) -> None:
        _ref(self.line_id, "line ID")
        _ref(self.price_source_ref, "price source ID")
        if not isinstance(self.kind, LineKind) or not isinstance(self.basis, PriceBasis):
            raise ValueError("invalid line kind or price basis")
        if not isinstance(self.unit_price, Money) or not isinstance(self.tax, TaxPolicy):
            raise ValueError("unit price and tax policy are required")
        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or not 1 <= self.quantity <= MAX_QUANTITY
        ):
            raise ValueError("quantity must be a positive bounded integer")
        _decimal(self.contingency_rate, "contingency rate", maximum=Decimal(1))
        if self.discount is not None and not isinstance(self.discount, Discount):
            raise ValueError("discount must be a Discount object")
        if self.discount and self.discount.amount_per_unit:
            if self.discount.amount_per_unit.currency != self.unit_price.currency:
                raise ValueError("discount and price currencies differ")
        if self.kind == LineKind.SHIPPING and self.basis != PriceBasis.CONFIRMED_FINAL:
            raise ValueError("documented shipping must be a final passthrough amount")
        if self.basis == PriceBasis.CONFIRMED_FINAL:
            if self.contingency_rate or self.discount:
                raise ValueError("confirmed final prices cannot receive another adjustment")
            if self.tax.treatment == TaxTreatment.EXCLUDED:
                raise ValueError("confirmed final price cannot require added tax")
            if not _fits_currency_precision(self.unit_price.amount, self.unit_price.currency):
                raise ValueError("confirmed final price exceeds currency precision")
        elif self.basis == PriceBasis.TAX_INCLUDED:
            if self.tax.treatment != TaxTreatment.INCLUDED:
                raise ValueError("tax-included price requires included treatment")
        elif self.tax.treatment == TaxTreatment.INCLUDED:
            raise ValueError("net price cannot be declared tax-included")


@dataclass(frozen=True)
class PricedLine:
    input: PriceLine
    status: PriceStatus
    contingency_unit: Decimal
    discount_unit: Decimal
    amount_after_discount: Decimal
    tax_added_unit: Decimal | None
    unrounded_unit: Decimal | None
    rounded_unit: Decimal | None
    line_total: Decimal | None
    missing_fields: tuple[str, ...]


@dataclass(frozen=True)
class QuoteInput:
    currency: CurrencyPolicy
    lines: tuple[PriceLine, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.currency, CurrencyPolicy):
            raise ValueError("quote currency policy is required")
        if not isinstance(self.lines, tuple) or not all(
            isinstance(line, PriceLine) for line in self.lines
        ):
            raise ValueError("quote lines must be a tuple of PriceLine")
        if len(self.lines) > MAX_QUOTE_LINES:
            raise ValueError("quote exceeds supported line count")


@dataclass(frozen=True)
class PricedQuote:
    input: QuoteInput
    status: PriceStatus
    lines: tuple[PricedLine, ...]
    total: Decimal | None
    pending_line_ids: tuple[str, ...]


def price_line(line: PriceLine) -> PricedLine:
    """Calculate exactly one unit, quantize, then multiply its rounded price."""
    with localcontext(_CALC_CONTEXT):
        contingency = line.unit_price.amount * line.contingency_rate
        adjusted = line.unit_price.amount + contingency
        discount = Decimal(0)
        if line.discount is not None:
            if line.discount.rate is not None:
                discount = adjusted * line.discount.rate
            else:
                assert line.discount.amount_per_unit is not None
                discount = line.discount.amount_per_unit.amount
        if discount > adjusted:
            raise ValueError("discount exceeds adjusted unit price")
        after_discount = adjusted - discount
        if (
            line.basis != PriceBasis.CONFIRMED_FINAL
            and line.tax.treatment
            in (
                TaxTreatment.UNKNOWN,
                TaxTreatment.EXCLUDED,
            )
            and line.tax.rate is None
        ):
            missing = "tax_policy" if line.tax.treatment == TaxTreatment.UNKNOWN else "tax_rate"
            return PricedLine(
                line,
                PriceStatus.PENDING,
                contingency,
                discount,
                after_discount,
                None,
                None,
                None,
                None,
                (missing,),
            )
        tax_added = (
            after_discount * line.tax.rate
            if line.basis == PriceBasis.NET
            and line.tax.treatment == TaxTreatment.EXCLUDED
            and line.tax.rate is not None
            else Decimal(0)
        )
        unrounded = after_discount + tax_added
        try:
            rounded = unrounded.quantize(
                line.unit_price.currency.quantum, rounding=line.unit_price.currency.rounding
            )
        except InvalidOperation as exc:
            raise ValueError("unit price exceeds supported decimal precision") from exc
        total = rounded * line.quantity
        return PricedLine(
            line,
            PriceStatus.PRICED,
            contingency,
            discount,
            after_discount,
            tax_added,
            unrounded,
            rounded,
            total,
            (),
        )


def price_quote(quote: QuoteInput) -> PricedQuote:
    """Price a same-currency quote; never present a partial sum as its final total."""
    if not quote.lines:
        raise ValueError("quote requires at least one line")
    line_ids = [line.line_id for line in quote.lines]
    if len(set(line_ids)) != len(line_ids):
        raise ValueError("quote line IDs must be unique")
    if any(line.unit_price.currency != quote.currency for line in quote.lines):
        raise ValueError("quote cannot mix currencies or rounding policies")
    priced = tuple(price_line(line) for line in quote.lines)
    pending = tuple(line.input.line_id for line in priced if line.status == PriceStatus.PENDING)
    with localcontext(_CALC_CONTEXT):
        total = (
            None
            if pending
            else sum(
                (line.line_total for line in priced if line.line_total is not None), Decimal(0)
            )
        )
    return PricedQuote(
        quote, PriceStatus.PENDING if pending else PriceStatus.PRICED, priced, total, pending
    )
