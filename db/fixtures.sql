SELECT addNode('Bart Simpson');
SELECT addNode('Lisa Simpson');
SELECT addNode('Maggie Simpson');
SELECT addNode('Homer Simpson');
SELECT addNode('Marge Simpson');
SELECT addNode('Mr Burns');
SELECT addNode('Smithers');
SELECT addNode('Barney');

SELECT addEdge('Homer Simpson', 'Bart Simpson', 'father of');
SELECT addEdge('Mr Burns', 'Homer Simpson', 'boss of');
SELECT addEdge('Smithers', 'Mr Burns', 'assistant of');

SELECT addEdge('Lisa Simpson', 'Bart Simpson', 'sibling');
SELECT addEdge('Lisa Simpson', 'Maggie Simpson', 'sibling');


WITH siblings AS (
  SELECT tail_node, head_node FROM edges WHERE label = 'sibling'
), 
  sibling_ids AS (
    SELECT DISTINCT nodes.id, properties->>'name' AS name FROM nodes, siblings 
      WHERE (nodes.id = siblings.head_node) OR 
      (nodes.id = siblings.tail_node)) 
    SELECT 
     addEdge(sib1.name, sib3.name, 'sibling') 
    FROM sibling_ids sib1 
      CROSS JOIN 
        sibling_ids AS sib2 
      CROSS JOIN 
        sibling_ids AS sib3
    WHERE 
      hasEdgeWithLabel(sib1.name, sib2.name, 'sibling') = 1 AND
      hasEdgeWithLabel(sib2.name, sib3.name, 'sibling') = 1 AND
      hasEdgeWithLabel(sib1.name, sib3.name, 'sibling') = 0 AND
      sib1.name != sib2.name AND
      sib2.name != sib3.name AND
      sib1.name != sib3.name


WITH rel_ids AS (
    -- relationships
    SELECT nodes.id, nodes.properties->>'name' AS name, edges.label FROM nodes
     LEFT JOIN edges
     ON 
      nodes.id = edges.tail_node
  )
    SELECT 
      rel1.name, rel1.label, rel2.name, rel2.label, rel3.name
    FROM rel_ids rel1
      CROSS JOIN 
        rel_ids AS rel2
      CROSS JOIN 
        rel_ids AS rel3
    WHERE 
      hasEdge(rel1.name, rel2.name) = 1 AND
      hasEdge(rel2.name, rel3.name) = 1 AND
      hasEdge(rel1.name, rel3.name) = 0 AND
      rel1.name != rel2.name AND
      rel2.name != rel3.name AND
      rel1.name != rel3.name;

-- select relationships
WITH rels AS (
  SELECT tail_node, head_node, label FROM edges
)
SELECT 
  n1.properties->>'name' as name1, 
  n2.properties->>'name' as name2, 
  rels.label AS relationship 
FROM nodes n1 CROSS JOIN 
  nodes n2 
INNER JOIN rels ON 
  rels.tail_node = n1.id AND rels.head_node = n2.id;
