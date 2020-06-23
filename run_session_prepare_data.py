#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 17:33:26 2020

@author: mehrdad
"""

#import prepare_data
import tslib.session.data_holder
import tslib.session.settings

import load_and_filter
import compute_mainmodes
import compute_modal_shifts
import tslib.trip_detection


# Start a session, and set filter and computation settings ---------------------------------

# Session sahred data:
session_data_global = tslib.session.data_holder.DataHolder()

# Set the run settings
settings = tslib.session.settings.SettingsHolder()
settings.data_filters = tslib.session.settings.DataFilters(from_year=2016, to_year=2019, 
                                                           from_date_iso_str = '2016-01-01',
                                                           to_date_iso_str = '2019-03-16',
                                                           region_name='Helsinki')
# NOTE: If ModalShiftFilters changes, then HAVE_NEW_MODALSHIFT_METHODS is True
settings.modal_shift_filters = tslib.session.settings.ModalShiftFilters(
                                                        min_C = 10, max_C = 300, # defaults: 10-30
                                                        max_precipitation = 5) # default: 5
settings.modal_shift_filters.consider_weather = True # TODO: optional

settings.DATASTORE_FOLDER = './data/datastore'
settings.DATAOUT_FOLDER = './data/output'

session_data_global.settings = settings

# --------------------------------------------------------------
# . Load data
# . Filter with initial conditions
# . Compute trip attributes
# . Compute potential changes and modal shifts
# . etc.

HAVE_NEW_TRIPS_IN_DATABASE = True
HAVE_NEW_MODALSHIFT_METHODS = True # Better to be True; If the above weather settings change, modal-shifts need recalculation
HAVE_NEW_ESTIMATION_METHODS = True

session_data = session_data_global

if HAVE_NEW_TRIPS_IN_DATABASE:
    HAVE_NEW_MODALSHIFT_METHODS = True
    
    load_and_filter.load_from_db(session_data)
    load_and_filter.compute_attributes(session_data.observed_trips, session_data.computed_trips)
    load_and_filter.compute_datasets(session_data)
    
    compute_mainmodes.fix_ebike_in_computed_multimodes(session_data.computed_trips)    

    #. Optional to call following function for observed trips?
    #. Wrong to call for computed trips, as their leg sequences are already correct
    #   compute_mainmodes.combine_samemode_leg_sequences(...)
        
    compute_mainmodes.compute_mainmodes_for_observed(session_data.observed_trips)
    
    # Following should be called only after legs on the same vehicle (unnecessarily detected as multiple legs) 
    # are combined, i.e. inter-leg idle times discarded
    load_and_filter.compute_leg_and_transfer_attributes(session_data)
    
    compute_mainmodes.compute_mainmodes_for_computed(session_data.computed_trips) # needs leg-count values
    #compute_mainmodes.fix_alts_with_misplaced_plan_id(session_data)
    
    # Save to files:
    load_and_filter.save_to_file(session_data)
    compute_mainmodes.save_to_file(session_data)
        
    #TODO: Also, compute clusters here
    if False: # read from ready file for now
        load_and_filter.load_clusters(session_data) 
    else:
        #exec(open("compute_trip_clusters_v2.py").read())
        #exec(open(compute_trip_clusters_v3_more_conditions.py").read())
        pass
else:
    # Load from file, if no new algorithm, or no new data
    load_and_filter.load_from_file(session_data)    
    compute_mainmodes.load_data_with_fixed_modes(session_data)
    load_and_filter.load_clusters(session_data)
    
    if session_data.observed_trips.empty:
        raise Exception("session_data.observed_trips is empty")
        

# Now, filter the loaded data according to specified ranges; dates, city region, etc.
load_and_filter.apply_initial_filters(session_data.settings, session_data)
load_and_filter.discard_noise_and_classify(session_data)
load_and_filter.cut_datasets_to_match_obsvered_trips(session_data)


if HAVE_NEW_ESTIMATION_METHODS:
    # compute emissions, having the desired CO2_E_PKM value
    session_data.observed_trips['emission_old'] = session_data.observed_trips.emission
    session_data.computed_trips['emission_old'] = session_data.computed_trips.emission
    session_data.observed_trips['emission'] = tslib.trip_detection.compute_trips_emissions(session_data.observed_trips)
    session_data.computed_trips['emission'] = tslib.trip_detection.compute_trips_emissions(session_data.computed_trips)
    
    #TODO: persons.compute_attributes()


if HAVE_NEW_MODALSHIFT_METHODS:
    print()
    print("Computing modal shifts and the resulting changes ... ")
    compute_modal_shifts.compute_and_save_to_file(session_data)
else:
    compute_modal_shifts.load_modal_shifts(session_data)

print()
print("------ Completed ------")
print("Session Settings:")
session_data.settings.report_settings()
print(); print("Outcome:")
session_data.report_session_data()
