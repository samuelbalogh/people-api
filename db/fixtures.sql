SELECT addNode('Bart Simpson');
SELECT addNode('Lisa Simpson');
SELECT addNode('Maggie Simpson');
SELECT addNode('Homer Simpson');
SELECT addNode('Marge Simpson');
SELECT addNode('Mr Burns');
SELECT addNode('Smithers');
SELECT addNode('Barney');
SELECT addNode('Moe');
SELECT addNode('Chief Wiggam');
SELECT addNode('Santas little helper');
SELECT addNode('Bobo');
SELECT addNode('Bobos creator');


SELECT addEdge('Homer Simpson', 'Bart Simpson', 'father of');
SELECT addEdge('Homer Simpson', 'Lisa Simpson', 'father of');
SELECT addEdge('Homer Simpson', 'Maggie Simpson', 'father of');
SELECT addEdge('Mr Burns', 'Homer Simpson', 'boss of');
SELECT addEdge('Mr Burns', 'Bobo', 'owner of');
SELECT addEdge('Bobos creator', 'Bobo', 'creator of');
SELECT addEdge('Bobo', 'Mr Burns', 'teddy bear of');
SELECT addEdge('Smithers', 'Mr Burns', 'assistant of');
SELECT addEdge('Homer Simpson', 'Barney', 'friend of');
SELECT addEdge('Homer Simpson', 'Moe', 'friend of');

SELECT addEdge('Marge Simpson', 'Homer Simpson', 'spouse of');

SELECT addEdge('Lisa Simpson', 'Bart Simpson', 'sibling');
SELECT addEdge('Lisa Simpson', 'Maggie Simpson', 'sibling');
SELECT addEdge('Santas little helper', 'Bart Simpson', 'dog of');


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

--- select paths up to 4 levels
WITH rel_ids AS (
    -- relationships
    SELECT n1.properties->>'name' AS name1, edges.label, n2.properties->>'name' name2 FROM nodes n1
     INNER JOIN edges
      ON n1.id = edges.tail_node
     INNER JOIN nodes n2
      ON n2.id = edges.head_node

      UNION

    SELECT n1.properties->>'name' AS name1, concat('1 / ', edges.label), n2.properties->>'name' name2 FROM nodes n1
     INNER JOIN edges
      ON n1.id = edges.head_node
     INNER JOIN nodes n2
      ON n2.id = edges.tail_node
  )
    SELECT 
      rel1.name1, rel1.label, rel1.name2, rel2.label, rel2.name2
    FROM rel_ids rel1
        LEFT JOIN 
          rel_ids AS rel2
        ON 
          rel1.name2 = rel2.name1 AND
          rel1.name1 != rel2.name2
     ORDER BY 1;


-- find all nodes which have a path to Homer
-- direction counts here
WITH RECURSIVE 
  knows_homer(id, n, path, cycle) AS (
    SELECT 
        id, 1, ARRAY[id], false
    FROM nodes WHERE properties->>'name' = 'Homer Simpson'

      UNION 

    SELECT 
      edges.tail_node, 
      n+1,
      path || edges.tail_node,
      edges.tail_node = ANY(path)
    FROM edges JOIN knows_homer ON edges.head_node = knows_homer.id
    WHERE NOT cycle
  ),
  knows_homer_details AS (
    SELECT nodes.properties->>'name' as name, knows_homer.* FROM nodes, knows_homer WHERE nodes.id = knows_homer.id LIMIT 100
  )
  SELECT name, MIN(n) distance, MIN(path) path FROM knows_homer_details GROUP BY 1 ORDER BY 2


-- find all nodes which have a path to Homer
-- direction does not count here
WITH RECURSIVE 
  knows_homer(id, n, path, cycle) AS (
    SELECT 
        id, 1, ARRAY[id], false
    FROM nodes WHERE properties->>'name' = 'Homer Simpson'

      UNION 

    SELECT 
      edges.tail_node, 
      n+1,
      path || edges.tail_node,
      edges.tail_node = ANY(path)
    FROM edges JOIN knows_homer ON edges.head_node = knows_homer.id
    WHERE NOT cycle
  ),
  knows_homer2(id, n, path, cycle) AS (
    SELECT 
        id, 1, ARRAY[id], false
    FROM nodes WHERE properties->>'name' = 'Homer Simpson'

      UNION 

    SELECT 
      edges.head_node, 
      n+1,
      path || edges.head_node,
      edges.head_node = ANY(path)
    FROM edges JOIN knows_homer2 ON edges.tail_node = knows_homer2.id
    WHERE NOT cycle
  ),
  knows_homer_details AS (
    SELECT nodes.properties->>'name' as name, n, path FROM nodes, knows_homer WHERE nodes.id = knows_homer.id LIMIT 100
  ),
  knows_homer_details2 AS (
    SELECT nodes.properties->>'name' as name, n, path FROM nodes, knows_homer2 WHERE nodes.id = knows_homer2.id LIMIT 100
  ),
  unioned AS (
    SELECT * FROM knows_homer_details UNION SELECT * FROM knows_homer_details2 ORDER BY n
  )
  SELECT name, MIN(n) levels, MIN(path) path FROM unioned GROUP BY 1 ORDER BY 2
  

-- select direct relationships (level 1)
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
