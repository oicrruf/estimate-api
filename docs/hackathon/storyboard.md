# Storyboard P0 — demo con datos ficticios

**Aviso visible:** Todos los productos, precios, proveedores e inventarios de esta demo son ficticios. No se usan clientes ni datos privados.

Tiempo objetivo: 5 minutos. Se preparan los ocho casos; se presentan Q1–Q5 y se usa Q6–Q8 como cierre o respaldo.

1. **Necesidad.** Ocho cámaras PoE, uplink dedicado, cuatro unidades de cámara y grabación de cuatro canales. Mostrar las tres necesidades y los atributos obligatorios.
2. **La oferta barata falla (Q1).** `SW-8` cuesta USD 80 ficticios, tiene ocho puertos totales. La ruta `SW-8 → totalPorts:8 → EV-SW8` explica por qué faltaría el noveno puerto del uplink. `INCOMPATIBLE`.
3. **Alternativa técnica (Q1).** `SW-16` cuesta USD 160 ficticios, tiene 16 puertos totales, ocho PoE y 150 W. Las tres rutas terminan en `EV-SW16`. `COMPATIBLE` para el requisito original.
4. **La disponibilidad falla aparte (Q2 y Q3).** Dos ofertas de `CAM-POE` muestran dos unidades cada una, pero ambas referencian `POOL-CAM-POE`: capacidad conjunta dos. Cuatro solicitadas → `INSUFFICIENT_STOCK`; dos solicitadas → `COMPATIBLE`. El control positivo no modifica los datos.
5. **Dependencia oculta (Q4).** `CAM-12V` requiere `AD-12V`, que no tiene oferta. Mostrar la relación `REQUIRES_ACCESSORY` y `MISSING_ACCESSORY_OFFER`. `CAM-ALT` es técnicamente viable en PoE y 4 MP, pero carece de oferta: no fingir que puede comprarse.
6. **Dato insuficiente (Q5).** `CAM-UNKNOWN` no declara `drawW`; la potencia no se adivina. `UNKNOWN` con `missingFields:["drawW"]`.
7. **Cambio de requisito (Q6).** Subir los puertos PoE a doce. `SW-16` pasa a `INCOMPATIBLE` porque sólo ocho son PoE.
8. **Generalización acotada (Q7) y grabador (Q8).** La misma forma de ruta sirve para un UPS de 1500 VA frente a 1000 VA. `NVR-8` satisface técnicamente cuatro canales, pero no tiene oferta. No extender la demo a un motor general de compras.

La interfaz propuesta muestra: requisito, producto/oferta, estado, razones, cantidad solicitada/disponible y rutas expandibles. Nunca presenta precio como sustituto de compatibilidad.
