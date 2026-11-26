# service-templates Specification

## Purpose

Planificar servicios de forma tipada con evidencias y precios explícitos, conservando condiciones pendientes.

## ADDED Requirements

### Requirement: Plantilla de servicio trazable

El sistema SHALL representar complejidad, trabajos incluidos/excluidos, materiales incluidos/excluidos con cantidades y pasos de verificación. SHALL rechazar nombres duplicados, cantidades inválidas y trabajo simultáneamente incluido y excluido.

#### Scenario: Exclusión visible
- **GIVEN** un servicio con reparación de pared y pintura excluidas
- **WHEN** se proyecta el servicio para el cliente
- **THEN** la reparación y la pintura permanecen explícitas en sus exclusiones.

### Requirement: Propiedad y evidencia de trabajos existentes

El sistema SHALL conservar trabajos existentes verificados o desconocidos, y SHALL requerir evidencia para afirmar ausencia o verificación. SHALL conservar activos del cliente fuera de las compras. SHALL requerir disponibilidad, validación y cantidad verificada suficiente antes de tratar un activo del cliente como reutilizable; los conflictos de propiedad SHALL permanecer pendientes.

#### Scenario: Gabinete del cliente validado
- **GIVEN** un gabinete disponible y validado, con dos unidades verificadas para dos requeridas
- **WHEN** se evalúa el servicio
- **THEN** no aparece como compra y el material puede reutilizarse.

#### Scenario: Cantidad o propiedad incierta
- **GIVEN** un gabinete del cliente sin cantidad suficiente o una compra propuesta para un artículo del cliente
- **WHEN** se evalúa el servicio
- **THEN** no se agrega una compra implícita y el resultado queda pendiente.

### Requirement: Contingencia única y precio seguro

El sistema SHALL usar el motor AT-224 para toda aritmética. SHALL aplicar una contingencia interna de 5% una sola vez cuando la política explícita diga que aplica, cero cuando no aplica y SHALL dejar pendiente aplicabilidad desconocida. SHALL dejar pendiente impuesto requerido sin tasa y materiales por comprar sin precio. La proyección externa SHALL omitir los componentes y la decisión interna de contingencia y SHALL omitir el total final cuando haya pendientes.

#### Scenario: Mano de obra ficticia
- **GIVEN** base 40.00, contingencia aplicable 5%, impuesto excluido declarado 13%, moneda de dos decimales y una unidad
- **WHEN** se evalúa un servicio sin pendientes
- **THEN** el unitario final es 47.46, sin duplicar contingencia ni divulgar el componente interno.

#### Scenario: Alcance o precio faltante
- **GIVEN** trabajo existente incierto, alcance incompleto o material de compra sin precio
- **WHEN** se evalúa el servicio
- **THEN** se indican los campos pendientes y no se presenta total final.
