# Diseño

`ServiceTemplate` declara trabajo, complejidad, materiales con uso `purchase`, `client_asset` o `excluded`, cantidades y pasos de verificación. `ServiceRequest` aporta `ScopeIntake` AT-246, evidencia de trabajo existente, cantidades verificadas de activos del cliente y una política monetaria explícita. `evaluate_service` reconstruye el borrador mediante `build_scope_draft`; no confía en una lista de preguntas suministrada externamente.

Un activo del cliente, aun no validado, nunca se convierte implícitamente en compra. Para reutilizarlo se exige disponibilidad, validación y evidencia de cantidad suficiente. Un conflicto entre compra y propiedad del cliente queda pendiente. Los materiales excluidos se conservan en la proyección. Una compra sin precio se muestra como requisito de compra y bloquea el total final; AT-259 no inventa precios de materiales.

La única línea monetaria es mano de obra AT-224. `ContingencyDecision.APPLIES` pasa exactamente `Decimal('0.05')` a `PriceLine` una vez; `NOT_APPLICABLE` pasa cero; `UNKNOWN` bloquea la cotización. AT-224 realiza todo cálculo, impuesto y redondeo. La proyección externa conserva alcance, materiales y un total sólo cuando no quedan pendientes, sin exponer componentes de contingencia internos. La política tributaria proviene del llamador y el 13% del caso es ficticio, no una tasa legal.

Los pasos de verificación son obligaciones de ejecución, no resultados inventados de una prueba futura. No se acredita ejecución real ni se realizan compras.
