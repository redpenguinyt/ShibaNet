from flask_pymongo import PyMongo
from .flaskutils import app

mongo = PyMongo(app)