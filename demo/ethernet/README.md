# AT-239 · Enlaces Ethernet sintéticos

La fixture es ficticia y publicable. `src/estimate_api/ethernet/evaluate.py` consume
`catalog` y `topology` de `fixture.json` y devuelve enlaces requeridos, cantidades
medidas, incompatibilidades y verificaciones pendientes. No usa precios.

```bash
python3 demo/ethernet/build_seed.py
.venv/bin/pytest tests/test_ethernet.py -q
```

El seed `seed.cypher` se carga en un archivo Relate temporal dentro de las pruebas;
`MERGE` conserva datos ajenos. Las rutas con `pathwayId` referencian una canalización
genérica. El contrato de integración con AT-238 es `pathwayId` más segmentos medidos;
este paquete no calcula EMT ni presume capacidad de ducto. AT-240 puede consumir
`links`, `materials`, `pending` e `incompatible` para proponer alcance, sin convertir
esas líneas automáticamente en una BOM aprobada o cotizada.

La medida de ejemplo de CAM-1 suma 12 + 8 m, 1 m de holgura en cada extremo y 5 %
de desperdicio: 23,10 m requeridos. El resto de enlaces conserva longitud desconocida.
Los rollos son una asignación determinista de cortes individuales; el sobrante es
potencialmente recuperable, sujeto a revisión de instalación.
Cada enlace punto a punto acepta un cable y un par de puertos; los cables paralelos
requieren enlaces y asignaciones de puertos separados.
