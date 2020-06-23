#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 18:47:31 2020

@author: mehrdad
"""

import numpy as np
import datetime
import pickle
import tslib.trip_detection
import tslib.server_app
from dal.base.database_commands_non_transactional import DatabaseCommandsNonTransactional
from dal.base.database_commands_transactional import DatabaseCommandsTransactional
from dal.base.database_session import DatabaseSession
import dal.trip_plans, dal.trips, dal.legs, dal.users
from pyfiles.common.otp_trip_planner import (OTPTripPlanner, OTPTripPlannerConfig)
from commonlayer.webnetworking import WebNetworking
from pyfiles.trips.trip_alternatives import TripAlternatives
from pyfiles.trips.trip_economics import TripEconomics




def compute_otp_trips(ref_trips, force_date_shift_to_current_week=False, retry_if_failed_with_404_stored=False):
    """ 
    NOTE: What value to pass for 'retry_if_failed_with_404_stored', depends on whether we run periodically on a server, and some other factors.
    """
    
    otp_planer_api_uri = 'http://api.digitransit.fi/routing/v1/routers/hsl/plan'

    # trip planners: 
    trip_plans_dal = dal.trip_plans.TripPlans(db_command_non_transactional)
    webnet = WebNetworking()
    planner_config = OTPTripPlannerConfig()
    # TODO: important settings, adjust depending on what is the nature of trips_for_otp_query 
    #planner_config.RETRY_ON_ALL_STORED_PLANS = True
    #planner_config.RETRY_ON_ALL_STORED_OTP_ERRORS = True
    planner_config.RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR = retry_if_failed_with_404_stored
    if force_date_shift_to_current_week:
        planner_config.PLAN_ONLY_WITH_SHIFTED_DATE = True
    planner = OTPTripPlanner(webnet, trip_plans_dal, otp_planer_api_uri, planner_config) # is passed a DAL class that has a non-transactional Command object

    #.prepare the list of trips of Trip class type
    trip_objects_for_otp_query = ref_trips
    
    #.plan otp trips and attach the alternatives to each observed trip
    # also stores the trip (OTP) route plans in 'trip_plans' table
    trip_alternatives = TripAlternatives(planner)
    planner.reset_stats()
    trips_with_computed_alts = trip_alternatives.plan_trip_alternatives_new(
                                                    trip_objects_for_otp_query,
                                                    desired_modes=['WALK', 'BICYCLE', 'PUBLIC_TRANSPORT']
                                                    )
    print("Total no of OTP records restored from DB cache =", planner.get_no_of_loaded_plans_from_cache())
    print("Total no of correct OTP plans restored from DB cache =", planner.get_no_of_correct_plans_loaded_from_cache())    
    print("Total no of new OTP queries sent =", planner.get_no_of_queries_sent())
    print("Total no of OTP responses with planning error =", planner.get_no_of_planning_errors_from_queries())
    print("Total no of deleted (AND replaced) plans in our DB cache =", planner.get_no_of_deleted_plans_from_cach())

    return trips_with_computed_alts

# TEST: review a bit
def TEST_review_computed_alts(trips_objects):            
    total_alts = 0
    for trip in trips_objects:
        if len(trip.alternative_trips) > 0:
            total_alts += len(trip.alternative_trips)
            print('--- trip (',trip.user_id,',',trip.id,')', 'planned', len(trip.alternative_trips),'alts ---')
            print('shifted_starttime_for_publictransport_tripplan:',trip.shifted_starttime_for_publictransport_tripplan)
            for alt in trip.alternative_trips:
                print('plan_id', alt.plan_id,', starttime', alt.starttime)
                leg_seq = ''
                distance = 0
                for leg in alt.legs:
                    leg_seq += '>'+leg['mode']
                    distance += leg['distance']
                    #print(leg['is_otp_leg'])
                print(leg_seq, '; calculated now D=', np.round(distance/1000, 1), 'km ; calculated by trip_economic D=', 
                      np.round(alt.distance/1000,1), 'km')
            print()
        else:
            print('--- trip (',trip.user_id,',',trip.id,')', 'ZERO alts planned ---')
            print('shifted_starttime_for_publictransport_tripplan:',trip.shifted_starttime_for_publictransport_tripplan)
            #print('--- trip (',trip.user_id,',',trip.id,')', 'planned ZERO alts!!! ---')
            pass                
    print("total trips:", len(trips_objects))
    print("total_alts:", total_alts)

               
def geoloc_string_to_tuple(geoloca_str):
    loc = geoloca_str.replace('(','').replace(')','').split(',')
    loc_tuple = (float(loc[0]), float(loc[1]))
    return loc_tuple

def review_leg_db_rows(leg_db_rows):
    for l in leg_db_rows:
        print(l)
    
def review_detected_trips(trips):
    # review and verify extracted trips: # TODO: add to general functions
    returned_to_middle_of_trip = 0
    for t in trips:
        ls = ''
        for l in t.legs:
            ls += l['mode'] + '->'
        returned_to_middle_of_trip += t.has_a_return_to_intermediate_destination
        od_D = (tslib.gis.get_point_distance(geoloc_string_to_tuple(t.origin_tuple), geoloc_string_to_tuple(t.destination_tuple)))/1000
        TT = np.round((t.endtime - t.starttime).total_seconds()/60)
        od_speed = np.round(od_D/(TT/60))
        if t.distance is not None:
            travel_D = np.round(t.distance/1000, 1)
        else:
            travel_D = 0

        print('(',t.user_id,t.id,'):',' start=',t.starttime,'; OD-D =',np.round(od_D,1),'; travel-D =',travel_D,"(km); O->D:",t.origin_tuple,t.destination_tuple," TT =",TT,'(min); OD-V =',od_speed,'(km/h)',ls,)
        if od_D > 50:
            print('\t\t',geoloc_string_to_tuple(t.origin_tuple), geoloc_string_to_tuple(t.destination_tuple))
            print('\t\t duration =', TT, 'minutes')            
        if len(t.legs_without_points) > 0:
            ls = ''
            bad_leg_ids = ''
            for l in t.legs_without_points:
                ls += l['mode'] + ';'
                bad_leg_ids += str(l['id']) + ';'
            print('--> legs_without_points: leg_ids=', bad_leg_ids, ';',ls) 
            
    print("Number of 'strange' trips with a leg returned_to_middle_of_trip =",returned_to_middle_of_trip)    
    # TODO ----------
    #   long distance cases, with incorrect mode, D > 100km ... but time short

    

# prepare connection to DB
#app, db, store, log = tslib.server_app.init_server_app()
#engine = db.engine
engine = tslib.database.init_db()
db_command_non_transactional = DatabaseCommandsNonTransactional(engine) 
db_session = DatabaseSession(engine)
db_command_transactional = DatabaseCommandsTransactional(db_session)

URBAN_LEG_MAX_TRAVEL_DISTANCE = 100 # km
USE_CUSTOM_DATE_RANGE = True # Usually on a server and running periodically, this flag should be disabled

# extract trips from legs ------------------------------
if True: # extarct trips from legs
    trips_dal = dal.trips.Trips(db_command_non_transactional)
    legs_dal = dal.legs.Legs(db_command_non_transactional) #TODO NOTE: DAL classes only access Command (not Session and Transaction)
    trip_economics = TripEconomics(legs_dal)
    
    ids_to_process = None # all users
    # Automatically detect which date range misses trips
    date_range_from = trips_dal.get_last_trip_end_time()
    # process up to some days ago (and not up to the present moment) to 'hope' that device_data_filtered records of legs are ready, and any crashes was resolved
    date_range_to = datetime.datetime.fromordinal((datetime.date.today() - datetime.timedelta(days=3)).toordinal())
    print("Date range with legs not processd for trip extraction:",date_range_from,"to",date_range_to)
    
    if USE_CUSTOM_DATE_RANGE:
        date_range_from = datetime.datetime(2019, 3, 14,    0, 0, 0)
        date_range_to = datetime.datetime(2019, 3, 16,    0, 0, 0)    
        #date_range_from = datetime.datetime(2020, 1, 1,    0, 0, 0)
        #date_range_to = datetime.datetime(2020, 2, 1,    0, 0, 0)            
        print("Date range customized:",date_range_from,"to",date_range_to)
    
    # Load all relevant legs, in order of start-time
    # TODO: memoray management: large memory needed if a lot of trips ** ...
    # Answer 1: no problem now ... even with 100,000 trips and assuming 1KB per trip-record --> only 100 MB memoray usage
    # NOTE: In PostgreSQL, seems like there is no max number of parameters in the IN clause
    legs_db_rows = legs_dal.load_legs(ids_to_process, date_range_from, date_range_to)
    if legs_db_rows.rowcount < 1:
        print()
        print("Note: No legs to process at the moment!")

    max_trip_id_per_user = trips_dal.get_max_trip_id_per_user(date_range_from, date_range_to, ids_to_process)
    idle_times = {'ALL': datetime.timedelta(minutes = 10), 'CAR':datetime.timedelta(minutes = 5)} # dynamic algorithm settings
    trips = tslib.trip_detection.extract_trips_from_legs(legs_db_rows, max_trip_id_per_user, idle_times, urban_leg_max_km=URBAN_LEG_MAX_TRAVEL_DISTANCE)
    print("Extraction of trips finished :)")
    
    trip_economics.calculate_trips_economics(trips)
    # review_detected_trips(trips)    
    print("Calculation of attributes finished :)")
    
    # store the new trips in DB
    trips_dal = dal.trips.Trips(db_command_transactional)    
    db_session.start_transaction()
    try:
        trips_dal.delete_trips_and_alternatives(date_range_from, date_range_to) # Remove both observed and computed trips in the date range
        trips_dal.store_trips_without_alts(trips)
        
        # commit only if all previous steps are complete
        db_session.commit_transaction()
        print("Stored all the new trips successfully :)")
    except Exception as e:
        db_session.rollback_transaction()
        print("Storing the new trips in DB FAILED! Changes rolled back.")
        print("EXCEPTION!:",e)
    finally:        
        pass

    # Cache it just in case
    with open('./data/output/extracted_trips_'+tslib.common.get_file_timestamp()+'.data', 'wb') as file:
        pickle.dump(trips, file)

    print("---- ENDED ----")
    print("We have processed these date ranges:",date_range_from,"to",date_range_to)

    

# Compute alternatives and store them --------------------------------
if True: # compute alts of new trips ----------------------------
    if False: # loading from trips cache
        trip_file_name = 'extracted_trips_2020-06-11 13:41:07.data'
        # extracted_trips_2020-06-10 23:22:39 (2019).data'
        with open('./data/output/'+trip_file_name, 'rb') as file:
            trips_loaded = pickle.load(file)
            #trips = trips[500:600] # NOTE: for test only
            #review_detected_trips(trips)
    else:
        trips_loaded = trips # Usually, on a server and running periodically, this is what we need
        # TODO: or load from database, according to the date range?

    print(); print('Computing alternative trips; For',len(trips_loaded),'observed trips; ...'); print()

    stored_well = 0
    stored_alts_well = 0
    not_stored = 0
    batch_size = 100
    for i in range(0, len(trips_loaded), batch_size):
        print()
        print('------------ Processing trips batch',i,'to',i+batch_size,'---------------')
        trips = trips_loaded[i: i+batch_size]
        
        # compute_missing_alternatives              
        trips_with_computed_alts = compute_otp_trips(trips, retry_if_failed_with_404_stored=False)

        #.compute attributes
        print("Computing attributes")
        trip_economics = TripEconomics(None)
        trip_economics.calculate_trips_alts_economics(trips_with_computed_alts)
        # Test and overview: 
        #TEST_review_computed_alts(trips_with_computed_alts)

        print("Storing computed alternatives in DB")
        #.store the alternatives in db ('trips_alts' table)
        # & update relevant fields of the observed trips in db
        #   e.g.: start_time_for_plan field in db                
        trips_dal = dal.trips.Trips(db_command_transactional)
        db_session.start_transaction()
        try:
            # insert the new alternatives
            alts_inserted = trips_dal.store_trips_alternatives(trips_with_computed_alts)

            # update relevant fields of the observed trips 
            # update the start_time_for_plan (indicates whether the stroed otp plan alternative have been shifted or not)
            res = trips_dal.update_trip_starttime_shifted_for_otp_query(trips_with_computed_alts)                
            if not res:
                raise
            
            # commit only if all previous steps are complete
            db_session.commit_transaction()
            # print("DB operations trasaction successful ***")
            stored_well += len(trips_with_computed_alts)
            stored_alts_well += alts_inserted
        except:
            db_session.rollback_transaction()
            not_stored += len(trips_with_computed_alts)
            print("Error! Storing the alternatives in DB FAILED; DB session rolled back.")
        finally:
            pass    
    print()
    print("Total no of trips that their alternatives were linked and stored in trips_alts table =", stored_well)
    print("Total no of alternatives linked and stored in trips_alts table =", stored_alts_well)
    print("Total no of trips with failed storing or linking of alternatives =", not_stored)
    print("---- ENDED ----")


