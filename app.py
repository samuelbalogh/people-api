import os

import requests

from sqlalchemy import create_engine
from flask import Flask
from flask_restful import Resource, Api

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
parser = reqparse.RequestParser()

class People(Resource):
    def get(self):
        result_set = db.execute("SELECT * FROM nodes")
        results = [p for p in result_set]
        return results

    def post(self)


api.add_resource(People, '/people')


if __name__ == '__main__':
    app.run(debug=True)
