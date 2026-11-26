# AT-224: contrato del motor de precios

`estimate_api.pricing.price_quote` acepta `QuoteInput` con líneas tipadas y una `CurrencyPolicy` explícita. Usa sólo `Decimal` y las tarifas que el llamador entrega; no consulta tasas ni fuentes externas. Los IDs y valores siguientes son ficticios.

| Base | Tratamiento permitido | Cálculo |
| --- | --- | --- |
| `net` | `excluded`, `not_applicable`, `unknown` | Contingencia, descuento y después impuesto excluido, si su tasa está declarada. |
| `tax_included` | `included` | Contingencia y descuento sobre el importe incluido; impuesto agregado cero. |
| `confirmed_final` | `included`, `not_applicable`, `unknown` | Importe de paso, sin contingencia, descuento ni impuesto agregado. |

El envío documentado exige `confirmed_final` y referencia de precio. Se redondea cada unitario con la precisión y modo indicados por `CurrencyPolicy`, luego se multiplica la cantidad y se suman los totales de línea. No hay conversión implícita entre códigos, precisiones ni modos de redondeo. El descuento puede ser porcentaje o importe por unidad, nunca ambos, y requiere referencia. La salida conserva entrada, contingencia, descuento, impuesto agregado, unitario antes y después de redondear, y total.

Una línea `import` de base sin política fiscal o sin tasa necesaria devuelve `pending` con `tax_policy` o `tax_rate` faltante y sin total. La cotización con alguna línea pendiente tampoco tiene total final. Un precio final confirmado puede conservar tratamiento tributario `unknown` porque no se añade impuesto; esto no afirma qué parte del precio es tributo.

Ejemplo estipulado: base ficticia `40.00`, contingencia `0.05`, tasa excluida `0.13`, tres unidades y moneda `USD` con dos decimales: `40 × 1.05 × 1.13 = 47.46` por unidad y `142.38` total. La tasa es sólo el parámetro del caso, no una afirmación legal.

El contrato rechaza importes negativos, no finitos, `float`, importes unitarios mayores que `10^18`, entradas con más de 1000 dígitos o escala de más de 1000, tasas mayores que 1, y cantidades fuera de `1..10^9`. El llamador debe validar vigencia, aprobación y jurisdicción de las políticas antes de crear entradas.
