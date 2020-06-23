#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 31 13:31:13 2019

@author: mehrdad
"""

import pandas as pd
import numpy as np
import tslib.trip_detection

# Compute the difference between observed trips and computed trips ----------------------
# Any mode to any mode
def compute_observed_vs_computed_diffs(observed_, computed_):
    M1 = pd.merge(observed_[['duration_in_min','distance','od_distance2','emission',
                                  'walk_distance', 'bike_distance', 'active_distance']], 
                  computed_[['duration_in_min','distance','od_distance2','emission',
                                  'walk_distance', 'bike_distance', 'active_distance']],                                   
                  left_index=True, right_index=True, 
                  how='left', 
                  suffixes=['_observed', '_alt'], 
                  indicator=True)
    
    #TOOD: whenever need the user-trip-plan_id column values as columns:
    # ... M1.reset_index()
    
    diff = pd.DataFrame()
    #index is automatically created by this first insert!!!
    #   plan_id part of the index is that of the computed
#    diff['user'] = M1.user
#    diff['trip'] = M1.trip
#    diff['plan_id'] = M1.plan_id
    diff['has_any_computed'] = (M1._merge=='both')
    diff['deltaT'] = M1.duration_in_min_observed - M1.duration_in_min_alt 
    diff['deltaE'] = M1.emission_observed - M1.emission_alt
    diff['deltaD'] = M1.distance_observed - M1.distance_alt
    diff['delta_walk_D'] = M1.walk_distance_observed - M1.walk_distance_alt
    diff['delta_bike_D'] = M1.bike_distance_observed - M1.bike_distance_alt
    diff['delta_AD'] = M1.active_distance_observed - M1.active_distance_alt
        
    return diff


# Choose the desired time-relevant low-carbon alternative --------------------------------
# Selection is made in comparison to the observed trip's attributes
def compute_substitutes(observed_, computed_, observed_vs_computed_deltas_, with_ebike):   
    alts = observed_vs_computed_deltas_[observed_vs_computed_deltas_.has_any_computed]
    alts = alts.drop(columns='has_any_computed')
    alts = pd.merge(alts, computed_[['mode']], left_index=True, right_index=True, how='inner')
    alts.rename(columns={'mode':'mode_alt'}, inplace = True)
    
    # Consider e-bike or not
    if not with_ebike: 
        alts = alts[alts.mode_alt != 'EBICYCLE']
    
    # Skip bike for bad weather months
    alts = pd.merge(alts, observed_[['month']], left_index=True, right_index=True, how='inner')
    alts = alts[(alts.mode_alt!='BICYCLE') | (~alts.month.isin([1,2,3, 10,11,12]))]
    
    # Apply time-delta (max 3 min) and emission-saving conditions *:
    #np.sum((alts.deltaT >= -3) & (alts.deltaE > 0) & (alts.mode_alt=='CAR'))/len(alts) # mainmode is incorrect?!
    #M2 = alts[(alts.deltaT >= -3) & (alts.deltaE > 0) & (alts.mode_alt!='CAR')]
    C_duration = -3
    alts = alts[(alts.deltaT >= C_duration) & (alts.deltaE > 0)]
    
    # Then, select the alt with the smallest emission, i.e., the largest emission-saving
    deltaE_maxs = alts.groupby(level=['user', 'trip'])['deltaE'].max()
    alts = pd.merge(alts, deltaE_maxs, left_index=True, right_index=True, how='inner', suffixes=['','_max'])
    
    # another type of code:
    #alts = pd.merge(alts, deltaE_maxs, 
     #               left_on=['user','trip'], 
      #              right_index=True, how='inner', suffixes=['','_max'])
    
    alts = alts[alts.deltaE == alts.deltaE_max]
    
    # test the problems
    # M4[(M4.user_id==2) & (M4.trip_id==360)]
    # MT[['duration_in_min_observed','mode_alt','duration_in_min_alt']]
    #                 duration_in_min_observed mode_alt  duration_in_min_alt
    #user_id trip_id                                                            
    #2       360                          41.5      BICYCLE            43.350000
    #        360                          41.5       SUBWAY            29.366667
    #        360                          41.5       SUBWAY            28.366667
    #        360                          41.5       SUBWAY            29.366667
    #        
    
    # Select the alt with shortest travel-time, i.e., the largest time-saving
    # TODO: How about giving priority to for example bike or walk? ... more advanced prioritization
    deltaT_maxs = alts.groupby(level=['user', 'trip'])['deltaT'].max()
    alts = pd.merge(alts, deltaT_maxs, left_index=True, right_index=True, how='inner', suffixes=['','_max'])
    alts = alts[alts.deltaT == alts.deltaT_max]
    
    #
    #2
    #        198              3             3  ...           3           3
    #        207              3             3  ...           3           3
    
    # MT[['alt_plan_id','mode_alt','duration_in_min_alt', 'start_time']]
    
    
    # TODO: At this point, there is still some trips with more than one alternative!
    #   SOME mode_alts are duplicates ... e.g. OTP query for PT returned only WALK !
    #   for example Trip: (2, 116) ***
    dft = alts.reset_index()
    dft = dft.drop_duplicates(subset=['user','trip','mode_alt'])
    alts = dft.set_index(keys=['user','trip','plan_id'])
    #alts = alts.drop_duplicates(subset=['user','trip','mode_alt'])
    
    substitutes_ = pd.DataFrame()
    substitutes_['deltaE_max'] = alts.deltaE_max
    substitutes_['deltaT_max'] = alts.deltaT_max

    return substitutes_


# Choose the desired time-relevant low-carbon alternative --------------------------------
# Selection is made in comparison to the observed trip's attributes

def compute_substitutes_regardless_of_timesaving(observed_, computed_, observed_vs_computed_deltas_, 
                                                 day_weather_suitable_for_bike,
                                                 with_ebike = False,
                                                 consider_weather = True):
    print("-- compute_substitutes_regardless_of_timesaving --")
    alts = observed_vs_computed_deltas_[observed_vs_computed_deltas_.has_any_computed]    
    alts = pd.merge(alts, computed_[['mainmode']], left_index=True, right_index=True, how='inner')
    #alts.rename(columns={'mode':'mode_alt'}, inplace = True)
    
    # Consider e-bike or not
    if not with_ebike: 
        alts = alts[alts.mainmode != 'EBICYCLE'] # Discard ebike alts
    print(alts.shape, " deltas, with any-computed, and after e-bike filter")
    
    # Skip bike for bad weather months
    alts = pd.merge(alts, observed_[['start_date']], left_index=True, right_index=True, how='inner')    
    print(alts.shape)
    if consider_weather:
        alts_vs_day_weather = pd.merge(alts, day_weather_suitable_for_bike, 
                                       left_on='start_date', right_index=True, how='left')
        # TODO: Simply fill the missing weather days for now, with True:
        alts_vs_day_weather.day_suitable_for_bike.fillna('True', inplace=True)    
        alts = alts[(alts.mainmode!='BICYCLE') | (alts_vs_day_weather.day_suitable_for_bike)]
    print(alts.shape)

    # Skip bike for distance longer than certain thresholds
    # TODO

    
    # Apply emission-saving conditions *:
    alts = alts[(alts.deltaE > 0)]
    print(alts.shape)

    # TODO: How about giving priority to for example bike or walk? ... more advanced prioritization
    
    return alts[[]]  


# Filter so that every alt mode is unique per observed trip
#   for example, only one subway alt, only one bike alt, etc. per observed trip
#   Choose by:
#   1) by leg_count for now (later compute real 'transfer count')
#   2) travel time
def discard_duplicate_mode_per_alternative(computed_, substitutes_, deltas_):
    
    print("-- discard_duplicate_mode_per_alternative --")
    print(substitutes_.shape)
    
    to_any = pd.merge(computed_[['mainmode', 'leg_count', 'duration_in_min']], substitutes_, 
                  left_index=True, right_index=True)
    
    # So, filter so that every alt mode is unique per observed trip
    # for example, only one subway, only one bike, etc.
    # Choose by:
    # 1) least transfer-count and then (leg_count or old_leg_count for now, later compute real 'transfer count'), and then
    # 2) smallest travel-time per mode
    dft = to_any.reset_index()
    dft = dft.sort_values(by=['user', 'trip', 'mainmode', 'leg_count', 'duration_in_min'])
    dft.drop_duplicates(subset=['user','trip','mainmode'], inplace=True)
    to_any_reduced_1 = dft
    to_any_reduced_1.set_index(keys=['user','trip','plan_id'], inplace=True)    
    print(to_any_reduced_1.shape)    

    # TODO: function evaluation
    # TEST: if any trips or alt-modes are missed during the process:
    if False:
        #to_any.groupby(['user', 'trip', 'mainmode']).mainmode.count()
        #to_any_reduced_1.groupby(['user', 'trip', 'mainmode']).mainmode.count()
        #to_any_reduced_2.groupby(['user', 'trip', 'mainmode']).mainmode.count()
        dft = to_any[to_any.mainmode != 'SMALL_SHARE'].reset_index()
        dft.groupby(['user', 'trip', 'mainmode']).mainmode.count().sort_values()
        
        dft = to_any_reduced_2[to_any_reduced_2.mainmode != 'SMALL_SHARE'].reset_index()
        dft.groupby(['user', 'trip', 'mainmode']).mainmode.count().sort_values()
        # see one case that is still repetitive per mode
        test = dft[(dft.user == 8) & (dft.trip==3007)]
        test[['mainmode', 'leg_count', 'deltaT', 'distance', 'emission']]
        #15020      BUS              3  -7.850000    6522.2     419.3
        #15021      BUS              3  -7.850000    6522.2     419.3
        #15022      BUS              3  -7.850000    6522.2     419.3
        
        dft = to_any_reduced_3[to_any_reduced_3.mainmode != 'SMALL_SHARE'].reset_index()
        dft.groupby(['user', 'trip', 'mainmode']).mainmode.count().sort_values()
        
    return to_any_reduced_1[[]]



# merge and find observed-trips joined with their relevant computed alternative
def get_trips_with_shift(observed_, computed_, substitutes_, shift_from, shift_to):
    trips = observed_[observed_['mainmode'].isin(shift_from)]
    # NOTE: merge() returns a new dataframe
    trips_with_shift_from = pd.merge(substitutes_, trips[[]], left_index=True, right_index=True, how='inner')

    alt_trips = computed_[computed_['mainmode'].isin(shift_to)]
    trips_with_shift_from_to = pd.merge(trips_with_shift_from, alt_trips[[]], left_index=True, right_index=True, how='inner')
    
    return trips_with_shift_from_to


def get_unique_alt_per_observed_trip(to_trips, first_priority_is_transfer_count=True):
    dft = to_trips.reset_index()
    # test: check if any single leg trip?:  dft.leg_count.value_counts()
    if first_priority_is_transfer_count:
        dft = dft.sort_values(by=['user', 'trip', 'pt_transfer_count', 'duration_in_min', 'leg_count'])
    else:
        dft = dft.sort_values(by=['user', 'trip', 'duration_in_min', 'pt_transfer_count', 'leg_count'])
    dft_fixed = dft.drop_duplicates(subset=['user','trip'])
    dft_fixed.set_index(keys=['user','trip','plan_id'], inplace=True)        
    return dft_fixed
    
# Find shift from car to pt:    
def get_car_to_alts(observed_, computed_, substitutes_, deltas_, remove_per_trip_alt_duplicates):
    # Find shifts from car to pt
    car_to_pt = get_trips_with_shift(observed_, computed_, substitutes_, 
                                     ['CAR'], tslib.trip_detection.PT_MODES)
    car_to_pt_details = pd.merge(car_to_pt, deltas_, left_index=True, right_index=True, how='inner')
    car_to_pt_details = car_to_pt_details.join(computed_[['pt_transfer_count', 'leg_count',
                                                          'duration_in_min', 'mainmode', 'start_time', 'pt_leg_count']])
    # NOTE: Following function, selects per trip, the PT plans with least transfer count
    #       Although, lowest transfer count option, could have more walk (up to 1 km) or a bit slower
    if remove_per_trip_alt_duplicates:
        car_to_pt_details = get_unique_alt_per_observed_trip(car_to_pt_details)
#        dft = car_to_pt_details.reset_index()
#        # test: check if any single leg trip?:  dft.leg_count.value_counts()
#        dft = dft.sort_values(by=['user', 'trip', 'leg_count', 'duration_in_min'])
#        dft_fixed = dft.drop_duplicates(subset=['user','trip'])
#        car_to_pt_details = dft_fixed
#        car_to_pt_details.set_index(keys=['user','trip','plan_id'], inplace=True)
        
    # OLDER CODE:
#    dft = car_to_pt_details.reset_index()
#    dft = dft.sort_values(by=['user', 'trip', 'leg_count', 'duration_in_min'])
#    dft.drop_duplicates(subset=['user','trip'], inplace=True)
#    car_to_pt_details = dft
#    car_to_pt_details.set_index(keys=['user','trip','plan_id'], inplace=True)
    
    # more mode details:
    car_to_bus = car_to_pt_details[car_to_pt_details.mainmode == 'BUS']
    car_to_rail = car_to_pt_details[car_to_pt_details.mainmode.isin(['RAIL','TRAM','SUBWAY'])]
    car_to_tram = car_to_pt_details[car_to_pt_details.mainmode.isin(['TRAM'])]
    car_to_metro = car_to_pt_details[car_to_pt_details.mainmode.isin(['SUBWAY'])]
    car_to_train = car_to_pt_details[car_to_pt_details.mainmode.isin(['RAIL'])]
    car_to_ferry = car_to_pt_details[car_to_pt_details.mainmode.isin(['FERRY'])]
    car_to_pt_multimode = car_to_pt_details[car_to_pt_details.mainmode == 'PT_MULTIMODE']
    
    # Find shifts from car to bike
    car_to_bike = get_trips_with_shift(observed_, computed_, substitutes_, 
                                                         ['CAR'], ['BICYCLE'])
    car_to_bike_details = pd.merge(car_to_bike, deltas_, left_index=True, right_index=True, how='inner')    
    car_to_bike_details = car_to_bike_details.join(computed_[['leg_count', 'duration_in_min', 'mainmode', 'start_time']])
    
    # Find shifts from car to walk
    car_to_walk = get_trips_with_shift(observed_, computed_, substitutes_, 
                                                         ['CAR'], ['WALK'])
    car_to_walk_details = pd.merge(car_to_walk, deltas_, left_index=True, right_index=True, how='inner')    
    car_to_walk_details = car_to_walk_details.join(computed_[['leg_count', 'duration_in_min', 'mainmode', 'start_time']])
        
    
    return car_to_pt_details, car_to_bike_details, car_to_walk_details,\
            car_to_bus, car_to_rail, car_to_tram, car_to_metro, car_to_train, car_to_ferry, car_to_pt_multimode
            
# -----------------------------------------------------------------------------
def get_alts_passing_deltaT_threshold(to_trips, deltaT_threshold):
    return to_trips[-to_trips.deltaT <= deltaT_threshold]

            
def get_ratio_of_modalshift_by_deltaT_threshold(from_trips, to_trips, deltaT_threshold):
    # TODO: this could also have an option to filter out deltaT and deltaE outliers
    
    return np.sum(to_trips.deltaT >= - deltaT_threshold) / len(from_trips)


def compute_modalshift_ratios_by_deltaT_thresholds(from_trips, to_trips, deltaT_threholds):
    ratios = []
    for threshold in deltaT_threholds:
        ratio = get_ratio_of_modalshift_by_deltaT_threshold(from_trips, 
                                                          to_trips, 
                                                          threshold)
        ratios.append(ratio)
    return ratios
