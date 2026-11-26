// DATOS FICTICIOS. Ejecutar cada sentencia por separado después de seed.cypher.

// Q1: switch barato excluido y alternativa positiva; 8 PoE + uplink distinto = 9 totales.
MATCH (r:REQUIREMENT {id:'REQ-SWITCH'})-[:REQUIRES]->(reqTotal:CAPABILITY {key:'totalPortsMin'})
MATCH (r)-[:REQUIRES]->(reqPoe:CAPABILITY {key:'poePortsMin'})
MATCH (r)-[:REQUIRES]->(reqBudget:CAPABILITY {key:'poeBudgetWMin'})
MATCH (r)-[:REQUIRES]->(reqUplink:CAPABILITY {key:'distinctUplinkPorts'})
MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT {kind:'switch'})
MATCH (p)-[:SUPPORTS]->(total:CAPABILITY {key:'totalPorts'})-[:SUPPORTED_BY]->(evTotal:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(poe:CAPABILITY {key:'poePorts'})-[:SUPPORTED_BY]->(evPoe:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(budget:CAPABILITY {key:'poeBudgetW'})-[:SUPPORTED_BY]->(evBudget:EVIDENCE)
OPTIONAL MATCH (p)-[bad:INCOMPATIBLE_WITH]->(r)
WITH r,p,o,total,poe,budget,evTotal,evPoe,evBudget,reqTotal,reqPoe,reqBudget,reqUplink,bad
RETURN r.id AS requirementId, p.id AS productId, o.id AS offerId, o.priceUsd AS fictitiousPriceUsd,
  CASE WHEN total.value >= reqTotal.value AND poe.value >= reqPoe.value AND budget.value >= reqBudget.value THEN 'COMPATIBLE' ELSE 'INCOMPATIBLE' END AS status,
  CASE WHEN bad IS NOT NULL THEN bad.reasonCode ELSE 'MEETS_SWITCH_REQUIREMENT' END AS reasonCode,
  reqPoe.value AS requiredPoePorts, reqUplink.value AS distinctUplinkPorts, reqTotal.value AS requiredTotalPorts,
  [{nodes:[r.id,reqTotal.id],relations:['REQUIRES']},
   {nodes:[p.id,total.id,evTotal.id],relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[p.id,poe.id,evPoe.id],relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[p.id,budget.id,evBudget.id],relations:['SUPPORTS','SUPPORTED_BY']}] +
  CASE WHEN bad IS NULL THEN [] ELSE [{nodes:[p.id,r.id],relations:['INCOMPATIBLE_WITH']}] END AS evidencePaths
ORDER BY fictitiousPriceUsd;

// Q2: las dos ofertas no duplican el pool físico.
MATCH (r:REQUIREMENT {id:'REQ-CAMERA'})
MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT {id:'CAM-POE'})
MATCH (p)-[:SUPPORTS]->(pool:CAPABILITY {key:'poolCapacity'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
WITH r,p,pool,ev,collect(o.id) AS offerIds,sum(o.quantity) AS listedQuantity
RETURN r.id AS requirementId,p.id AS productId,offerIds,r.quantity AS requestedQuantity,
  CASE WHEN listedQuantity < pool.value THEN listedQuantity ELSE pool.value END AS availableQuantity,
  CASE WHEN r.quantity <= pool.value AND r.quantity <= listedQuantity THEN 'COMPATIBLE' ELSE 'INSUFFICIENT_STOCK' END AS status,
  'SHARED_POOL_CAPACITY' AS reasonCode,
  [{nodes:[p.id,pool.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;

// Q3: control positivo independiente del pool, con cantidad 2; no cambia el seed.
MATCH (o:OFFER)-[:SELLS]->(p:PRODUCT {id:'CAM-POE'})
MATCH (p)-[:SUPPORTS]->(pool:CAPABILITY {key:'poolCapacity'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
WITH p,pool,ev,collect(o.id) AS offerIds,sum(o.quantity) AS listedQuantity
RETURN p.id AS productId,offerIds,2 AS requestedQuantity,
  CASE WHEN listedQuantity < pool.value THEN listedQuantity ELSE pool.value END AS availableQuantity,
  CASE WHEN 2 <= pool.value AND 2 <= listedQuantity THEN 'COMPATIBLE' ELSE 'INSUFFICIENT_STOCK' END AS status,
  [{nodes:[p.id,pool.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;

// Q4: dependencia oculta; el adaptador no tiene oferta.
MATCH (p:PRODUCT {id:'CAM-12V'})-[:REQUIRES_ACCESSORY]->(a:ACCESSORY)-[:SUPPORTED_BY]->(ev:EVIDENCE)
OPTIONAL MATCH (o:OFFER)-[:SELLS]->(a)
RETURN p.id AS productId,a.id AS accessoryId,collect(o.id) AS accessoryOfferIds,
  CASE WHEN count(o)=0 THEN 'MISSING_ACCESSORY_OFFER' ELSE 'ACCESSORY_AVAILABLE' END AS status,
  [{nodes:[p.id,a.id,ev.id],relations:['REQUIRES_ACCESSORY','SUPPORTED_BY']}] AS evidencePaths;

// Q5: la potencia de la cámara desconocida impide cerrar el presupuesto PoE.
MATCH (p:PRODUCT {id:'CAM-UNKNOWN'})
OPTIONAL MATCH (p)-[:SUPPORTS]->(draw:CAPABILITY {key:'drawW'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
RETURN p.id AS productId,draw.value AS drawW,
  CASE WHEN draw IS NULL THEN 'UNKNOWN' ELSE 'KNOWN' END AS status,
  CASE WHEN draw IS NULL THEN ['drawW'] ELSE [] END AS missingFields;

// Q6: cambio de ocho a doce puertos PoE; SW-16 sólo tiene ocho PoE.
MATCH (p:PRODUCT {id:'SW-16'})-[:SUPPORTS]->(poe:CAPABILITY {key:'poePorts'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
RETURN p.id AS productId,12 AS changedPoePortsMin,poe.value AS measuredPoePorts,
  CASE WHEN poe.value >= 12 THEN 'COMPATIBLE' ELSE 'INCOMPATIBLE' END AS status,
  [{nodes:[p.id,poe.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;

// Q7: segundo dominio, smoke test de reutilización del contrato.
MATCH (r:REQUIREMENT {id:'REQ-UPS-SMOKE'})-[:REQUIRES]->(required:CAPABILITY {key:'capacityVaMin'})
MATCH (p:PRODUCT {id:'UPS-1500'})-[:SUPPORTS]->(actual:CAPABILITY {key:'capacityVa'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
RETURN r.id AS requirementId,p.id AS productId,
  CASE WHEN actual.value >= required.value THEN 'COMPATIBLE' ELSE 'INCOMPATIBLE' END AS status,
  [{nodes:[r.id,required.id],relations:['REQUIRES']},
   {nodes:[p.id,actual.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;

// Q8: grabador, tercer requisito de red; evidencia técnica sin oferta.
MATCH (r:REQUIREMENT {id:'REQ-NVR'})-[:REQUIRES]->(required:CAPABILITY {key:'channelsMin'})
MATCH (p:PRODUCT {id:'NVR-8'})-[:SUPPORTS]->(actual:CAPABILITY {key:'channels'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
RETURN r.id AS requirementId,p.id AS productId,
  CASE WHEN actual.value >= required.value THEN 'TECHNICALLY_COMPATIBLE_NO_OFFER' ELSE 'INCOMPATIBLE' END AS status,
  [{nodes:[r.id,required.id],relations:['REQUIRES']},
   {nodes:[p.id,actual.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;

// Q9: cámara alternativa cumple técnica, pero no hay oferta adquirible.
MATCH (r:REQUIREMENT {id:'REQ-CAMERA'})-[:REQUIRES]->(resolution:CAPABILITY {key:'resolutionMpMin'})
MATCH (p:PRODUCT {id:'CAM-ALT'})-[:SUPPORTS]->(actual:CAPABILITY {key:'resolutionMp'})-[:SUPPORTED_BY]->(ev:EVIDENCE)
MATCH (p)-[:SUPPORTS]->(power:CAPABILITY {key:'power'})-[:SUPPORTED_BY]->(evPower:EVIDENCE)
OPTIONAL MATCH (o:OFFER)-[:SELLS]->(p)
WITH r,p,actual,resolution,power,ev,evPower,collect(o.id) AS offerIds
RETURN r.id AS requirementId,p.id AS productId,offerIds,
  CASE WHEN actual.value >= resolution.value AND power.value='PoE' AND size(offerIds)=0 THEN 'TECHNICALLY_COMPATIBLE_NO_OFFER' ELSE 'UNKNOWN' END AS status,
  [{nodes:[p.id,actual.id,ev.id],relations:['SUPPORTS','SUPPORTED_BY']},
   {nodes:[p.id,power.id,evPower.id],relations:['SUPPORTS','SUPPORTED_BY']}] AS evidencePaths;
