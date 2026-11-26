// Solo tipos genéricos ficticios 1¼; datos dimensionales están en fixture.json.
MERGE (n:SPEC {id:'SPEC-DIAMETER-1-1-4'}) SET n.diameter = '1 1/4';
MERGE (n:MATERIAL {id:'GEN-EMT-1-1-4'}) SET n.family = 'emt', n.kind = 'generic_type';
MERGE (n:EVIDENCE {id:'EV-GUIDED-CAT-EMT-1-1-4'}) SET n.kind = 'synthetic_catalog_record';
MATCH (i:MATERIAL {id:'GEN-EMT-1-1-4'}), (d:SPEC {id:'SPEC-DIAMETER-1-1-4'}) MERGE (i)-[:FITS_DIAMETER {ruleId:'GUIDED-DIAMETER'}]->(d);
MATCH (i:MATERIAL {id:'GEN-EMT-1-1-4'}), (e:EVIDENCE {id:'EV-GUIDED-CAT-EMT-1-1-4'}) MERGE (i)-[:SUPPORTED_BY {ruleId:'GUIDED-CATALOG'}]->(e);
MERGE (n:ACCESSORY {id:'GEN-COUPLING-1-1-4'}) SET n.family = 'coupling', n.kind = 'generic_type';
MERGE (n:EVIDENCE {id:'EV-GUIDED-CAT-COUPLING-1-1-4'}) SET n.kind = 'synthetic_catalog_record';
MATCH (i:ACCESSORY {id:'GEN-COUPLING-1-1-4'}), (d:SPEC {id:'SPEC-DIAMETER-1-1-4'}) MERGE (i)-[:FITS_DIAMETER {ruleId:'GUIDED-DIAMETER'}]->(d);
MATCH (i:ACCESSORY {id:'GEN-COUPLING-1-1-4'}), (e:EVIDENCE {id:'EV-GUIDED-CAT-COUPLING-1-1-4'}) MERGE (i)-[:SUPPORTED_BY {ruleId:'GUIDED-CATALOG'}]->(e);
MERGE (n:ACCESSORY {id:'GEN-CONNECTOR-1-1-4'}) SET n.family = 'connector', n.kind = 'generic_type';
MERGE (n:EVIDENCE {id:'EV-GUIDED-CAT-CONNECTOR-1-1-4'}) SET n.kind = 'synthetic_catalog_record';
MATCH (i:ACCESSORY {id:'GEN-CONNECTOR-1-1-4'}), (d:SPEC {id:'SPEC-DIAMETER-1-1-4'}) MERGE (i)-[:FITS_DIAMETER {ruleId:'GUIDED-DIAMETER'}]->(d);
MATCH (i:ACCESSORY {id:'GEN-CONNECTOR-1-1-4'}), (e:EVIDENCE {id:'EV-GUIDED-CAT-CONNECTOR-1-1-4'}) MERGE (i)-[:SUPPORTED_BY {ruleId:'GUIDED-CATALOG'}]->(e);
MERGE (n:ACCESSORY {id:'GEN-SUPPORT-1-1-4'}) SET n.family = 'support', n.kind = 'generic_type';
MERGE (n:EVIDENCE {id:'EV-GUIDED-CAT-SUPPORT-1-1-4'}) SET n.kind = 'synthetic_catalog_record';
MATCH (i:ACCESSORY {id:'GEN-SUPPORT-1-1-4'}), (d:SPEC {id:'SPEC-DIAMETER-1-1-4'}) MERGE (i)-[:FITS_DIAMETER {ruleId:'GUIDED-DIAMETER'}]->(d);
MATCH (i:ACCESSORY {id:'GEN-SUPPORT-1-1-4'}), (e:EVIDENCE {id:'EV-GUIDED-CAT-SUPPORT-1-1-4'}) MERGE (i)-[:SUPPORTED_BY {ruleId:'GUIDED-CATALOG'}]->(e);
