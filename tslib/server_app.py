#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  3 12:00:05 2019

@author: mehrdad
"""


from flask import Flask
import logging
import tslib.database

    
def init_server_app(allow_debug_mode=True):
    # TODO: Remove?
    logging.basicConfig()
    log = logging.getLogger(__name__)    
    # OR MAYBE USE IT AS USED in TEST_HSL_data.py
    #   log.setLevel(logging.INFO)
    # Then, Replace the print() statements with the following functions
    #   log.exception
    #   log.warning
    #   log.info()
        
    app = Flask(__name__)

    in_debug_mode = allow_debug_mode
    
    # Read the configs 
    app.config.from_pyfile('../app_config.cfg')

    # Settings for debug/non-debug
    if in_debug_mode:
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
        app.debug = True
        log.setLevel(logging.INFO)
        print ('init_server_app(): Running in Debug mode.')
    else:
        # IMPORTANT custom settings for performance
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.debug = False
        log.setLevel(logging.WARNING)
    
    db, store = tslib.database.init_db_with_flask(app)
    
    return app, db, store, log

