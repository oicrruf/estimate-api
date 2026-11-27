# Tareas AT-209 (corte mínimo)

- [x] Revisar ADR, entrada HTTP actual y SQL/RLS de AT-208; documentar contrato preliminar y fuentes.
- [x] Ensayar en PostgreSQL descartable la lectura como propietario, miembro y ajeno, más el cierre transaccional del rol y claim; registrar que el fixture no valida JWT.
- [x] Recibir criterios resumidos del hilo principal, integrar base AT-208 y fijar dependencias JWT/DB y lockfile; implementar firma y claims con claves sintéticas.
- [x] Implementar consultas parametrizadas de lista/detalle con transacción y rol de lectura, sin alterar la ruta de mutación AT-208.
- [x] Probar HTTP con JWT sintético, JWKS local y RLS con proyectos/usuarios descartables, negativos y limpieza transaccional; generar y verificar OpenAPI en la rama.
- [x] Probar paginación, revocación por membresía y separación de identidades en la entrada HTTP y PostgreSQL descartable.
- [x] Probar GoTrue oficial descartable con ES256/JWKS, JWT emitidos y la ruta HTTP/Postgres RLS, sin OAuth real.
- [x] Exigir allowlist backend de `sub` verificado para el modo interactivo; probar JWT válido rechazado, ausencia y configuración inválida con GoTrue y HTTP descartables.
- [ ] Contrastar texto completo Linear y obtener revisión independiente de seguridad y CI del SHA final.
- [ ] Coordinar el cambio exacto de contrato y ancla AT-280 en estimate-app antes de fusionar el OpenAPI nuevo a estimate-api/develop.
- [ ] Completar el CRUD, idempotencia y auditoría restantes de AT-209 antes de declarar Done.
- [ ] Sincronizar/archivar OpenSpec en el commit final de AT-209, abrir PR a `develop` y no cerrar issue antes del merge.
- [x] Ensayar el preview local HTTP completo con GoTrue/PostgreSQL descartables, cuotas 2/4/8, duplicado, revocación, carrera y extractor sintético; no montar proveedor real.
- [x] Ensayar con dos conexiones degradación y revocación antes de reserva, y recibos ante resultado, fallo del stub y fallo de escritura final, sin repetir extractor.
