# Propuesta: corte guiado de BOM ficticia

## Why

Demostrar en una ruta local y sin proveedores cómo un cambio tipado de cantidad o diámetro exterior de UTP modifica la selección técnica preliminar de EMT y accesorios. Se mantiene separado del demo publicado con pin `46e97c16`.

## What Changes

El caso ficticio parte de tres cámaras Wi-Fi en un sitio sin red ni internet. El tramo con UTP es una opción de infraestructura independiente, no una dependencia asumida de esas cámaras. El grafo Relate conserva relaciones y procedencia; Python calcula ocupación con dimensiones y umbral ilustrativos declarados. AT-238 deriva cantidades; AT-239 recuerda que un enlace físico exige topología y pruebas; AT-246 conserva hechos inferidos, confirmados y desconocidos; AT-247 expande opciones, no aprueba compras. El agente ADK local ejecuta sólo herramientas fijas, sin LLM.

Fuera de alcance: norma de llenado, diseño eléctrico, compatibilidad real, precios, URLs comerciales, investigación de proveedores, API pública, UI, datos de clientes y despliegue.
