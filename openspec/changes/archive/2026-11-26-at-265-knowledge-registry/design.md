# Design

## Context

El documento AT-264 identifica paquetes por `namespace` y `version`, y mantiene los hechos propios del dominio en `facts`. Un catálogo debe poder evolucionar sin añadir campos al núcleo.

## Decisions

1. El registro tiene JSON Schema 2020-12 y tipos Python propios. Cada paquete declara fuente y versión, jurisdicciones, categorías, ámbitos, límites y estado de revisión.
2. La coincidencia exige referencia exacta de `namespace` y `version` en el proyecto. La jurisdicción y categoría coinciden literalmente; el ámbito de proyecto cubre sus ámbitos internos y los demás ámbitos requieren coincidencia exacta.
3. El resultado solo describe cobertura del catálogo. La revisión verificada es metadato proporcionado por el registrador y exige referencia de revisor y evidencia; este módulo no autentica credenciales.
4. Múltiples paquetes aplicables requieren especialista. Para señalar incompatibilidades declaradas, dos `choice` distintos bajo el mismo `topic` producen un conflicto ordenado por tema e ID. No se interpretan las reglas ni sus valores.
5. Entradas inválidas producen `pending_specialist`; ausencia de paquete produce `unsupported`. Ninguna ruta produce conformidad normativa o conclusión técnica.

## Risks / Trade-offs

- La coincidencia literal de jurisdicción no infiere jerarquías territoriales; una cobertura no declarada permanece sin soporte.
- Los metadatos `verified` no prueban competencia real; el proceso de revisión externo debe verificar la evidencia antes de registrarlos.
