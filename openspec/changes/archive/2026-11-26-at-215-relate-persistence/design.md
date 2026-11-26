# Diseño AT-215

`catalog.json` simula un snapshot SQL. `spike.py` lo convierte en nodos/aristas con IDs estables mediante Cypher y produce consultas de capacidades, compatibilidad, alternativas, requisitos, evidencias y candidatos. `container_probe.py` ejecuta una fase por contenedor contra volúmenes nombrados: construcción, verificación y restauración. La imagen fija Python 3.12.14 por digest y `relate-db` 1.3.0 por SHA-256 de wheel. La instalación de la wheel dentro de la imagen es sin índice; Compose deshabilita la red durante la ejecución.

El respaldo se copia después de cerrar la conexión, a otro volumen local. Esto no representa respaldo fuera de host. Los procesos de prueba son efímeros y el gate limpia los volúmenes creados. El runtime no implementa mutaciones de negocio: autorización, idempotencia, auditoría y resolución de conflictos siguen en el límite SQL/API establecido por AT-206.
