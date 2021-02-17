DROP FUNCTION addNode;
CREATE OR REPLACE FUNCTION addNode(name text) RETURNS void AS $$
  BEGIN
    INSERT INTO nodes(properties) VALUES (json_build_object('name', name));
  END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION addEdge(from_name text, to_name text, label text) RETURNS void AS $$
  BEGIN
    INSERT INTO edges(tail_node, head_node, label) SELECT 
      (SELECT id FROM nodes WHERE (properties->>'name')::text = from_name) as tail_node,
      (SELECT id FROM nodes WHERE (properties->>'name')::text = to_name) as head_node,
       (SELECT label as label)
     FROM nodes WHERE properties->>'name' = from_name;
  END;
$$ LANGUAGE plpgsql;


DROP FUNCTION hasEdge;
CREATE OR REPLACE FUNCTION hasEdge(from_name text, to_name text) RETURNS int AS $$
  DECLARE
    has_edge int = 0;
  BEGIN
    WITH matched_nodes AS (
      SELECT array_agg(id) as node_ids FROM nodes WHERE
        (properties->>'name')::text = from_name OR 
        (properties->>'name')::text = to_name
    )
    SELECT COUNT(*) INTO has_edge FROM edges, matched_nodes WHERE 
    (
       edges.tail_node = matched_nodes.node_ids[1] AND
       edges.head_node = matched_nodes.node_ids[2]
    OR
      (
       tail_node = node_ids[2] AND
       head_node = node_ids[1]
    );
    RETURN has_edge;
  END;
$$ LANGUAGE plpgsql;

DROP FUNCTION hasEdgeWithLabel;
CREATE OR REPLACE FUNCTION hasEdgeWithLabel(from_name text, to_name text, label_name text) RETURNS int AS $$
  DECLARE
    has_edge int = 0;
  BEGIN
    WITH matched_nodes AS (
      SELECT array_agg(id) as node_ids FROM nodes WHERE
        (properties->>'name')::text = from_name OR 
        (properties->>'name')::text = to_name
    )
    SELECT COUNT(*) INTO has_edge FROM edges, matched_nodes WHERE 
    (
       tail_node = node_ids[1] AND
       head_node = node_ids[2] AND
       edges.label = label_name
      )
    OR
      (
       tail_node = node_ids[2] AND
       head_node = node_ids[1] AND
       edges.label = label_name
    );
    RETURN has_edge;
  END;
$$ LANGUAGE plpgsql;


