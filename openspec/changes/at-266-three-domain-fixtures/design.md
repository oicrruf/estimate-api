# Design

## Context

El núcleo `ProjectDocument` ya admite los tres dominios. El registro `Registry` decide cobertura, pero no ejecuta reglas. AT-240 implementará el descubrimiento de alcance en otra rama.

## Decisions

1. Cada caso declara `projectFile`, categoría, jurisdicción, ámbito, semilla de cantidad y reglas ficticias con `packageId`, disparador, salida, factor, unidad y modo (`per_unit` o `fixed`). El arnés expone `DiscoveryInput` con `ProjectDocument` y `Registry` validados para facilitar una adaptación posterior a AT-240.
2. Un registro separado contiene tres paquetes no verificados, uno por dominio, con fuente sintética y límites expresos. La coincidencia exige namespace/version del proyecto y categoría, jurisdicción y ámbito exactos del paquete. Cada regla de caso debe corresponder a una declaración de catálogo.
3. El arnés de pruebas recorre la misma lógica genérica para todos los casos. Las cantidades son hipótesis explícitas del fixture; una partida nueva representa un faltante respecto de la semilla, no una recomendación profesional.
4. Cambiar la cantidad semilla vuelve a calcular todas las salidas. Pruebas negativas bloquean reglas de otro dominio, salida no declarada y versión incompatible. La cobertura permanece `pending_specialist` porque los paquetes no están verificados.

## Risks / Trade-offs

- La simulación no prueba el pipeline real de AT-240; queda pendiente conectar ese consumidor una vez integrado y repetir las mismas aserciones allí.
- La fórmula de factor y las unidades no modelan conversiones ni dimensionamiento técnico; sirven exclusivamente para comprobar propagación determinista.
