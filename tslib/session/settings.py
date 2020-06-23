#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 15:02:04 2020

@author: mehrdad
"""

import json
import datetime

class ModalShiftFilters():
    def __init__(self, min_C, max_C, max_precipitation):
        self.min_C = min_C
        self.max_C = max_C
        self.max_precipitation = max_precipitation

class DataFilters():
    def __init__(self, from_year, to_year, from_date_iso_str, to_date_iso_str, region_name):
        self.from_year = from_year
        self.to_year = to_year
        self.from_date_iso_str = from_date_iso_str
        self.to_date_iso_str = to_date_iso_str
        #self.from_date_iso_str = str(datetime.datetime.fromisoformat(str(self.from_year)+'-01-01'))
        #self.to_date_iso_str = str(datetime.datetime.fromisoformat(str(self.to_year+1)+'-01-01'))
        self.region_name = region_name
        
                                        

class SettingsHolder():
    def __init__(self):
        # Settings for loading, computation and analysis in this session:
        self.data_filters = None
        self.modal_shift_filters = None
        self.DATASTORE_FOLDER = None
        self.DATAOUT_FOLDER = None

    def report_settings(self):
        if self.data_filters is not None:
            print(self.data_filters.__dict__)
        if self.modal_shift_filters is not None:
            print(self.modal_shift_filters.__dict__)
                
    def get_settings_dict(self):
        settings_dict = dict()
        settings_dict.update({"data_filters": self.data_filters.__dict__})
        settings_dict.update({"modal_shift_filters": self.modal_shift_filters.__dict__})
        return settings_dict
    
    def save_to_file(self):
        with open(self.DATAOUT_FOLDER+'/session_settings.json', 'w') as file:
            file.write(json.dumps(self.get_settings_dict()))