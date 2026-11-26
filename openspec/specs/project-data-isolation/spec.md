# project-data-isolation Specification

## Purpose

Restringe cada lectura y escritura a la identidad autenticada y al proyecto autorizado, manteniendo los datos de otro tenant invisibles incluso cuando se conoce un identificador ajeno.

## Requirements

### Requirement: Acceso de mínimo privilegio
Las tablas de aplicación SHALL aplicar RLS y permisos de columna para que propietario, editor y lector obtengan únicamente las operaciones definidas para su proyecto.

#### Scenario: Contactos privados
- **GIVEN** un usuario autenticado que puede leer el directorio de proveedores
- **WHEN** intenta leer contactos de sucursal o perfiles de cliente en el esquema privado
- **THEN** la base deniega el acceso directo.

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
Las operaciones de usuario SHALL ejecutarse bajo contexto de identidad autenticada con RLS. Los cambios comerciales SHALL pasar por un servicio transaccional con actor validado, autorización por recurso e idempotencia; la conexión de servicio SHALL recibir solo ejecución de funciones revisadas y ningún DML directo sobre las tablas comerciales.

#### Scenario: Cliente intenta escribir datos comerciales
- **GIVEN** un propietario o editor autenticado
- **WHEN** inserta directamente una oferta, línea, presupuesto, snapshot, entidad de evidencia o paquete
- **THEN** la base rechaza la escritura aunque el proyecto le pertenezca.

#### Scenario: Cliente intenta escribir proyecto o membresía
- **GIVEN** un propietario autenticado
- **WHEN** intenta insertar o actualizar directamente proyecto o membresía
- **THEN** la base deniega DML y exige los comandos de backend con actor, autorización e idempotencia.

#### Scenario: Servicio registra oferta
- **GIVEN** un actor validado por FastAPI con permiso de edición y una clave idempotente
- **WHEN** la conexión de servicio registra una oferta con evidencia y precio finito
- **THEN** la operación se autoriza por proyecto, audita y aumenta la revisión una sola vez; un reintento idéntico devuelve el mismo ID.

#### Scenario: Servicio selecciona candidato
- **GIVEN** un candidato y la evaluación aceptada más reciente con evidencia del mismo proyecto
- **WHEN** el backend registra selección con actor autorizado y clave idempotente
- **THEN** cambia solo ese candidato, conserva el historial y devuelve el mismo resultado en reintentos idénticos.

#### Scenario: Prueba local con identidad simulada
- **GIVEN** un PostgreSQL descartable que simula el contexto de Auth
- **WHEN** pasa una prueba de aislamiento
- **THEN** el resultado se informa como prueba de políticas SQL y no como verificación de JWT o de Supabase alojado.
