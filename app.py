import os

from sqlalchemy import (
    create_engine,
    sql,
    Table,
    MetaData,
    Column,
    String,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSON

from uuid import UUID as pyUUID

from flask import Flask
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

# TODO this is for local dev - to be removed later
DB_HOST = os.getenv("DB_HOST") or "localhost"
DB_NAME = os.getenv("DB_NAME") or "people-api"
DB_PORT = os.getenv("DB_PORT") or "5432"
DB_USER = os.getenv("DB_USER") or "people-api"
DB_PASSWORD = os.getenv("DB_PASSWORD") or "people-api"

db_string = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

db_string = os.getenv("DATABASE_URL") or db_string

db = create_engine(db_string)

metadata = MetaData()

nodes = Table('nodes', metadata,
    Column('id', UUID, primary_key=True),
    Column('properties', JSON)
)

edges = Table('edges', metadata,
    Column('tail_node', UUID, ForeignKey('nodes.id')),
    Column('head_node', UUID, ForeignKey('nodes.id')),
    Column('label', String),
    Column('properties', JSON),
)

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
    WITH
        people AS (
            SELECT id, properties FROM nodes WHERE properties->>'name' = :name
        ),
        {SQL_STATIC_CTE_PARTS}
""")

SQL_GET_PERSON_BY_ID = sql.text(f"""
    with
        people as (
            select id, properties from nodes where id = :id
        ), 
        {SQL_STATIC_CTE_PARTS}
;""")


SQL_GET_ALL_PEOPLE = sql.text(f"""
    WITH
        people AS (
            SELECT id, properties FROM nodes
        ),
       {SQL_STATIC_CTE_PARTS}
       """)


SQL_GET_ALL_PEOPLE_FREE_TEXT_SEARCH= sql.text(f"""
    WITH
        people AS (
            SELECT id, properties FROM nodes join json_each_text(nodes.properties) props ON True WHERE props.value ilike :search_term
        ),
       {SQL_STATIC_CTE_PARTS}
""")


class Person(Resource):
    def get(self, person_id):
        with db.begin() as connection:
            res = connection.execute(SQL_GET_PERSON_BY_ID, id=person_id)

        results = [dict(i) for i in res]
        for item in results:
            for key, value in item.items():
                if isinstance(value, pyUUID):
                    item[key] = str(value)

        return results

    def put(self, person_id):
        arguments = parser.parse_args()
        
        with db.begin() as connection:
            stmt = sql.insert([nodes])


class People(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name')
        parser.add_argument('search')

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
        pass


api.add_resource(Person, '/people/<person_id>')
api.add_resource(People, '/people/')


if __name__ == '__main__':
    app.run(debug=True)
