# Contrato Angular provisional: `guided-bom.v1`

**Origen:** mismo origen por proxy de desarrollo; servidor backend local
`127.0.0.1:8002`. No exponer el puerto ni fusionar con la API productiva.

```http
GET /v1/demo/guided-bom?cable_count=6&cable_variant=thick
```

| Parámetro | Requerido | Valores exactos |
| --- | --- | --- |
| `cable_count` | Sí | `3`, `6` |
| `cable_variant` | Sí | `thick`, `slim`, `unknown` |
| `route_length` | No | `known` (default), `unknown` |

No pasar `store`, URLs, consultas, nombres de cliente o precios. Una clave
adicional, duplicada o inválida devuelve 422. El backend usa un store Relate
fijo y un único escenario sintético. Cargar `guided-bom.v1.example.json` como
fixture del componente; el GET `6/thick` devuelve el mismo objeto.

Campos de primer nivel, todos presentes: `wireVersion`, `scenarioId`,
`notice`, `assumptions[]`, `requirements[]`, `bom[]`, `candidates`,
`evidence`, `status`.

- `assumptions[]`: `{id, state, value}`; `state=inferred` nunca significa
  hecho confirmado.
- `requirements[]`: `{id, state, value, unit, evidenceId}`; `CABLE-OD`
  agrega `variant`. Con `unknown`, `value` y `evidenceId` son `null`.
- `bom[]`: `{itemId, family, quantity, unit, state, ruleId, evidenceIds}`;
  `state=draft`. Vacío si falta OD o longitud. No mostrarlo como compra.
- `candidates.emt[]`: `{itemId, family, diameter, innerDiameterIn, status,
  reasonCodes[], fill, evidencePaths[]}`. `fill` incluye
  `occupiedAreaFactorIn2`, `allowedAreaFactorIn2`, `fillPercent` y
  `eligible`; todos salvo `eligible` son cadenas decimales o `null`.
  `eligible` es booleano o `null`.
- `candidates.accessories[]`: `{itemId, family, diameter, status,
  reasonCodes[], evidencePaths[]}`. Las variantes de otro diámetro siguen
  visibles como incompatibles.
- `candidates.cameras[]`, `.cables[]`, `.connectivity[]`: opciones pendientes
  sin precio; `.switch[]` y `.enclosure[]` permanecen vacíos.
- `evidence.graphPaths[]`: `{nodes:[{id,type}], relations:[...], ruleId}`;
  cada ruta llega a un nodo `EVIDENCE`. Las rutas de candidatos muestran
  `FITS_DIAMETER` y `SUPPORTED_BY`. `fillCriterion` registra la fórmula y el
  umbral ilustrativo; `primarySources` contiene las fichas que se consultaron
  al preparar la fixture, sin fetch en ejecución.
- `status`: `{code, selectedDemoEmtId, compatibility, unknown[],
  professionalValidationRequired}`. `code=PENDING_REVIEW` siempre;
  `selectedDemoEmtId=null` y `compatibility=PENDING_OD` si falta OD.

Resultados de aceptación del GET: `3/thick → GEN-EMT-3-4`,
`6/thick → GEN-EMT-1-1-4`, `6/slim → GEN-EMT-1`.
`6/unknown → selectedDemoEmtId=null, bom=[]`.
`6/thick&route_length=unknown → GEN-EMT-1-1-4, bom=[]`.
La UI debe mostrar la tabla de `fillPercent` junto con los `reasonCodes` y
permitir abrir las rutas de `evidencePaths`; el porcentaje mostrado se redondea
solo después de la comparación exacta.
