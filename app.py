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


single_person_by_name = sql.text("""
    with
        person as (
            select id, properties from nodes where properties->>'name' = :name
        ), 
        person_details as (
            select person.properties, nodes.*, edges.label, edges.head_node from
                nodes, edges, person where nodes.id = person.id and edges.tail_node = person.id
        ) 
        select person_details.*, nodes.properties->>'name' as head_node_name
            from person_details, nodes 
            where person_details.head_node = nodes.id
;""")

single_person_by_id = sql.text("""
    with
        person as (
            select id, properties from nodes where id = :id
        ), 
        person_details as (
            select person.properties, nodes.*, edges.label, edges.head_node from 
                nodes, edges, person where nodes.id = person.id and edges.tail_node = person.id
        ) 
        select person_details.*, nodes.properties->>'name' as head_node_name
            from person_details, nodes 
            where person_details.head_node = nodes.id
;""")



class Person(Resource):
    def get(self, person_id):
        with db.begin() as connection:
            res = connection.execute(single_person_by_id, id=person_id)

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
        arguments = parser.parse_args()
        name = arguments.get('name')

        with db.begin() as connection:
            res = connection.execute(single_person_by_name, name=name)

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
