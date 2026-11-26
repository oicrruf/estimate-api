# Spec Delta

## Purpose

Restringe cada lectura y escritura a la identidad autenticada y al proyecto autorizado, manteniendo los datos de otro tenant invisibles incluso cuando se conoce un identificador ajeno.

## ADDED Requirements

### Requirement: Acceso de mínimo privilegio
Las tablas de aplicación SHALL aplicar RLS y permisos de columna para que propietario, editor y lector obtengan únicamente las operaciones definidas para su proyecto.

#### Scenario: Lector intenta mutar
- **GIVEN** un lector de un proyecto
- **WHEN** intenta modificar una entidad o presupuesto
- **THEN** la base rechaza la mutación.

#### Scenario: Editor de proyecto ajeno
- **GIVEN** un editor del proyecto A sin membresía en B
- **WHEN** consulta o modifica registros de B
- **THEN** no obtiene datos de B ni puede modificarlos.

### Requirement: Identidad ausente o no confiable
La capa de datos SHALL rechazar por defecto operaciones de usuario sin identidad validada; un identificador declarado en el cuerpo del pedido SHALL NOT sustituir al sujeto del token validado.

#### Scenario: Sin sujeto
- **WHEN** se consulta la base como rol anónimo o con sujeto ausente
- **THEN** no se obtiene ningún registro de proyecto ni se acepta una mutación.

### Requirement: Límite del rol privilegiado
Las operaciones de usuario SHALL ejecutarse bajo contexto de identidad autenticada con RLS. El rol de servicio SHALL quedar reservado para migraciones o administración explícita y no para omitir autorización por recurso.

#### Scenario: Prueba local con identidad simulada
- **GIVEN** un PostgreSQL descartable que simula el contexto de Auth
- **WHEN** pasa una prueba de aislamiento
- **THEN** el resultado se informa como prueba de políticas SQL y no como verificación de JWT o de Supabase alojado.
