# Diseño

`price_line` recibe un `PriceLine` inmutable con `Money` y `CurrencyPolicy`. Rechaza `float`, no finitos, cantidades no enteras, moneda distinta y combinaciones ambiguas. El orden es precio base unitario → contingencia una vez → descuento documentado → impuesto sólo si la base excluye impuesto → redondeo por unidad con precisión y modo declarados → multiplicación por cantidad. El resultado conserva entradas y componentes; `price_quote` suma únicamente totales de líneas terminadas de la misma moneda.

`tax_included` no agrega otro impuesto. `confirmed_final` y envío documentado son importes de paso sin contingencia, descuento ni impuesto agregado. La importación de base sin tasa necesaria produce `PENDING` con el campo faltante, sin total final. El código no define tarifas legales: el 13% del ejemplo es un parámetro ficticio explícito.

La fuente de precio y la referencia de política fiscal son metadatos declarados, no certificados. Las integraciones futuras deberán resolver aprobaciones, vigencia de tarifas y jurisdicción fuera de este motor.
