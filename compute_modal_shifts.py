#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 18:30:39 2019

@author: mehrdad
"""

import tslib.common, tslib.trip_detection, tslib.gis
import tslib.mapplot
import tslib.modal_shift
import tslib.weather

#For data from TS app
input_folder = 'data'
output_folder = 'data/output'

# -----------------------------------------------------------------------------------

def compute_and_save_to_file(session_data):
    # Settings:
    WITH_EBIKE = False
    
    # Compute the difference between observed trips and computed trips ----------------------
    deltas = tslib.modal_shift.compute_observed_vs_computed_diffs(
                                                            session_data.observed_trips, 
                                                            session_data.computed_trips)
    obsvered_trips_with_zero_computed = deltas[~ deltas.has_any_computed]
    
    # Choose the desired time-relevant low-carbon alternatives --------------------------------
    # Selection is made in comparison to the observed trip's attributes
    time_relevant_substitutes = tslib.modal_shift.compute_substitutes(session_data.observed_trips, 
                                                        session_data.computed_trips, 
                                                        deltas, 
                                                        WITH_EBIKE)
    
    # Choose the desired low-carbon alternatives, regardless of being time-relevant -------------------
    # Main conditions: altternative has to be emission-saving
    day_suitable_for_bike = tslib.weather.are_days_suitable_for_bike(
                                                            session_data.daily_weather_history, 
                                                            session_data.settings.modal_shift_filters.min_C,
                                                            session_data.settings.modal_shift_filters.max_C,
                                                            session_data.settings.modal_shift_filters.max_precipitation)
    substitutes_no_time_limit_1 = tslib.modal_shift.compute_substitutes_regardless_of_timesaving(
                                                        session_data.observed_trips, 
                                                        session_data.computed_trips, 
                                                        deltas, 
                                                        day_suitable_for_bike,
                                                        WITH_EBIKE,
                                                        session_data.settings.modal_shift_filters.consider_weather)
    # Filter so that every alt mode is unique per observed trip
    #   for example, only one subway alt, only one bike alt, etc. per observed trip
    #   Choose by:
    #   1) by leg_count for now (later compute real 'transfer count')
    #   2) travel time
    substitutes_no_time_limit_2 = tslib.modal_shift.discard_duplicate_mode_per_alternative(
                                                            session_data.computed_trips, 
                                                            substitutes_no_time_limit_1,
                                                            deltas)
    substitutes_no_time_limit = substitutes_no_time_limit_2 # Update the final return value
    
    session_data.update_modal_shift_data(deltas, 
                                         time_relevant_substitutes, substitutes_no_time_limit, 
                                         day_suitable_for_bike)
    
    
    # ---------------------------------------------------------------------------
    print("Total number of observed vs. computed deltas:",len(deltas.index.unique()))
    print("Total number of substitutes with deltaT max = 3 min:",len(time_relevant_substitutes.index.unique()))
    print("Total number of substitutes regardless of deltaT value:",len(substitutes_no_time_limit.index.unique()))
    
    print("WARNING:",len(obsvered_trips_with_zero_computed.index.unique()),"observed trips do not have *any* computed alternatives")
    print("That is", round(100*len(obsvered_trips_with_zero_computed.index.unique())/len(session_data.observed_trips.index.unique()), 1), "% of all observed trips")
    print()
    
    # ---------------------------------------------------------------------------
    # if SAVE_ON_DISK:
    print("Saving to file ...")
    tslib.common.save_dataframe_to_file(output_folder,'observed_vs_computed_deltas', deltas)
    tslib.common.save_dataframe_to_file(output_folder,'substitutes', time_relevant_substitutes)
    tslib.common.save_dataframe_to_file(output_folder,'substitutes_no_time_limit', substitutes_no_time_limit)
    tslib.common.save_dataframe_to_file(output_folder,'day_suitable_for_bike', day_suitable_for_bike)
    #deltas.to_csv(output_folder+'/observed_vs_computed_deltas.csv')
    #time_relevant_substitutes.to_csv(output_folder+'/substitutes.csv')
    
# -------------------------------------------
def load_modal_shifts(session_data):
    print("Loading modal shifts from file ...")
    deltas = tslib.common.load_dataframe_from_file(output_folder,'observed_vs_computed_deltas')
    time_relevant_substitutes = tslib.common.load_dataframe_from_file(output_folder,'substitutes')
    substitutes_no_time_limit = tslib.common.load_dataframe_from_file(output_folder,'substitutes_no_time_limit')
    day_suitable_for_bike = tslib.common.load_dataframe_from_file(output_folder,'day_suitable_for_bike')

    session_data.update_modal_shift_data(deltas, time_relevant_substitutes, substitutes_no_time_limit, day_suitable_for_bike)

