# People API

Backend for the **Hackathon** project written on the 9th January 2021. 

## Concept

The idea was to write an app to list friends and note some details about them, like when we talked last time, and how their kids are called (I always forget their names), and who their acquaintances are - the last requirement basically makes this a **super-simple social network**.

## Why Postgres?

I wanted to use Postgres as a graph database (a bad idea in production) because I wanted to see how terrible it could be to shoehorn a graph use-case into a relational database. I think overall for a simple use-case like this, it works surprisingly well. 
There are some complicated-looking CTEs that I use for querying the data, but honestly it's not that bad.

The data structure is based on two tables: `nodes` and `edges` (it's how Martin Kleppman described in the [DDIA book](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/)).

**Nodes** are currently only **people**, but they could be anything, like hobbies or places. For simplicity's sake, I'm storing places and hobbies as properties, not as nodes, so they are not first-class citizens in this model.
**Edges** are relationships between people. They point from `node A` to `node B` and they have a label, like `friend`.


```
people-api=# \d nodes
                     Table "public.nodes"
   Column   | Type | Collation | Nullable |      Default       
------------+------+-----------+----------+--------------------
 id         | uuid |           | not null | uuid_generate_v4()
 properties | json |           |          | 
Indexes:
    "nodes_pkey" PRIMARY KEY, btree (id)
Referenced by:
    TABLE "edges" CONSTRAINT "edges_head_node_fkey" FOREIGN KEY (head_node) REFERENCES nodes(id) ON DELETE CASCADE
    TABLE "edges" CONSTRAINT "edges_tail_node_fkey" FOREIGN KEY (tail_node) REFERENCES nodes(id) ON DELETE CASCADE
```

```
people-api=# \d edges
                     Table "public.edges"
   Column   | Type | Collation | Nullable |      Default       
------------+------+-----------+----------+--------------------
 id         | uuid |           | not null | uuid_generate_v4()
 tail_node  | uuid |           | not null | 
 head_node  | uuid |           | not null | 
 label      | text |           |          | 
 properties | json |           |          | 
Indexes:
    "edges_pkey" PRIMARY KEY, btree (id)
    "edges_heads" btree (head_node)
    "edges_tails" btree (tail_node)
Foreign-key constraints:
    "edges_head_node_fkey" FOREIGN KEY (head_node) REFERENCES nodes(id) ON DELETE CASCADE
    "edges_tail_node_fkey" FOREIGN KEY (tail_node) REFERENCES nodes(id) ON DELETE CASCADE
```

## Limitations

I have also shifted some logic the application layer (like sorting results, so that people are surrounded by people with whom they are connected with).


