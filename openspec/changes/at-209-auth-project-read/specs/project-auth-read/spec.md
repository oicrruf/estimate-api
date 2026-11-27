# Spec Delta

## ADDED Requirements

### Requirement: Identidad verificada en lectura de proyectos
El backend SHALL aceptar solo un access token de Supabase Auth válido, derivar su usuario del `sub` verificado y SHALL NOT aceptar identidad de GitHub, cuerpo, query o sesión MCP como sustituto. El inicio de sesión del producto SHALL usar GitHub como proveedor OAuth único de Supabase Auth.

#### Scenario: Callback PKCE del cliente interactivo
- **GIVEN** una sesión de inicio de sesión GitHub iniciada por el cliente con PKCE y `redirectTo` exacto permitido
- **WHEN** Supabase Auth devuelve un código a la ruta callback del mismo navegador
- **THEN** el cliente intercambia ese código por una sesión Supabase, envía solo su access token a FastAPI y no concede acceso hasta recibir autorización interactiva del backend.

#### Scenario: Token válido
- **GIVEN** un JWT de acceso sintético firmado por una clave efímera del emisor esperado con audiencia, expiración y rol correctos
- **WHEN** se solicita una lectura de proyectos
- **THEN** el backend deriva el actor del token verificado y consulta solo proyectos visibles para él.

#### Scenario: Token ausente o no verificable
- **GIVEN** ausencia de Bearer, firma inválida, token vencido, usuario anónimo o emisor, audiencia o rol distintos
- **WHEN** se solicita una lectura de proyectos
- **THEN** la API responde 401 sin consultar datos del proyecto.

#### Scenario: JWKS temporalmente inaccesible
- **GIVEN** un Bearer presente y el servicio de claves inaccesible sin una clave válida en caché
- **WHEN** se solicita una lectura de proyectos
- **THEN** la API responde 503 sin exponer el token ni consultar datos del proyecto.

#### Scenario: Rotación de clave publicada con antelación
- **GIVEN** una clave asimétrica de reserva publicada en JWKS antes de su activación
- **WHEN** el backend actualiza su caché y recibe un token firmado por esa clave
- **THEN** verifica el token con esa clave; si el `kid` aún no está disponible, falla cerrado.

### Requirement: Lectura por membresía de proyecto
La API SHALL listar y leer proyectos únicamente si el actor está admitido al modo interactivo y es propietario o miembro actual. SHALL ejecutar el SELECT bajo `authenticated` y RLS de AT-208 en una transacción con identidad local a esa transacción; SHALL ocultar con 404 un proyecto ajeno.

#### Scenario: Login SQL demasiado privilegiado
- **GIVEN** una conexión de lectura configurada con un LOGIN superusuario, BYPASSRLS o herencia de privilegios
- **WHEN** la API intenta leer proyectos con un token válido
- **THEN** falla cerrado con 503 antes de consultar proyectos, sin aprovechar ese LOGIN para omitir RLS.

#### Scenario: JWT válido sin admisión
- **GIVEN** un usuario autenticado por Supabase Auth con JWT válido cuyo `sub` no figura en la allowlist del backend
- **WHEN** solicita lista o detalle de proyectos
- **THEN** la API responde 403 sin consultar proyectos, aunque su proveedor sea GitHub.

#### Scenario: Configuración de admisión ausente o inválida
- **GIVEN** una allowlist ausente o con formato inválido
- **WHEN** un usuario con JWT válido solicita proyectos
- **THEN** la API deniega por defecto con 403 si está ausente, o 503 si no puede interpretar la configuración; nunca amplía acceso.

#### Scenario: Propietario, editor y lector
- **GIVEN** un proyecto con un propietario, un editor y un lector sintéticos
- **WHEN** cada uno solicita lista o detalle con su identidad verificada
- **THEN** ve el proyecto y recibe su propio `access_role` sin datos comerciales privados.

#### Scenario: Proyecto ajeno
- **GIVEN** un usuario sin propiedad ni membresía en el proyecto
- **WHEN** solicita el detalle por UUID conocido
- **THEN** la API devuelve 404 y su lista no incluye ese proyecto.

#### Scenario: Estado de conexión reutilizada
- **GIVEN** dos peticiones consecutivas de usuarios distintos sobre la misma conexión del pool
- **WHEN** la primera termina y comienza la segunda
- **THEN** rol e identidad de la primera no afectan a la segunda.

### Requirement: Lista acotada y revocación vigente
La API SHALL ordenar la lista por ID, limitar cada página a 1–100 elementos y usar un cursor exclusivo. Cada petición SHALL consultar la membresía actual dentro de su propia transacción; un token aún válido SHALL NOT conservar acceso tras la revocación de membresía.

#### Scenario: Páginas y cambio de membresía
- **GIVEN** un propietario con más de un proyecto y un miembro con token vigente
- **WHEN** se solicita una página de tamaño uno y luego se revoca la membresía del otro usuario
- **THEN** el cursor continúa sin duplicados, y el usuario revocado recibe lista vacía y 404 en detalle con el mismo token.

### Requirement: Preview local autenticado con reserva acotada
La API SHALL mantener deshabilitado por defecto el preview interactivo. Cuando el servidor de pruebas configure un extractor inyectado y un almacén descartable, SHALL verificar JWT, allowlist y membresía con rol propietario/editor antes de la reserva; SHALL limitar reservas a 2 por actor, 4 por proyecto y 8 globales por hora en una transacción serializada, y SHALL NOT invocar extractor en peticiones no autorizadas, duplicadas o sin cuota.

#### Scenario: Solicitud sin acceso
- **GIVEN** un token ausente, inválido, no admitido, o un proyecto ajeno o revocado
- **WHEN** se solicita un preview con clave de idempotencia
- **THEN** responde 401, 403 o 404 según la frontera y no crea reserva ni llama al extractor.

#### Scenario: Reserva autorizada de prueba
- **GIVEN** un propietario/editor con cupo y un extractor sintético inyectado
- **WHEN** solicita un preview
- **THEN** crea una sola reserva y responde `scope-review-preview.v1` en estado `pending_review`, sin persistir propuesta ni habilitar uso comercial.

#### Scenario: Revocación antes del punto de reserva
- **GIVEN** una petición cuya comprobación inicial de proyecto pasó y una revocación o degradación de editor que confirma antes de la reserva
- **WHEN** la transacción de reserva vuelve a consultar membresía y rol
- **THEN** responde 404 o 403, no reserva cupo y no invoca el extractor.

#### Scenario: Recibo de reserva e idempotencia ante fallo
- **GIVEN** una reserva confirmada antes de invocar un extractor sintético
- **WHEN** el extractor completa o falla y se repite la misma clave
- **THEN** conserva el cupo y un recibo local; repite la respuesta completada o deniega el reintento pendiente/fallido, sin invocar otra vez el extractor.

#### Scenario: Misma clave con brief diferente
- **GIVEN** un recibo local confirmado para un actor, proyecto, clave y brief exacto
- **WHEN** el actor repite la clave con un brief diferente
- **THEN** responde 409, no reproduce la respuesta anterior, no consume otro cupo y no llama al extractor.

#### Scenario: Clave HTTP en blanco
- **GIVEN** un actor autorizado y una cabecera `Idempotency-Key` compuesta solo por espacios
- **WHEN** solicita el preview
- **THEN** la API responde 422 antes de reservar y no llama al extractor.

#### Scenario: Proyección sintética de ADK y Relate
- **GIVEN** una fixture local de inventario compartido y un extractor falso inyectado
- **WHEN** una cantidad de cámaras inequívoca pasa por el adaptador local
- **THEN** proyecta solo cantidad, pregunta fija, evidencia y disponibilidad a un borrador pendiente, sin precio, oferta, métricas o texto del modelo.

#### Scenario: Capacidad del adaptador antes de la cuota
- **GIVEN** un adaptador sintético con máximo 700 y la ruta HTTP existente con máximo 4000
- **WHEN** un propietario/editor envía 701 o 4000 caracteres
- **THEN** la transacción revalida primero el rol, responde 422 y no crea ni cambia recibos, cuota o llamadas al extractor.
- **WHEN** envía 4001 caracteres
- **THEN** la validación de esquema HTTP responde 422 sin reservar.
- **WHEN** un lector o usuario revocado envía 701 caracteres
- **THEN** responde 403 o 404 sin revelar detalles del adaptador.
