# ADR 0015 — Relate como grafo técnico local (AT-215)

- **Fecha:** 2026-11-26
- **Estado:** go experimental local; decisión de despliegue pendiente
- **Dependencia:** [ADR 0001](0001-arquitectura-inicial.md) y contrato SQL/API de los issues propietarios

## Contexto y decisión

El catálogo persistido conserva IDs estables de productos, capacidades y evidencias. Relate es una proyección reconstruible para consultar relaciones técnicas con Cypher y recomendaciones contextuales. Descartar un candidato de un proyecto no elimina conocimiento compartido. Las rectificaciones de evidencia preservan revisiones y motivo.

Se acepta Relate 1.3.0 para integrar un slice experimental: el runtime Python y un contenedor local escribieron y leyeron un archivo `.rl`, lo reabrieron desde otro proceso/contenedor y rechazaron un segundo escritor. Una copia del archivo cerrado se restauró en otro volumen nombrado. El [registro AT-215](../evidence/at-215.md) precisa resultados y límites. Se restringe a un solo dueño de escritura por store hasta pruebas adicionales.

## Condiciones para go de host

1. Verificar identidad, permisos y capacidades del host/Dokploy autorizado; volumen persistente entre restart y redeploy.
2. Ensayar respaldo fuera de host y restauración tras pérdida simulada, con RPO/RTO definidos.
3. Definir snapshot SQL versionado y reconciliación; probar fallos parciales, reintentos e integridad a escala.
4. Implementar autorización por recurso, idempotencia, revisión esperada y auditoría en SQL/API conforme a ADR 0001. El spike no expone operaciones mutables de negocio.
5. Probar lectores concurrentes, límites de memoria/latencia y healthcheck del servicio real.

La prueba local no autoriza afirmar persistencia o recuperación en Dokploy ni sincronización con Supabase. No se conectó ni modificó infraestructura real.

## Alternativa si falla el gate

Conservar productos, capacidades, compatibilidades, requisitos, alternativas y revisiones de evidencia en SQL normalizado con claves e índices; resolver consultas mediante joins y CTE cuando aplique. Medirlas con cargas representativas antes de sustituir Relate.
