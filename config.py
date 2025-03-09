import os

class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:root@localhost:8889/auctions'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
