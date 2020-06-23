#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 19:30:07 2019

@author: mehrdad
"""
from math import sin, cos, sqrt, atan2, radians
import numpy as np
import pandas as pd


# =============================================================================
# def calc_OD_point_distance(legs):    
#     return legs.apply(lambda x: get_point_distance(x.origin,x.destination), axis=1)
# 
#     # slow code!:
#     #    legs['OD_point_distance'] = 0.0    
#     #    for index, leg in legs.iterrows():
#     #        legs.at[index, 'OD_point_distance'] = get_point_distance(leg.origin, leg.destination)        
#     #        #legs.apply(lambda x: get_point_distance(x.origin,x.destination), axis=1)
# 
# =============================================================================

def get_ODs_of_routes(paths):
    origins = np.zeros_like(paths)
    destinations = np.zeros_like(paths)
    n = 0
    for path in paths:
        origins[n] = path[0]
        destinations[n] = path[len(path)-1]
        n+=1
        
    return origins, destinations


def get_legs_boundaries(df):
    A = df.apply(lambda x: geo.LineString(x.path_human_readable).bounds, axis=1)
    AA = A.apply(lambda x: ((x[0], x[1]), (x[2], x[3])))
    B = pd.DataFrame(data=AA.values.tolist(), columns={'a', 'b' }, index=df.index)
    return B

def get_point_distance(A, B):    
    R = 6373.0 # approximate radius of earth in km
    
    lat1 = radians(A[0])
    lon1 = radians(A[1])
    lat2 = radians(B[0])
    lon2 = radians(B[1])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c * 1000 # distance in meters
        
    return distance

def get_point_distance_vecotrized(Alat, Alon, Blat, Blon):    
    R = 6373.0 # approximate radius of earth in km
    
    lat1 = np.radians(Alat)
    lon1 = np.radians(Alon)
    lat2 = np.radians(Blat)
    lon2 = np.radians(Blon)
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c * 1000 # distance in meters
        
    return distance