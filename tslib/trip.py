#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  7 11:35:21 2020

@author: mehrdad
"""

import json
import tslib.trip_detection



# TODO: refactor
def has_pt_leg(multimodal_summary):
    return any(leg_mode in multimodal_summary for leg_mode in tslib.trip_detection.PT_SINGLE_MODES)

# TODO: refactor
def has_bike_leg(multimodal_summary):
    return any(leg_mode in multimodal_summary for leg_mode in ['BICYCLE'])

def get_mainmode_group(mainmode):
    if mainmode in tslib.trip_detection.PT_MODES:
        return 'PT'
    else:
        return mainmode

def get_leg_count(multimodal_summary):
    return len(multimodal_summary.split('->'))

def get_pt_leg_count(multimodal_summary):
    pt_legs_str = multimodal_summary.replace('WALK', '').replace('EBICYCLE', '').replace('BICYCLE', '').replace('CAR', '')
    legs = pt_legs_str.split('->')
    pt_leg_count = len(legs) - legs.count('')
    return pt_leg_count

def get_mode_leg_count(multimodal_summary, mode_str):
    return multimodal_summary.split('->').count(mode_str)


def get_pt_transfer_count(pt_leg_count):    
    transfer_count = max([0, pt_leg_count - 1])
    return transfer_count
   
#def compute_pt_transfer_count(multimodal_summary):
#    modes = multimodal_summary.split('->')
#    pt_leg_count = 0
#    for mode in modes:
#        pt_leg_count += (mode in PT_SINGLE_MODES)
#    transfer_count = np.max([0, pt_leg_count - 1])
#    return transfer_count
    

def get_att_by_mode(att_summary_str, mode_str): # example usage: get_att_by_mode(emission_by_mode, 'CAR')
    j = json.loads(att_summary_str)
    if mode_str in j:
        return j[mode_str]
    else:
        return 0


