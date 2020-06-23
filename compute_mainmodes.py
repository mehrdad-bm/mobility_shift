#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 00:17:55 2020

@author: mehrdad
"""
import json
import numpy as np
import pandas as pd
import time
import math
#import blist
import tslib.mining
import tslib.common
import tslib.trip_detection
import tslib.trip


STORE_RESULTS = False

#output_folder = './data/output'

#all_modes = {'WALK':0, 'RUN':0, 'BUS': 0, 'TRAM':0, 'RAIL':0, 'FERRY':0, 
#             'CAR':0, 'SUBWAY':0, 'BICYCLE':0, 'EBICYCLE':0}
#all_modes_df = pd.DataFrame(data=all_modes.values(), index=all_modes.keys())

#from pyfiles.common.modalchoice import ModalChoice


# ----------------------------------------------------------------------------------------

def combine_sequential_modes(multimodal_summary):    
    multimodal_summary = multimodal_summary.replace('RUN','WALK')
    
    l = multimodal_summary.split('->')
    new_l = []
    prev_mode = 'none'
    for mode in l:
        if mode == prev_mode:
            pass
        else:
            new_l.append(mode)
            prev_mode = mode
            
    new_modes_str = '->'.join(new_l)
    
    return new_modes_str


def fix_ebike_in_computed_multimodes(data):
    print("fix_ebike_in_computed_multimodes() ...")
    start = time.time()
    ebikes = data[data['mode']=='EBICYCLE']
    new_multimodal = ebikes.multimodal_summary.apply(lambda x: x.replace('BICYCLE', 'EBICYCLE'))
    data.update(new_multimodal)
    
    new_d_by_mode = ebikes.distance_by_mode.apply(lambda x: x.replace('EBICYCLE', 'ERASED'))
    new_d_by_mode = new_d_by_mode.apply(lambda x: x.replace('BICYCLE', 'EBICYCLE'))    
    #ebikes.distance_by_mode.values[0]
    #'{"RUN": 0.0, "WALK": 0.0, "EBICYCLE": 0.0, "BICYCLE": 20427.21}'
    data.update(new_d_by_mode)
    
    # TODO: If planning to also update time_by_mode, the time values should be reduced according to ebike speed
    # ...
    
    #temp = pd.DataFrame()
    #temp['multimodal_summary'] = ebikes.multimodal_summary.apply(lambda x: x.replace('BICYCLE', 'EBICYCLE'))

    end = time.time()
    print("elapsed", end-start)


def compute_modes_distance_shares_per_trip(data):
    # ----------------------------------------
    # Get distances-by-mode
    #temp = data.distance_by_mode.apply(lambda x: dict(json.loads(x)))
    temp = data.distance_by_mode.apply(json.loads)
    d_df = temp.to_frame()
    d_df['distance'] = data.distance
    
    start = time.time()
    
    # compute modes distance shares per trip ---------------
    #users = blist.blist() # maybe better performance for larger datasets
    #users = list(np.zeros(len(d_df), dtype=int)) # not necessary unless profiler shows that list.append() is a bottleneck
    
    users = list()
    trip_ids = list()
    plan_ids = list()
    mode_shares = list()
    max_mode_shares = list()
    max_modes = list()
    total_d_errors =list()
    row_index = 0
    
    for trip in d_df.itertuples():
        users.append(trip.Index[0])
        trip_ids.append(trip.Index[1])
        if len(trip.Index)==3: # for computed_trips
            plan_ids.append(trip.Index[2])
    
        total_distance = trip.distance
        d = trip.distance_by_mode
        dvals = np.array(list(d.values()))
    
        total = math.fsum(dvals)
            
        if total>0:
            shares = dvals/total
            max_share = shares.max()
            max_index = shares.argmax()
            max_mode = list(d.keys())[max_index]
                
            shares = shares[shares>0]
        else:
            max_share = 0
            max_mode = 'UNDEFINED'
            shares = []
        
        mode_shares.append(shares)
        max_mode_shares.append(max_share)
        max_modes.append(max_mode)
        total_d_errors.append(total_distance - total)
    
        #users[row_index] = trip.Index[0]
        row_index += 1
    
    all_data={#'user': users, 
          #'trip': trip_ids, 
          'max_mode': max_modes, 
          'max_mode_share':max_mode_shares,
          'mode_shares':mode_shares,
          'total_d_error':total_d_errors}
    
    #users = np.apply_along_axis(lambda x: x[0] , 1, indexes)
    #trip_ids = np.apply_along_axis(lambda x: x[1] , 1, indexes)
    #plan_ids = np.apply_along_axis(lambda x: x[2] , 1, indexes)
    if len(trip.Index) == 2:
        all_index=[users, trip_ids]
    elif len(trip.Index) == 3: # for computed_trips
        all_index=[users, trip_ids, plan_ids]
    
    mode_distance_shares = pd.DataFrame(index=all_index, data=all_data)
    # mode_distance_shares.set_index(keys=['user', 'trip'], inplace=True)
    
    end = time.time()
    print("compute_modes_distance_shares_per_trip(): elapsed", end-start)
    
    return mode_distance_shares
    # -----------------------------------------

def compute_mainmode_per_trip(mode_distance_shares):
    # Compute main-mode per trip -----------------------
    start = time.time()
    
    mainmodes = []
    mainmode_shares = []
    
    for trip in mode_distance_shares.itertuples():
        MIN_SHARE = tslib.mining.MIN_DISTANCE_SHARE_OF_MAINMODE
        
        if trip.max_mode_share < MIN_SHARE and trip.max_mode_share > 0:
            main_mode = 'SMALL_SHARE'
            main_mode_share = 0 # we don't have a main-mode for this trip
        else:
            main_mode = trip.max_mode
            main_mode_share = trip.max_mode_share
            if main_mode == 'RUN': 
                main_mode = 'WALK'
    
        mainmodes.append(main_mode)
        mainmode_shares.append(main_mode_share)
        
    mode_distance_shares['mainmode'] = mainmodes
    mode_distance_shares['mainmode_share'] = mainmode_shares
    
    end = time.time()
    print("elapsed", end-start)
    
    return mode_distance_shares


# -----------------------------------------------------------

def get_all_mode_shares(mode_distance_shares):
    # Get all mode distance shares, for later stats -----------------------
    start = time.time()
    
    share_values_history = []
    for trip in mode_distance_shares.itertuples():
        share_values_history.extend(trip.mode_shares)
    share_values_history_df = pd.DataFrame(data={'mode_distance_share': share_values_history})
    
    end = time.time()
    print("elapsed", end-start)
    
    return share_values_history_df
    # ---------------------------------------
    
    
def combine_samemode_leg_sequences(trips):
    # Refine multimodal_summary of each trip, combine modes repeated right after each other:        
    trips['multimodal_summary_combined'] = trips.multimodal_summary.apply(combine_sequential_modes)    

    
def compute_mainmodes_for_observed(trips):
    print("compute_mainmodes_for_observed(): Given ",len(trips),"trip records")        
        
    mode_distance_shares = compute_modes_distance_shares_per_trip(trips)
    mode_distance_shares = compute_mainmode_per_trip(mode_distance_shares)
    # optional?: share_values_history_df = get_all_mode_shares(mode_distance_shares)    
    # Update the records:
    trips['old_mode'] = trips['mode']
    trips['mode'] = mode_distance_shares['mainmode']
    trips['mainmode'] = mode_distance_shares['mainmode']
    trips['mainmode_share'] = mode_distance_shares['mainmode_share']
    
    if STORE_RESULTS:
        store_filename_suffix = 'observed'
        print("saving to file ...")
        mode_distance_shares.to_csv('./trips/output/'+'mode_distance_shares_'+store_filename_suffix+'.csv')
        #share_values_history_df.to_csv('./trips/output/share_values_history_df_'+store_filename_suffix+'.csv')


def compute_mainmodes_for_computed(trips):
    print("compute_mainmodes_for_computed(): Given ",len(trips),"trip records")                
    
    mode_distance_shares = compute_modes_distance_shares_per_trip(trips)    
    mode_distance_shares = compute_mainmode_per_trip(mode_distance_shares)
    trips['mainmode_share'] = mode_distance_shares['mainmode_share']
    
    tslib.trip_detection.compute_mainmode_of_PT_trips(trips)    
    tslib.trip_detection.compute_mainmode_of_non_PT_trips(trips)



def fix_alts_with_misplaced_plan_id(session_data):
    computed_trips_ = session_data.computed_trips
    
    # POSSIBLE FIXES
    # See: X.multimodal_summary.value_counts() of following datasets:
    # also: 
    #   np.histogram(pt_alts_by_planid.car_distance/pt_alts_by_planid.distance, bins=[0, 0.01, 0.3, 0.7, 1])
    #   np.histogram(pt_alts_by_planid.bike_distance/pt_alts_by_planid.distance, bins=[0, 0.01, 0.3, 0.7, 1])
    #   np.histogram(pt_alts_by_planid.walk_distance/pt_alts_by_planid.distance, bins=[0, 0.3, 0.7, 1])
    #   np.histogram(pt_alts_by_planid.pt_distance/pt_alts_by_planid.distance, bins=[0, 0.3, 0.7, 1])
    walk_alts_by_planid = tslib.trip_detection.get_alts_by_planid(computed_trips_, [1]) # supposed to be walk alts 
        #OK, but very few CAR, BIKE and PT
            # for which, bike and pt should be fine because they have the correct mainmode ??
    bike_alts_by_planid = tslib.trip_detection.get_alts_by_planid(computed_trips_, [2]) # supposed to be bike alts 
        #OK, but very few CAR and PT
    car_alts_by_planid = tslib.trip_detection.get_alts_by_planid(computed_trips_, [3]) # supposed to be bike alts 
        # Has ~400 PT, 60 WALK
            # The PT ones wihtout SMALL_SHARE are fine already
            
    pt_alts_by_planid = tslib.trip_detection.get_alts_by_planid(computed_trips_, [4,5,6]) # only can be PT alts
    #test: (pt_alts_by_planid[pt_alts_by_planid.mainmode == 'WALK']).multimodal_summary.value_counts()
        # 2551 are only WALK leg, and apparently those trips already have plan_id=1 WALK computed: 
            # Implies PT is not available or not posisble? ... see the distances
            # Update computed_trips as 'mainmode' = PT_PLANNED_AS_WALK ?!!               
        # the rest have at least one PT leg. 
            # How to fixe computed_trips?
            # Is it ok if for a 'PT' trip, actual motorized distance is only e.g. 20%?
                # 12191 reciords mainmode == SMALL_SHARE ***
                # Update SMALL_SHARE to a PT mode
                #   to the largest share ?!
                #   to dft.old_mode.value_counts() ?!
                #   to 'MULTI_PT_MODES' or 'PT_SMALL_SHARE' and then add 'MULTI_PT_MODES', etc. to PT_MODES ?!
    
    # Make the corrections:
    # PT alts:
    # .1
    revise = pt_alts_by_planid[(pt_alts_by_planid.multimodal_summary == 'WALK') & (pt_alts_by_planid.mainmode != 'PT_PLANNED_AS_WALK')]
    computed_trips_.loc[computed_trips_.index.isin(revise.index), 'mainmode'] = 'PT_PLANNED_AS_WALK'
    
    # .2
    revise = pt_alts_by_planid[pt_alts_by_planid.mainmode == 'SMALL_SHARE']
    #revise['pt_d_share'] = revise.pt_distance/revise.distance
    #revise[['old_mode', 'multimodal_summary', 'pt_distance', 'pt_d_share']]
    #dft.multimodal_summary
    computed_trips_.loc[computed_trips_.index.isin(revise.index), 'mainmode'] = 'PT_SMALL_SHARE'
    # . Where mainmode incorrectly classified as 'WALK' because walk leg had largest distance-share
    revise = pt_alts_by_planid[(pt_alts_by_planid.multimodal_summary.apply(tslib.trip.has_pt_leg)) &\
                               (~ pt_alts_by_planid.mainmode.isin(tslib.trip_detection.PT_MODES))]
    computed_trips_.loc[computed_trips_.index.isin(revise.index), 'mainmode'] = 'PT_SMALL_SHARE'
    
    # .3
    revise = car_alts_by_planid[car_alts_by_planid.multimodal_summary.apply(tslib.trip.has_pt_leg) &\
                                (car_alts_by_planid.mainmode == 'SMALL_SHARE')]
    computed_trips_.loc[computed_trips_.index.isin(revise.index), 'mainmode'] = 'PT_SMALL_SHARE'    
    

        
# ======================================================
    
def save_to_file(session_data):
    print("Saving trips to file ...")
    output_folder = session_data.settings.DATAOUT_FOLDER
    tslib.common.save_dataframe_to_file(output_folder,'observed_trips', session_data.observed_trips)
    tslib.common.save_dataframe_to_file(output_folder,'computed_trips', session_data.computed_trips)

    
def load_data_with_fixed_modes(session_data):
    print("Loading trips from file ...")
    data_storage_folder = session_data.settings.DATASTORE_FOLDER    
    session_data.observed_trips = tslib.common.load_dataframe_from_file(data_storage_folder,'observed_trips')
    session_data.computed_trips = tslib.common.load_dataframe_from_file(data_storage_folder,'computed_trips')
    
