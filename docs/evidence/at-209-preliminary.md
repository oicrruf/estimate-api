# AT-209: corte local de autenticación y lectura

Fecha: 26/11/2026. Base `estimate-api/develop` `838834287a9a9fd002509925b5232e2222f78ab4`; rama local `feature/AT-209-auth-project-read-current`. Sin push, PR, despliegue, OAuth real, secretos ni acceso a Supabase alojado.

## Alcance probado

- `GET /projects` y `GET /projects/{project_id}` aceptan Bearer JWT Supabase con firma asimétrica `RS256` o `ES256`, `kid`, emisor/audiencia configurados, expiración, `iat`, rol `authenticated` y `sub` UUID y rechazo de `is_anonymous=true` o mal tipado. El backend ignora `user_metadata` y no usa el UUID del cliente como actor.
- Lista paginada: `limit` 1–100 (20 por defecto), cursor exclusivo UUID, orden de ID y `{items, next_cursor}`. Detalle ajeno o inexistente devuelve 404. JWKS tiene caché 600 s y cooldown de 30 s ante `kid` desconocido; falla cerrado.
- La admisión interactiva usa `ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS`, JSON de UUID de Supabase Auth administrado solo en backend. Un JWT válido sin admisión recibe 403; configuración ausente deniega por defecto e inválida falla 503. Esto no reemplaza RLS ni membresía. La prueba GoTrue confirma el rechazo antes de añadir el usuario a la allowlist.
- PostgreSQL abre una conexión de lectura por petición, verifica que el LOGIN sea `NOSUPERUSER NOINHERIT NOBYPASSRLS` (503 si no), asume `authenticated` con `SET LOCAL ROLE` y fija el `sub` verificado dentro de una transacción `READ ONLY READ COMMITTED`. RLS de AT-208 y filtro explícito devuelven solo proyectos del propietario o miembro actual. El mismo token deja de ver un proyecto al revocarse su membresía. Peticiones sucesivas de usuarios distintos no comparten rol ni identidad.
- Errores 401/403/404/422/503 son genéricos y no devuelven token o DSN. No se usa `service_role` ni se altera la vía mutadora AT-208.

## Comandos y resultados

```text
UV_CACHE_DIR=/workspace/scratch/at-209-current/.uv-cache uv run --no-sync pytest -q
→ 333 passed, 1 skipped, 73 warnings [dev + demo + private-ai instalados, sin llamadas a proveedores]
bash tests/at209/run_preliminary_read.sh
→ AT-209 preliminary owner/member/outsider RLS and transaction identity passed
→ 2 passed, 1 warning [HTTP con JWT RS256 sintéticos y PostgreSQL descartable]
bash tests/at209/run_official_auth.sh
→ Official disposable GoTrue -> FastAPI preview HTTP -> AT-208 RLS passed
uv run --no-sync ruff check . → All checks passed
uv run --no-sync ruff format --check . → 124 files already formatted
uv run --no-sync mypy src scripts tests → Success: no issues found in 92 source files
uv run --no-sync python scripts/openapi.py --check → OpenAPI matches
ci/at-206-docs/node_modules/.bin/openspec validate at-209-auth-project-read --strict → Change is valid
uv run --no-sync python scripts/check_secrets.py → No potential secrets detected
uv 0.7.6 lock --check → Resolved 133 packages
```

El primer script también comprueba que un DSN de superusuario falle cerrado con 503 y que el verificador rechace el indicador anónimo. El primer script usa `postgres:17-alpine` descartable, puerto aleatorio solo en `127.0.0.1`, cinco usuarios y tres proyectos ficticios. Aplica migración AT-208, prueba propietario, editor, lector, ajeno, paginación y revocación, y destruye el contenedor. TestClient usa JWKS HTTP y claves efímeras; los tests cubren firma, emisor, audiencia, expiración, rol, sujeto, rotación y servicio de claves inaccesible.

El segundo script usa Supabase CLI **3.4.0** para generar una clave ES256 efímera, GoTrue oficial **v2.198.0** (`ghcr.io/supabase/gotrue@sha256:ba8c0c82c574756c835c696df2a2c698020cc408a42034013d3712e34de7964d`) y PostgreSQL **17-alpine** (`postgres@sha256:f9cf3e1f0066f0eb0c48707d864f0ac5941e9ff454a072077d97a4d278d07d73`). GoTrue crea `auth.users` y su `auth.uid()` real. El fixture solo aprovisiona roles aislados y grants para instalar AT-208. GoTrue emite dos tokens ES256 por signup de usuarios sintéticos `.invalid`; FastAPI consulta su JWKS oficial, valida tokens y usa RLS para propietario y miembro. La prueba comprueba 401 sin token o con token inválido, 403 con token oficial válido antes de admitir al usuario, lista vacía y detalle 404 para admitido sin membresía, concesión/revocación de membresía, 404 tras revocación y alternancia de identidades mediante TestClient. Además levanta Uvicorn en loopback y comprueba por socket HTTP 401 sin Bearer y 200 con el token oficial del propietario. Las claves/contraseñas son efímeras, archivo de entorno `0600`, contenedores y red se eliminan al salir. No se imprimen tokens ni claves.

La pila completa `supabase start` se intentó con CLI 3.4.0, pero la descarga de la imagen PostgreSQL agotó el espacio disponible del overlay (466 MB libres durante la descarga); se canceló el proceso y Docker recuperó el espacio temporal. La prueba independiente con GoTrue oficial y PostgreSQL descartable cubre el flujo JWT/JWKS/HTTP/RLS, pero no demuestra una pila Supabase CLI completa, GitHub OAuth, pooler ni permisos alojados.

Para reproducir, instalar la CLI fijada con `npm install --prefix /tmp/at209-supabase-cli supabase@3.4.0` y ejecutar el script. Usa las imágenes fijadas indicadas arriba; los puertos son loopback. La prueba requiere que 55424 esté libre.

## Transición exacta AT-280/AT-209

OpenAPI de esta rama: SHA256 `a198c8b7509d2af89fcb1b5f7c7623deb06d9a67a59864a781a1416f30884735`. `estimate-app/develop` `d24ca275ce15758ebd687d26f2e87eb5c174798a` conserva el contrato anterior SHA256 `2e1936350479446e779b01024755738d77e1d0d29bc2f376fcbd897d6ae0873a` y su ancla `APPROVED_SHA=6ecc9a9c5d6ba6355e3332f8b6533c81ed878b74`; el generador Angular solo acepta `/health`.

Secuencia propuesta antes de integrar API: (1) aprobar hash y SHA completos de ambas versiones; (2) en AT-280, adaptar el generador Angular para emitir proyecciones tipadas de ambas versiones y hacer que el verificador reconozca solo pares versión/hash aprobados, sin ejecutar contratos ni admitir deriva arbitraria; (3) aprobar una ventana transitoria explícita para API nueva y copia app anterior con ambos CI verdes; (4) integrar API, actualizar copia/cliente/ancla en app al SHA fusionado y retirar el par transitorio. La actualización frontend **no está hecha**. Si el gate no permite una ventana estricta, coordinar integración atómica entre repos antes de fusionar la API.

## Interfaz OAuth propuesta (sin implementación frontend)

Para AT-280: botón interactivo inicia `signInWithOAuth` con `provider: github`, `flowType: pkce`, `redirectTo` exacto `<origen-app>/auth/callback` y scopes de perfil/email, ninguno de repositorios. El callback GitHub OAuth App apunta a Supabase Auth `/auth/v1/callback`; la URL de retorno Supabase apunta al frontend y debe figurar exactamente en la allowlist de redirecciones. Angular intercambia `code` una sola vez en el mismo navegador, limpia la URL y presenta la sesión a FastAPI. La API valida el JWT y la allowlist; 403 muestra acceso denegado. La ruta callback, la configuración GitHub OAuth y la restricción del proveedor a GitHub no están implementadas aquí. El modo público técnico offline permanece separado.

La integración local preserva la dependencia `private-ai` y las piezas AT-211 presentes en `develop`; `docs/at-209-at-211-boundary.md` define el gate reutilizable de proyecto y el límite transaccional previo a cualquier gasto.

## Preview HTTP local descartable

`POST /v1/projects/{projectId}/scope-review-preview` acepta `{brief}` de 1..4000 caracteres y `Idempotency-Key`. La ruta de producto permanece 503 sin extractor inyectado. `bash tests/at209/run_official_auth.sh` monta únicamente el stub de `tests.at209.preview_server` sobre GoTrue/PostgreSQL descartables. Por HTTP normal comprueba 401 sin token o con token inválido; 403 para no admitido y miembro lector; 404 tras revocación o proyecto ajeno; 422 para brief vacío o excesivo; 200 para el propietario/editor, con `scope-review-preview.v1` pendiente, no persistido ni comercial; 200 repetido para clave completada y 409 para pendiente/fallida; 429 en límites 2/actor, 4/proyecto, 8/global y una carrera contra el último cupo; 503 por tabla de reservas ausente. Una sola reserva se inserta para la solicitud repetida y ningún caso denegado llama al stub. La tabla `private.preview_reservations` existe solo en el fixture local; no hay migración ni proveedor real.

Regresión concurrente adicional: una conexión retiene el bloqueo de reserva mientras el HTTP pasa la lectura inicial; otra degrada al editor a lector o revoca su membresía, confirma y libera el bloqueo. La lectura transaccional posterior devuelve 403/404, cero reservas y cero invocaciones del stub. Una clave exitosa repite su respuesta desde el recibo sin segunda invocación; un fallo sintético del stub deja `failed` y un fallo sintético de escritura final deja `pending`. Ambos ocupan cupo y su repetición responde 409 sin nueva llamada. No hay transacción de base abierta durante el stub. La revocación posterior a la lectura de rol aún puede adelantarse a una llamada externa: queda como límite de un futuro protocolo pagado, no como garantía de este corte local.

## Gates restantes

El hilo principal consultó Linear: AT-209 completo exige además CRUD de proyectos, clientes, requisitos, catálogo y proveedores/contactos, idempotencia, auditoría y OpenAPI. Este corte no cumple Done. Faltan revisión independiente del SHA final, CI de la rama, coordinación AT-280, pruebas de OAuth GitHub y rol real/pooler del entorno final. La CLI Linear de este entorno respondió `Unknown tool`; el texto íntegro no estuvo disponible aquí.

Fuentes: [GitHub sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-github), [PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow), [redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls), [changelog Supabase](https://supabase.com/changelog.md), [JWT/JWKS](https://supabase.com/docs/guides/auth/jwts), [signing keys](https://supabase.com/docs/guides/auth/signing-keys), [desarrollo local](https://supabase.com/docs/guides/local-development), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [compose oficial](https://github.com/supabase/supabase/blob/master/docker/docker-compose.yml).
