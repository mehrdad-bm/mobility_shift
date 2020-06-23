#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 16:38:57 2019

@author: mehrdad
"""
import pandas as pd
import os
import pickle
import time
import datetime


def duration_to_minutes(duration):
    return duration.total_seconds()/60.0

def duration_to_hours(duration):
    return duration.total_seconds()/(60*60)

def duration_str_to_minutes(duration_str_series):
    duration = pd.DatetimeIndex(duration_str_series)
    minutes_series = duration.hour*60 + duration.minute + duration.second/60.0
    return minutes_series

def duration_str_to_hours(duration_str_series):
    duration = pd.DatetimeIndex(duration_str_series)
    hours_series = duration.hour + duration.minute/60.0 + duration.second/3600.0
    return hours_series

def get_file_timestamp():
    return str(datetime.datetime.fromtimestamp(int(time.time())))

def save_dataframe_to_file(folder, filename_without_extension, legs):    
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    path_prefix = folder+'/'+filename_without_extension
    
    with open(path_prefix+'.data', 'wb') as file:
        pickle.dump(legs, file)

def load_dataframe_from_file(folder, filename_without_extension):    
    filename = folder+'/'+filename_without_extension+'.data'
    
    if not os.path.exists(filename):
        raise Exception("load_dataframe_from_file(): ERROR! File does not exist: ",filename)
        return pd.DataFrame()
        
    with open(filename, 'rb') as file:
        x=pickle.load(file)
    return x


class StopWatch:
    def __init__(self):
        self._start_time = None
        self._end_time = None
        self._took = None
        self._started = False
        self._stopped = False
        
    def start(self):
        self._start_time = time.time()
        self._started = True
        self._stopped = False
        
    def stop(self):
        if self._started:
            if not self._stopped:
                self._end_time = time.time()
                self._took = self._end_time - self._start_time
                self._stopped = True
            else:
                print("Stopwatch already stopped!")
        else:
            print("Start the stopwatch first!")
            
    def report(self, subsecond_digits=2):
        if self._stopped:
            print("Stopwatch elapsed",round(self._took, subsecond_digits),"seconds.")
        elif self._started:
            so_far = time.time() - self._start_time
            print("Stopwatch elapsed so far:",round(so_far, subsecond_digits),"seconds; Still running...")
        else:
            print("Stopwatch not started!")
        
    def stop_and_report(self):
        self.stop()
        self.report(subsecond_digits=2)
        
    def get_elapsed(self):
        if self._took is not None:
            return self._took