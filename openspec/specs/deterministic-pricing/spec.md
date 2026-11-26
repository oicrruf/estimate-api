# deterministic-pricing Specification

## Purpose

Calcular importes comerciales desde políticas declaradas y entradas monetarias exactas, sin inventar impuestos.

## Requirements

### Requirement: Aritmética monetaria determinista

El motor SHALL usar `Decimal`, SHALL rechazar valores no finitos y `float`, y SHALL redondear el precio unitario según moneda y política antes de multiplicar la cantidad. SHALL conservar insumos y componentes en la salida.

#### Scenario: Mano de obra ficticia
- **GIVEN** base 40.00, contingencia 5%, impuesto excluido 13%, moneda con dos decimales y tres unidades
- **WHEN** se evalúa la partida
- **THEN** el unitario es 47.46 y el total 142.38.

#### Scenario: Redondeo unitario
- **GIVEN** un importe unitario que requiere redondeo y varias unidades
- **WHEN** se calcula el total
- **THEN** el total multiplica el unitario redondeado, sin redondear sólo el agregado.

### Requirement: Tratamiento explícito de precios

El motor SHALL aplicar contingencia sólo una vez. SHALL evitar agregar impuesto a precios con impuesto incluido, y SHALL conservar como paso un precio final confirmado o un envío documentado. SHALL aplicar descuentos sólo cuando exista instrucción documentada.

#### Scenario: Equipo con impuesto incluido
- **GIVEN** equipo con precio 100.00 que ya incluye impuesto y contingencia 5%
- **WHEN** se evalúa la partida
- **THEN** el unitario es 105.00 y el impuesto agregado es cero.

#### Scenario: Envío documentado
- **GIVEN** un cargo de envío final documentado
- **WHEN** se evalúa
- **THEN** se conserva su importe sin recargo.

### Requirement: Política incompleta y moneda exacta

El motor SHALL dejar pendiente un importe con tasa tributaria necesaria ausente, sin crear un total final. SHALL rechazar importes o descuentos en otra moneda y tasas fuera del dominio permitido.

#### Scenario: Importación sin impuesto definido
- **GIVEN** una base de importación sin tasa tributaria aplicable
- **WHEN** se evalúa la partida o la cotización
- **THEN** el estado es `PENDING`, se identifica la tasa faltante y no se presenta total final.

#### Scenario: Monedas distintas
- **GIVEN** dos partidas con políticas de moneda diferentes
- **WHEN** se intenta sumar la cotización
- **THEN** se rechaza la operación sin conversión implícita.
