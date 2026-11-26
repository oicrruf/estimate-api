# AT-224: motor determinista de precios

## Why

La cotización necesita cálculos monetarios reproducibles que conserven tarifas y política explícitas. El motor no debe inferir impuestos ni repetir contingencias o IVA.

## What Changes

- Contratos tipados de moneda, importe, tratamiento tributario, contingencia, descuento, partida y resultado.
- Cálculo puro con `Decimal`, redondeo unitario antes de multiplicar cantidades y suma de líneas ya redondeadas.
- Estado pendiente cuando falta una tasa tributaria necesaria, en especial importación sin política completa.
- Pruebas de mano de obra, equipo con impuesto incluido, precio final, envío, descuento y entradas malformadas.

## Impact

Sólo el módulo independiente `estimate_api.pricing` y sus pruebas. No se integra con presupuestos, persistencia, IA, fuentes externas ni políticas fiscales reales.
