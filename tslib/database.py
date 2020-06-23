#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 13:41:56 2020

@author: mehrdad
"""

import sqlalchemy
import flask_sqlalchemy
import flask_kvsession
import simplekv.db.sql
import json


def init_db():
    # Wihtout Flask
    db_engine = None
    with open("./db_config.json") as file:
        settings = json.loads(file.read())
    connection_url = settings['SQLALCHEMY_DATABASE_URI']
    db_engine = sqlalchemy.create_engine(connection_url)    
    return db_engine

def init_db_with_flask(app):
    db = flask_sqlalchemy.SQLAlchemy(app)    

    metadata = db.metadata
    metadata.bind = db.engine

    # Run session storage also on SQLAlchemy
    store = simplekv.db.sql.SQLAlchemyStore(db.engine, metadata, 'kv_session')
    flask_kvsession.KVSessionExtension(store, app)
    
    return db, store