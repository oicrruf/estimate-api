# Spec Delta

## Purpose

Conserva los datos estructurados del proyecto y el catálogo compartido con revisiones, referencias íntegras y antecedentes comerciales sin imponer reglas de cálculo de precios.

## ADDED Requirements

### Requirement: Propiedad y membresía
La persistencia SHALL identificar exactamente un propietario de cada proyecto y membresías con roles editor o lector, sin duplicados. La transferencia de propiedad SHALL ser atómica, autorizada por el propietario actual y limitada a un miembro editor existente.

#### Scenario: Miembro único
- **GIVEN** un proyecto con un miembro editor
- **WHEN** se intenta registrar de nuevo el mismo usuario en el mismo proyecto
- **THEN** la base rechaza el duplicado.

#### Scenario: Transferencia de propiedad
- **GIVEN** un propietario y un miembro editor del mismo proyecto
- **WHEN** el propietario transfiere el proyecto al editor
- **THEN** el editor queda como único propietario y el antiguo propietario como editor.

### Requirement: Entidades y relaciones universales
La persistencia SHALL almacenar entidades del contrato universal con identificador estable y revisión; cada relación y paquete SHALL referenciar entidades del mismo proyecto.

#### Scenario: Relación entre proyectos
- **GIVEN** dos proyectos con entidades distintas
- **WHEN** una relación de uno apunta a la entidad del otro
- **THEN** la base rechaza la referencia.

### Requirement: Catálogo reutilizable y ofertas históricas
La persistencia SHALL separar catálogo global versionado de registros de proyecto y conservar ofertas fechadas como antecedentes inmutables.

#### Scenario: Candidato rechazado
- **GIVEN** un producto global con especificaciones, fuente y garantía
- **WHEN** un proyecto rechaza su candidatura
- **THEN** el producto y sus antecedentes permanecen disponibles para otros proyectos.

#### Scenario: Proveedor y sucursal
- **WHEN** se registra una oferta histórica
- **THEN** referencia proveedor y, si existe, una sucursal de ese mismo proveedor.

#### Scenario: Oferta con fecha inválida
- **WHEN** se registra una oferta cuya fecha final antecede a la inicial
- **THEN** la base la rechaza sin alterar ofertas anteriores.

#### Scenario: Evidencia revisada después de oferta
- **GIVEN** una oferta histórica creada con evidencia conocida
- **WHEN** la entidad de evidencia avanza de revisión
- **THEN** la oferta conserva su revisión y contenido original, y un reintento idéntico recupera la misma oferta.

#### Scenario: Valor no finito
- **WHEN** se propone `NaN` o infinito como precio o cantidad
- **THEN** la base rechaza el valor; un número finito y válido se conserva.

### Requirement: Presupuesto activo único
La persistencia SHALL permitir como máximo un presupuesto activo por proyecto y SHALL mantener líneas y referencias de oferta dentro del mismo proyecto.

#### Scenario: Segundo presupuesto activo
- **GIVEN** un proyecto con presupuesto activo
- **WHEN** se intenta activar otro presupuesto del mismo proyecto
- **THEN** la base rechaza la operación.

### Requirement: Directorios y datos por proyecto
La persistencia SHALL normalizar país, proveedor, sucursal y contacto privado; cliente, candidatura, evaluación y selección SHALL quedar delimitados por proyecto. Los servicios y observaciones de tarifas SHALL conservar su fuente y fecha sin definir cómo se calcula un presupuesto.

#### Scenario: Selección ajena
- **GIVEN** un candidato del proyecto B
- **WHEN** se intenta seleccionarlo en el proyecto A
- **THEN** la base rechaza la referencia cruzada.

### Requirement: Snapshot y auditoría
La persistencia SHALL conservar snapshots de propuesta como borradores inmutables y eventos de mutación sin alterar registros históricos ni copiar secretos o documentos comerciales completos al evento de auditoría. Un snapshot SHALL NOT conceder permiso para emitir una propuesta.

#### Scenario: Mutación con actor
- **GIVEN** una identidad validada y autorizada por proyecto
- **WHEN** se modifica un registro mutable
- **THEN** queda un evento con actor, proyecto, acción, recurso y hora.

#### Scenario: Borrador canónico
- **GIVEN** un presupuesto activo con revisión vigente
- **WHEN** el servicio captura un borrador
- **THEN** la base construye la proyección desde líneas y antecedentes fijados, la guarda inmutable y no concede emisión.
