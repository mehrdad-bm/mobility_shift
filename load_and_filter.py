#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 18:30:39 2019

@author: mehrdad
"""

import pandas as pd
import time
import tslib.common, tslib.trip_detection
import tslib.server_app
import tslib.database    
from dal.base.database_commands_non_transactional import DatabaseCommandsNonTransactional
import dal.trips
import dal.users
import dal.weather
import tslib.trip


# --- load and prepare -----------------
def load_from_db(session_data):
    # --- Init connecting to database ---
    #app, db, store, log = tslib.server_app.init_server_app()
    #engine = db.engine
    engine = tslib.database.init_db()
    db_command_non_transactional = DatabaseCommandsNonTransactional(engine)
    
    # Directly query from database, if DB is available
    trips_dal = dal.trips.Trips(db_command_non_transactional)
    users_dal = dal.users.Users(db_command_non_transactional)
    weather_dal = dal.weather.Weather(db_command_non_transactional)

    print("Loading records from DB ...")
    start = time.time()
    observed_trips = trips_dal.load_observed_trips(session_data.settings.data_filters.from_date_iso_str, session_data.settings.data_filters.to_date_iso_str)
    computed_trips = trips_dal.load_computed_trips(session_data.settings.data_filters.from_date_iso_str, session_data.settings.data_filters.to_date_iso_str)        
    traveler_stats = users_dal.load_user_activity_stats()
    weather_history = weather_dal.load_observed_weather()
    end = time.time()
    print("elapsed:", round(end-start), "seconds")

    # Set proper index, as (user, trip)
    # NOTE: Interesting that index does not have to be unique in pandas, 
    #       e.g. for computed_trips, the real unique index would be (user, trip, plan_id)
    observed_trips = observed_trips.set_index(['user','trip'], drop=True)
    computed_trips = computed_trips.set_index(['user','trip','plan_id'], drop=True)
    # Note: See the index names by: df.index.names
    # Note: Use df.reset_index() to
    #       Copy the index values into the dataframe as columns 
    #       Set index as a single column of oridinal numbers starting at 0
    # And maybe df.set_index(keys=['column name','column name' ...]) to move columns to index
    
    print("Total number of loaded observed trips:",len(observed_trips))
    print("Total number of loaded computed trips:",len(computed_trips))
    print("Total number of loaded traveler activity stats:",len(traveler_stats))
        
    # return observed_trips, computed_trips, traveler_stats, weather_history
    
    session_data.update_db_loaded_data(observed_trips, 
                                    traveler_stats,
                                    computed_trips, 
                                    weather_history)


def load_clusters(session_data):
    #cluster_file_path = './data/output/OD_clusters/max_1000m/fixed'
    cluster_file_path = session_data.settings.DATASTORE_FOLDER+'/trip clusters/max_1000m/fixed'
    cluster_file_name = 'OD_and_D_clusters_users_2_274_ALL_USERS_1583704253'
    session_data.trips_of_clusters_without_trip_info = tslib.common.load_dataframe_from_file(cluster_file_path, cluster_file_name)
    

def compute_attributes(observed_trips, computed_trips):
    print("Initializing and adding columns to the loaded records ...")
    start = time.time()
    tslib.trip_detection.init_trips(observed_trips)
    tslib.trip_detection.init_trips(computed_trips)        
    end = time.time()
    print("elapsed:", round(end-start), "seconds")

def compute_leg_and_transfer_attributes(session_data):
    tslib.trip_detection.compute_leg_counts(session_data.observed_trips)
    tslib.trip_detection.compute_leg_counts(session_data.computed_trips)
    tslib.trip_detection.compute_trasfer_counts(session_data.observed_trips)
    tslib.trip_detection.compute_trasfer_counts(session_data.computed_trips)
    
def compute_datasets(session_data):
    session_data.daily_weather_history = tslib.weather.compute_daily_weather(session_data.weather_history)



# --- initial filters -------------------------------------------------------------------------------
def apply_initial_filters(session_settings, session_data):
    trips = session_data.observed_trips
    
    # Desired date range:
    #   note: We got almost no weather data for year 2016 and year 2020!
    from_year = session_settings.data_filters.from_year
    to_year = session_settings.data_filters.to_year
    trips = trips[(trips.year >= from_year) & (trips.year <= to_year)]
    #   test: np.histogram(trips.year, [2015, 2016, 2017, 2018, 2019, 2020, 2021])
    #         np.histogram(daily_weather_history.year, [2015, 2016, 2017, 2018, 2019, 2020, 2021])
    
    # Desired region:
    trips = tslib.trip_detection.filter_by_region_from_OD(trips, session_settings.data_filters.region_name)
   
    session_data.observed_trips = trips



def discard_noise_and_classify(session_data):
    # Deal with noise and accuracy, circle trips, etc. ----------------------------------------

    # 'observed_trips' so far contains trips after desired range filers
    # keep it, just in case for further exploration
    session_data.observed_trips_with_noise = session_data.observed_trips.copy()
        
    
    # NOTE: Classification of trips by detection noise, route shape, etc. :
    # -- Tree of filtered trips --
    # observed_trips_with_noise
    #   correct_trips
    #       non_circle_trips    (assumed as 'observed_trips' for further analysis after this step)
    #       circle_trips
    #           round_trips
    #   incorrect_trips
    
    # Remove some noise ---------
    trips = session_data.observed_trips
    correct_trips = tslib.trip_detection.get_correct_trips(trips,
                                                           min_route_distance=0,
                                                           min_urban_speed=tslib.mining.MIN_VALID_URBAN_SPEED,
                                                           max_urban_speed=tslib.mining.MAX_VALID_URBAN_SPEED,
                                                           max_walk_speed=tslib.mining.MAX_VALID_WALK_SPEED)
    incorrect_trips = trips[~trips.index.isin(correct_trips.index.values)]
        
    # Separate normal, circle and round trips ------------:
    coeff = tslib.mining.TRAVELED_DISTANCE_TO_OD_DISTANCE_COEFF
    circle_trips = tslib.trip_detection.get_circle_trips(correct_trips, min_traveled_to_od_distance_coeff=coeff)
    round_trips = tslib.trip_detection.get_roundtrips(correct_trips, 
                                                      max_od_distance=tslib.mining.OD_CLUSTER_RADIUS, 
                                                      min_traveled_to_od_distance_coeff=coeff)
    # Note: 'round_trips' are a subset of 'circle_trips'
    non_circle_trips = correct_trips[~correct_trips.index.isin(circle_trips.index.values)]
    
    # Only non-circle trips will go to next steps as 'observed_trips'
    observed_trips = non_circle_trips.copy() # Update it! # TODO
    # ----------------------------------------------------------------------------------

    #return incorrect_trips, correct_trips, circle_trips, round_trips, observed_trips

    session_data.update_denoised_trip_data(correct_trips, observed_trips, circle_trips, round_trips, incorrect_trips)
    
    

def cut_datasets_to_match_obsvered_trips(session_data):
    observed_trips = session_data.observed_trips
    computed_trips = session_data.computed_trips
    traveler_stats = session_data.traveler_stats
    trips_of_clusters_without_trip_info = session_data.trips_of_clusters_without_trip_info
    
    
    # Match other datasets to the selected and noise-filtered observed_trips -------------------------
    # Filter computed_trips also, to match with the filtered observed_trips: 
    # Note: The names specified in *_on=[], are what merge() looks for, either in the Index or Data Columns
    computed_trips = pd.merge(observed_trips[[]], computed_trips, left_index=True, right_on=['user','trip'], how='inner')
    # TODO: Why the following does not return a dataframe with 'plan_id' in the index?!
    # pd.merge(observed_trips[[]], computed_trips, on=['user','trip'], how='inner')
    # pd.merge(observed_trips[[]], computed_trips, left_on=['user','trip'], right_on=['user','trip'], how='inner')
    
    # Set correct number of travelers, only from final selected trips
    print(traveler_stats.shape, "traveler_stats")
    travelers = observed_trips.index.get_level_values(0).unique().values
    traveler_stats = traveler_stats[traveler_stats.user.isin(travelers)]    
    print(traveler_stats.shape, "traveler_stats according to selected observed_trips")
    
    
    trips_of_clusters_without_trip_info = trips_of_clusters_without_trip_info.join(observed_trips[[]], on=['user', 'trip'], how='inner')

    
    # Get index of trips(user_id, trip_id) observed
    print("Total number of filtered observed trips to be used:",len(observed_trips.index.unique()))
    print("Total number of filtered computed trips to be used:",len(computed_trips.index.unique()))
    
    # Get index of trips(user_id, trip_id) for which at least one alternative is computed
    #trip_indexes_in_computed = computed_trips.index.unique() # funny that 'index' may not be unique
    #print("Total no. of computed alt trips:",len(trip_indexes_in_computed))
    
    # TODO: Are trips <500 m dimissed also during computing alt trips?
    #   6688 observed short trips (bad trips not filteed)
    #       1008 of these observed short trips are present in computed too *
    #           7 of their alts have traveled-distance <500m
    #           0 od_distance2_observed <500m !!!! ERROR in data?
    #   run Compute Alternatives with OTP, for <500m trips ??
    # Test code for above stats: 
    #   np.sum(alts.distance_observed<500)
    
    # TODO: What's the source of this error in data?
    # 2873 observed trips where OD_Distance longer than Travelled-distance !!!!
    # test code for this: np.sum((observed_trips.od_distance2>observed_trips.distance))
    
    
    # Updatte session data
    session_data.computed_trips = computed_trips
    session_data.traveler_stats = traveler_stats
    session_data.travelers = travelers
    session_data.trips_of_clusters_without_trip_info = trips_of_clusters_without_trip_info
    



# ----------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------


# Store the refined and filtered records:
#def save_to_file():
#    if BACKUP_ON_DISK:
#        print("Saving filtered refined observed trips and computed trips to file ...")
#        # NOTE: Binary (.data) files are better with date-time types, than .csv files, for our code
#        tslib.common.save_dataframe_to_file(output_folder,'observed_trips', observed_trips)
#        tslib.common.save_dataframe_to_file(output_folder,'computed_trips', computed_trips)
#        tslib.common.save_dataframe_to_file(output_folder,'bad_observed_trips', bad_observed_trips)
#        # Save into csv too, for human readability, exporting to QGIS, and so on
#        observed_trips.to_csv(output_folder+'/observed_trips.csv')
#        computed_trips.to_csv(output_folder+'/computed_trips.csv')


def save_to_file(session_data):    
    # keep an on-disk backup of the original records, just in case
    # NOTE: Binary (.data) files are better with date-time types, than .csv files, for our code
    output_folder = session_data.settings.DATAOUT_FOLDER
    
    #tslib.common.save_dataframe_to_file(output_folder,'observed_trips_not_filtered', session_data.observed_trips)
    #tslib.common.save_dataframe_to_file(output_folder,'computed_trips_not_filtered', session_data.computed_trips)
    tslib.common.save_dataframe_to_file(output_folder,'person_active_days_with_legs', session_data.traveler_stats)            
    tslib.common.save_dataframe_to_file(output_folder,'weather_history', session_data.weather_history)
    tslib.common.save_dataframe_to_file(output_folder,'daily_weather_history', session_data.daily_weather_history)        
    
    # Save into csv too, for human readability, exporting to QGIS, and so on
    #        observed_trips.to_csv(output_folder+'/observed_trips_not_filtered.csv')
    #        computed_trips.to_csv(output_folder+'/computed_trips_not_filtered.csv')
    #        traveler_stats.to_csv(output_folder+'/person_active_days_with_legs.csv')
        
        
def load_from_file(session_data):    
    # Load from the back-up files, that were originally loaded in Python from DB
    #   NOTE: Binary files are better with date-time types for our code
    
    data_storage_folder = session_data.settings.DATASTORE_FOLDER
    
    observed_trips = None
    computed_trips = None
        
    print("Loading traveler-stats and weather-data file ...")
    traveler_stats = tslib.common.load_dataframe_from_file(data_storage_folder, 'person_active_days_with_legs')
    weather_history = tslib.common.load_dataframe_from_file(data_storage_folder, 'weather_history')
    daily_weather_history = tslib.common.load_dataframe_from_file(data_storage_folder, 'daily_weather_history')
    

    #global session_data
    session_data.update_file_loaded_data(observed_trips, 
                                    traveler_stats,
                                    computed_trips, 
                                    weather_history, daily_weather_history)

    
    print()
    #print("Total number of loaded trips:",len(observed_trips))
#    print("correct_trips trips:",len(correct_trips))
#    print("observed_trips trips:",len(observed_trips))
#    print("circle_trips trips:",len(circle_trips))
#    print("circle_trips trips:",len(circle_trips))
#    print("incorrect trips:",len(incorrect_trips))
#    print("    SUM =",len(correct_trips)+len(incorrect_trips))
#    print("Total number of loaded traveler activity stats:",len(traveler_stats))
#    print("Total number of loaded filtered computed trips:",len(computed_trips))

