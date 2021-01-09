import os
import json

from sqlalchemy import (
    create_engine,
    sql,
)
from uuid import UUID as pyUUID

from flask import Flask
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = "*"
    header["Access-Control-Allow-Headers"] = "*"
    header["Access-Control-Allow-Methods"] = "*"
    return response

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
        person_details AS (
            SELECT people.id, people.properties, edges.label, edges.head_node FROM
                nodes LEFT OUTER JOIN people ON nodes.id = people.id LEFT OUTER JOIN edges ON edges.tail_node = people.id
        ),
        results AS (
            SELECT
                person_details.id,
                person_details.properties::text AS props,
                COALESCE(json_agg(json_build_object('type', person_details.label,'name', nodes.properties->>'name', 'id', nodes.id)) FILTER (WHERE person_details.label is not null), '[]') AS outgoing_edges
                FROM person_details LEFT OUTER JOIN NODES ON person_details.head_node = nodes.id GROUP BY 1,2
        )
        SELECT id, props::json, outgoing_edges FROM results WHERE id IS NOT NULL;
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
SQL_INSERT_EDGE = sql.text("INSERT INTO edges (tail_node, head_node, label) VALUES (:tail_node, :head_node, :label) RETURNING *")
SQL_DELETE_NODE = sql.text("""DELETE FROM nodes WHERE id = :id""")

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('search')
parser.add_argument('properties', type=dict, location='json')
parser.add_argument('relationships', type=dict, location='json')

parser.add_argument('tail_node', location='json')
parser.add_argument('head_node', location='json')
parser.add_argument('type', location='json')


class Person(Resource):
    def get(self, person_id):
        with db.begin() as connection:
            res = connection.execute(SQL_GET_PERSON_BY_ID, id=person_id)

        results = [dict(i) for i in res]
        for item in results:
            for key, value in item.items():
                if isinstance(value, pyUUID):
                    item[key] = str(value)

        return results[0]

    def put(self, person_id):
        arguments = parser.parse_args()

        properties = arguments.get('properties')
        if properties is None:
            return

        with db.begin() as connection:
            pass

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

        results = [dict(i) for i in res]
        for item in results:
            for key, value in item.items():
                if isinstance(value, pyUUID):
                    item[key] = str(value)

        return results

    def post(self):
        arguments = parser.parse_args()
        properties = arguments.get('properties')
        relationships = arguments.get('relationships')

        if relationships is not None:
            head_node = relationships.get('id')
            label = relationships.get('type')

        with db.begin() as connection:
            res = connection.execute(SQL_INSERT_NODE, properties=json.dumps(properties))
            node = [i for i in res][0]
            node = dict(node)
            node['id'] = str(node['id'])
            if relationships is not None:
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

        return res, 201

    def get(self):
        pass


api.add_resource(Person, '/people/<person_id>')
api.add_resource(People, '/people/')
api.add_resource(Relationships, '/relationships/')


if __name__ == '__main__':
    app.run(debug=True)
