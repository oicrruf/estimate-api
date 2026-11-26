# Private guided AI

## ADDED Requirements

### Requirement: Transporte privado acotado

Las CLI SHALL usar `gpt-6-luna` por defecto, Responses con
`reasoning.effort=none`, salida estructurada, `store=false`, máximo 500 tokens
de salida, timeout de 15 segundos y cero reintentos. Un modelo alternativo
SHALL requerir configuración explícita y no habrá fallback automático.

#### Scenario: Respuesta completa

- **WHEN** el SDK devuelve HTTP 200 y una respuesta tipada completa
- **THEN** el adaptador SHALL analizar `parse()` sin leer `raw.json()` y
  registrar sólo estado HTTP y contadores de tokens si existen

#### Scenario: Respuesta inválida

- **WHEN** falta la clave, la respuesta está incompleta o excede límites
- **THEN** el modo SHALL fallar cerrado sin exponer descripción o cuerpo

### Requirement: Cantidad de cámaras y stock compartido

La entrada privada de cámaras SHALL admitir únicamente cantidad inequívoca
de dos o cuatro respaldada en el texto, y SHALL usar Relate en modo lectura
con consulta fija para evaluar el pool común.

#### Scenario: Cuatro cámaras

- **WHEN** el texto sintético solicita cuatro cámaras
- **THEN** el resultado SHALL indicar dos disponibles, stock insuficiente y
  rutas de evidencia reales del producto y pool

#### Scenario: Dos cámaras

- **WHEN** el texto sintético solicita dos cámaras
- **THEN** el resultado SHALL indicar `CAM-POE` compatible y dos disponibles

#### Scenario: Cantidad ambigua

- **WHEN** falta una cantidad inequívoca de cámaras
- **THEN** el agente SHALL preguntar por ella y no llamar a Relate ni calcular stock

### Requirement: BOM guiada separada

El GET guiado determinista SHALL permanecer separado de la extracción privada
y la extracción de UTP SHALL aceptar sólo cantidades y mediciones completas
con unidades explícitas que coincidan con la fixture. SHALL rechazar valores
incompatibles o contradictorios antes de llamar al grafo.

#### Scenario: Mediciones completas

- **WHEN** una descripción ES/EN contiene seis UTP, OD 0.278 in y tramos de
  2 m y 1.5 m, con números y unidades completos
- **THEN** el corte SHALL invocar Relate y producir una evaluación preliminar

#### Scenario: Subcadenas o unidades incompatibles

- **WHEN** el texto contiene 12 m y 11.5 m, OD 0.278 mm u otra medición fuera
  del fixture, aunque incluya como subcadena 2 m o 0.278
- **THEN** el corte SHALL fallar antes de usar Relate o generar cantidades

#### Scenario: Afirmaciones contradictorias

- **WHEN** el texto mezcla cantidades UTP u OD incompatibles
- **THEN** el corte SHALL fallar antes de usar Relate

#### Scenario: Falta OD o longitud

- **WHEN** la descripción omite OD o longitud del tramo
- **THEN** el corte SHALL dejar pendientes las conclusiones o cantidades
  correspondientes y no inventar precio ni compatibilidad; sin OD o cantidad
  UTP SHALL omitir la consulta de grafo
