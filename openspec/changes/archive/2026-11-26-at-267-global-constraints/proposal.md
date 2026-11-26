# Propuesta

## Why

Una solución puede tener materiales técnicamente individuales pero incumplir restricciones globales. AT-267 necesita findings trazables sin completar evidencias ausentes con suposiciones.

## What Changes

- Añadir checks declarativos de cardinalidad, capacidad, compatibilidad y cobertura en paquetes del contrato AT-264.
- Exigir origen, revisión vigente y evidencia conocida para cada operando; devolver pass, fail o pending tipados.
- Probar la entrada de documento sintético con puertos totales, puertos PoE, potencia, modelo EMT y cobertura.

## Fuera de alcance

No se modifica AT-238 ni se calculan rutas, cantidades de accesorios, estándares eléctricos, precios, permisos reales o un endpoint. Las dimensiones de tareas, materias primas, insumos, transporte, tiempo, permisos y normativa declarada usan el mismo check de cobertura; su selección y corroboración pertenecen a flujos posteriores.
