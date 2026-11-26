# universal-package-handoff Specification

## Purpose

Hacer verificable el límite entre proyecto universal, paquetes especializados y evidencia sin prometer un flujo completo.

## ADDED Requirements

### Requirement: Trazabilidad de responsabilidades
La guía SHALL identificar qué módulo integrado valida el sobre universal, el registro y la aplicabilidad, los checks globales y los patrones especializados. SHALL distinguir cobertura de catálogo de conclusión técnica.

#### Scenario: Lectura del mapa
- **GIVEN** una nueva especialidad ficticia
- **WHEN** se consulta la guía
- **THEN** se identifica cómo agregar un paquete versionado sin insertar campos o ramas de cámara en el núcleo.

### Requirement: Prueba multirrubro independiente
Un smoke SHALL usar los contratos integrados con fixtures ficticios de pintura y evento, SHALL comprobar cobertura exacta positiva sólo como metadata y SHALL mostrar `unsupported` y `pending_specialist` en entradas sin cobertura o revisión declarada.

#### Scenario: Dos dominios y cobertura insuficiente
- **GIVEN** documentos válidos de pintura y evento y un registro sintético
- **WHEN** se valida el núcleo y se resuelve cobertura
- **THEN** ambos usan el mismo contrato, y la falta de categoría, jurisdicción o revisión declarada produce estados conservadores.

### Requirement: Evidencia y aislamiento declarados con honestidad
El smoke SHALL demostrar que un check genérico con evidencia rota o fuente supuesta queda pendiente y bloqueante. La guía SHALL situar autorización y aislamiento por proyecto en una futura frontera de servicio confiable; SHALL NOT afirmar que la validación local los aplica.

#### Scenario: Fuente supuesta
- **GIVEN** un permiso de evento supuesto
- **WHEN** se evalúa un check de cobertura declarado
- **THEN** el hallazgo es `pending` y bloqueante, sin afirmar aprobación del evento.
