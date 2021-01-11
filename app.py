import os
import json
import time
import logging

from sqlalchemy import (
    create_engine,
    sql,
)
from uuid import UUID

from flask import Flask, request, g
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

log = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

@app.before_request
def before_request():
    g.start = time.time()

@app.after_request
def after_request(response):
    diff = round(time.time() - g.start, 4)
    log.info(f"request time: {diff} seconds")
    return response

@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = "*"
    header["Access-Control-Allow-Methods"] = "*"
    header["Access-Control-Allow-Headers"] = "Content-Type"
    return response

APP_SECRET = os.getenv('APP_SECRET') or 'jabberwocky'

@app.before_request
def check_api_key():
    if os.getenv("CHECK_AUTH") == 'false':
        return
    auth_header = 'x-people-auth'
    if auth_header not in request.headers or request.headers[auth_header] != APP_SECRET:
        return 'Forbidden', 401


# TODO this is for local dev - to be removed later
DB_HOST = os.getenv("DB_HOST") or "localhost"
DB_NAME = os.getenv("DB_NAME") or "people-api"
DB_PORT = os.getenv("DB_PORT") or "5432"
DB_USER = os.getenv("DB_USER") or "people-api"
DB_PASSWORD = os.getenv("DB_PASSWORD") or "people-api"

db_string = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
db_string = os.getenv("DATABASE_URL") or db_string

db = create_engine(db_string)

# These CTEs are reused in each query and are not parametrized, hence they are safe to be passed as a format string param
SQL_STATIC_CTE_PARTS = """
        person_details_outgoing_edges AS (
            SELECT people.id, people.properties, edges.label, edges.head_node, edges.tail_node FROM
                nodes LEFT OUTER JOIN people ON nodes.id = people.id LEFT OUTER JOIN edges ON edges.tail_node = people.id
        ),
        person_details_incoming_edges AS (
           SELECT people.id, people.properties, edges.label, edges.head_node, edges.tail_node FROM
               nodes LEFT OUTER JOIN people ON nodes.id = people.id LEFT OUTER JOIN edges ON edges.head_node = people.id
        ),
        results AS (
            SELECT
                person_details_outgoing_edges.id,
                person_details_outgoing_edges.properties::text AS props,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'type', person_details_outgoing_edges.label,'name', nodes.properties->>'name', 'id', nodes.id
                        )
                    ) FILTER (WHERE person_details_outgoing_edges.label is not null), '[]'
                ) AS outgoing_edges
                FROM person_details_outgoing_edges LEFT OUTER JOIN NODES ON person_details_outgoing_edges.head_node = nodes.id GROUP BY 1,2
        ),
        results2 AS (
            SELECT
                person_details_incoming_edges.id,
                person_details_incoming_edges.properties::text AS props,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'type', person_details_incoming_edges.label,'name', nodes.properties->>'name', 'id', nodes.id
                        )
                    ) FILTER (WHERE person_details_incoming_edges.label is not null), '[]'
                ) AS incoming_edges
                FROM person_details_incoming_edges LEFT OUTER JOIN NODES ON person_details_incoming_edges.tail_node = nodes.id GROUP BY 1,2
        ),
        graph AS (
            SELECT results.id, results.props::json, json_build_object('out', outgoing_edges, 'in', incoming_edges) AS edges
            FROM results, results2 WHERE results.id IS NOT NULL and results.id  = results2.id
        )
        SELECT * FROM graph
"""


SQL_GET_PERSON_BY_NAME = sql.text(f"""
    WITH people AS (SELECT id, properties FROM nodes WHERE properties->>'name' = :name), {SQL_STATIC_CTE_PARTS}
""")

SQL_GET_PERSON_BY_ID = sql.text(f"""
    WITH people as (select id, properties from nodes where id = :id), {SQL_STATIC_CTE_PARTS}
;""")


SQL_GET_ALL_PEOPLE = sql.text(f"""
    WITH people AS (SELECT id, properties FROM nodes), {SQL_STATIC_CTE_PARTS}
       """)

SQL_GET_ALL_PEOPLE_FREE_TEXT_SEARCH= sql.text(f"""
    WITH people AS (SELECT id, properties FROM nodes join json_each_text(nodes.properties) props ON True WHERE props.value ilike :search_term),
    {SQL_STATIC_CTE_PARTS}
""")


SQL_INSERT_NODE = sql.text("INSERT INTO nodes (properties) VALUES (:properties) RETURNING *")
SQL_DELETE_NODE = sql.text("""DELETE FROM nodes WHERE id = :id""")
SQL_UPDATE_NODE = sql.text("""UPDATE nodes SET properties = :properties WHERE id = :id RETURNING *""")

SQL_INSERT_EDGE = sql.text("INSERT INTO edges (tail_node, head_node, label) VALUES (:tail_node, :head_node, :label) RETURNING *")
SQL_GET_EDGE_FROM_TO_NODE = sql.text("SELECT * FROM edges WHERE tail_node= :id or head_node = :id")

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('search')
parser.add_argument('properties', type=dict, location='json')
parser.add_argument('relationships', type=dict, location='json')

parser.add_argument('from', location='json')
parser.add_argument('to', location='json')
parser.add_argument('type', location='json')


class Person(Resource):
    def get(self, person_id):
        with db.begin() as connection:
            res = connection.execute(SQL_GET_PERSON_BY_ID, id=person_id)

        results = [dict(i) for i in res]
        for item in results:
            for key, value in item.items():
                if isinstance(value, UUID):
                    item[key] = str(value)

        return results[0]

    def put(self, person_id):
        arguments = parser.parse_args()

        properties = arguments.get('properties')

        with db.begin() as connection:
            res = connection.execute(SQL_UPDATE_NODE, id=person_id, properties=json.dumps(properties))
            res = [i for i in res][0]
            res = dict(res)
            res['id'] = str(res['id'])

        return res, 200

    def delete(self, person_id):
        with db.begin() as connection:
            res = connection.execute(SQL_DELETE_NODE, id=person_id)



class People(Resource):
    def get(self):
        arguments = parser.parse_args()
        name = arguments.get('name')
        search = arguments.get('search')

        with db.begin() as connection:
            if name is not None:
                res = connection.execute(SQL_GET_PERSON_BY_NAME, name=name)
            elif search is not None:
                res = connection.execute(SQL_GET_ALL_PEOPLE_FREE_TEXT_SEARCH, search_term=f'%{search}%')
            else:
                res = connection.execute(SQL_GET_ALL_PEOPLE)

        # This is so that people are more or less grouped together
        # based on whether or not they have a connection
        unsorted_results = []
        ids = {}
        for item in res:
            item = dict(item)
            item['id'] = str(item['id'])  # for serializing UUIDs
            unsorted_results.append(item)
            ids[str(item['id'])] = item

        already_in = set()
        sorted_results = []

        for item in unsorted_results:
            if item['id'] not in already_in:
                sorted_results.append(item)
                already_in.append(item)

            # add their connections to the result set
            connections = item['edges']['in'] + item['edges']['out']

            for conn in connections:
                if conn['id'] not in already_in:
                    sorted_results.append(ids[conn['id']])
                    already_in.add(conn['id'])

        return sorted_results

    def post(self):
        arguments = parser.parse_args()
        properties = arguments.get('properties')
        relationships = arguments.get('relationships')

        with db.begin() as connection:
            res = connection.execute(SQL_INSERT_NODE, properties=json.dumps(properties))
            node = [i for i in res][0]
            node = dict(node)
            node['id'] = str(node['id'])
            if relationships is not None:
                head_node = relationships.get('id')
                label = relationships.get('type')
                connection.execute(SQL_INSERT_EDGE, tail_node=node['id'], head_node=head_node, label=label)

        return node, 201


class Relationships(Resource):
    def post(self):
        arguments = parser.parse_args()
        tail_node = arguments.get('from')
        head_node = arguments.get('to')
        label = arguments.get('type')
        with db.begin() as connection:
            edge = connection.execute(SQL_INSERT_EDGE, tail_node=tail_node, head_node=head_node, label=label)

        res = [i for i in edge][0]
        res = dict(res)
        res['id'] = str(res['id'])
        res['from'] = str(res['tail_node'])
        res['to'] = str(res['head_node'])

        del res['tail_node']
        del res['head_node']

        return res, 201

    def get(self):
        with db.begin() as connection:
            edge = connection.execute(SQL_GET_EDGE_FROM_TO_NODE, id=node_id)
        
api.add_resource(Person, '/people/<person_id>')
api.add_resource(People, '/people/')
api.add_resource(Relationships, '/relationships/')


if __name__ == '__main__':
    app.run(debug=True)
