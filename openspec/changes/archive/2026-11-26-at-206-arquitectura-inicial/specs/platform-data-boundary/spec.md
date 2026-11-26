# Spec Delta

## Purpose

Establece dónde viven los datos y archivos del MVP y qué comportamiento deben conservar sus adaptadores aunque cambie el proveedor de infraestructura.

## ADDED Requirements

### Requirement: Fuente de verdad única
El sistema SHALL conservar catálogo, BOM, cantidades, propuestas y selección en la base de datos principal, y SHALL exponer edición mediante la API autenticada.

#### Scenario: Edición de cantidad
- **GIVEN** un usuario autorizado y una revisión vigente
- **WHEN** envía una edición de cantidad
- **THEN** la API persiste una única nueva revisión y devuelve su identificador.

### Requirement: Objetos comerciales privados
El sistema SHALL almacenar PDF y activos comerciales en almacenamiento privado y SHALL entregar descargas autorizadas con vencimiento limitado.

#### Scenario: Descarga autorizada
- **GIVEN** un usuario con acceso al proyecto
- **WHEN** pide descargar un PDF
- **THEN** recibe un acceso temporal limitado al objeto solicitado.

#### Scenario: Acceso directo ajeno
- **GIVEN** un usuario sin permiso sobre el proyecto
- **WHEN** intenta acceder al objeto o solicitar un enlace
- **THEN** se deniega el acceso.

### Requirement: Adaptadores de persistencia
El servicio SHALL usar contratos tipados para datos y archivos que conserven identidad del proyecto, errores y revisión al cambiar implementación de proveedor.

#### Scenario: Sustitución de proveedor
- **GIVEN** un adaptador alternativo que cumple el contrato
- **WHEN** se ejecuta la suite contractual
- **THEN** se obtienen los mismos resultados observables y controles de acceso.
