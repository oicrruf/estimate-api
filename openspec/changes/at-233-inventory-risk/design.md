# Diseño

`read_inventory` lee ofertas y pool AT-229 sin mutar Relate. Una observación `STOCK_OBSERVATION` sintética, cuando existe, proporciona estado, cantidad, fecha de consulta, vigencia, proveedor/sucursal, reposición y fuente. Sin esa observación, la cifra de `OFFER.quantity` es sólo pública y la capacidad `poolCapacity` conserva su procedencia AT-229 sin convertirse en confirmación.

`evaluate_inventory` acepta un snapshot tipado, tiempo explícito y umbrales de cobertura. Sólo `supplier_confirmed` o `reserved` con fechas vigentes y fuente/evidencia aportan capacidad. Un pool compartido requiere además límite confirmado vigente; la suma de dos ofertas nunca supera ese límite. Una relación de distribuidor documentada señala correlación comercial y eleva un riesgo bajo a medio, pero no convierte las ofertas en un único pool. Observaciones desconocidas, públicas, caducadas o sin evidencia hacen la capacidad total indeterminada. La salida conserva claims y dependencias junto a motivos; elegibilidad técnica, score y selección manual no se calculan.

Las observaciones de prueba se escriben únicamente en stores temporales sintéticos antes de invocar el lector. No se crea API ni integración de producción.
