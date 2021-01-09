CREATE TABLE IF NOT EXISTS nodes(
  id UUID PRIMARY KEY UNIQUE DEFAULT uuid_generate_v4(),
  properties JSON
);

CREATE TABLE IF NOT EXISTS edges(
  id UUID PRIMARY KEY UNIQUE DEFAULT uuid_generate_v4(),
  tail_node UUID REFERENCES nodes(id) ON DELETE CASCADE NOT NULL,
  head_node UUID REFERENCES nodes(id) ON DELETE CASCADE NOT NULL,
  label TEXT,
  properties JSON
);

CREATE INDEX edges_tails ON edges (tail_node);
CREATE INDEX edges_heads ON edges (head_node);
