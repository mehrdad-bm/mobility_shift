#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 23:19:48 2020

@author: mehrdad
"""

import threading
import tslib.threads
import tslib.common
import tslib.trip_computation
import datetime
import pickle
import numpy as np
import tslib.server_app
import tslib.database
import tslib.common
import tslib.trip_detection
import tslib.trip_computation
from dal.base.database_commands_non_transactional import DatabaseCommandsNonTransactional
from dal.base.database_commands_transactional import DatabaseCommandsTransactional
from dal.base.database_session import DatabaseSession
import dal.trip_plans, dal.trips, dal.legs, dal.users
from pyfiles.common.otp_trip_planner import (OTPTripPlanner, OTPTripPlannerConfig)
from commonlayer.webnetworking import WebNetworking
from pyfiles.trips.trip_economics import TripEconomics


# --------------------------------------------------------------

def save_extracted_trips_brief_to_file(trips, filename):
    trips_df = tslib.common.object_list_to_df(trips)
    if trips_df.empty:
        trips_df.to_csv(filename)
    else:
        trips_df['origin_wkt'] = trips_df.origin.apply(tslib.gis.pointrow_to_kwt)
        trips_df['destination_wkt'] = trips_df.destination.apply(tslib.gis.pointrow_to_kwt)                
        trips_df.rename(columns={'id':'trip_id'}, inplace=True)
        trips_df.to_csv(filename, columns=['user_id', 'trip_id', 'starttime', 'endtime', 
                                           'origin_tuple', 'destination_tuple', 'origin_wkt', 'destination_wkt'],
                                            sep=';')

def save_ignored_trips_brief_to_file(trips, filename):
    trips_df = tslib.common.object_list_to_df(trips)
    if trips_df.empty:
        trips_df.to_csv(filename)
    else:
        trips_df['origin_wkt'] = trips_df.origin.apply(tslib.gis.pointrow_to_kwt)
        trips_df['destination_wkt'] = trips_df.destination.apply(tslib.gis.pointrow_to_kwt)                
        trips_df.rename(columns={'id':'trip_id'}, inplace=True)
        trips_df.to_csv(filename, columns=['user_id', 'trip_id', 'planning_mode', 'multimodal_summary',
                                           'starttime', 'endtime', 
                                           'distance', 'origin_wkt', 'destination_wkt', 'notes'],
                                            sep=';')

def report_parallel_settings():
    print('trips_within_region:',len(trips_within_region))
    print('MAX_THREAD_COUNT:', MAX_THREAD_COUNT)
    print('MAX_BATCH_SIZE:', MAX_BATCH_SIZE)
    print('ideal_batch_size *:',ideal_batch_size)
    print('batch_size:', batch_size)
    print('util:', util)
    print('run_rounds:', run_rounds)

    
# =========================================================
# =========================================================
DEBUG_MODE = True
TARGET_REGION_FOR_OTP = 'Helsinki' # Could be 'All' if we have linked to OTP server(s) that process(es) any region or city
USE_CUSTOM_DATE_RANGE = True # Usually on a server and running periodically, this flag should be disabled
COMPUTE_ALT_TRIPS = True

session_file_timestamp = tslib.common.get_file_timestamp()

# Prepare connection to DB
#app, db, store, log = tslib.server_app.init_server_app()
#db_engine = db.engine
db_engine = tslib.database.init_db()

stopwatch_all = tslib.common.StopWatch()
stopwatch_all.start()

# extract trips from legs ------------------------------
elapsed_extract = 0
if True: # extarct trips from legs
    db_session = DatabaseSession(db_engine)
    db_command_transactional = DatabaseCommandsTransactional(db_session)
    db_command_non_transactional = DatabaseCommandsNonTransactional(db_engine) 

    w = tslib.common.StopWatch()
    w.start()
    
    trips_dal = dal.trips.Trips(db_command_non_transactional)
    legs_dal = dal.legs.Legs(db_command_non_transactional) #NOTE: DAL classes only access Command (not Session and Transaction)
    trip_economics = TripEconomics(legs_dal)
    
    ids_to_process = None # all users
    # Automatically detect which date range misses trips
    date_range_from = trips_dal.get_last_trip_end_time()
    # process up to some days ago (and not up to the present moment) to 'hope' that device_data_filtered records of legs are ready, and any crashes was resolved
    date_range_to = datetime.datetime.fromordinal((datetime.date.today() - datetime.timedelta(days=2)).toordinal())
    print("Date range with legs not processd for trip extraction:",date_range_from,"to",date_range_to)
    
    if USE_CUSTOM_DATE_RANGE:
        #date_range_from = datetime.datetime(2019, 3, 14,    0, 0, 0)
        #date_range_to = datetime.datetime(2019, 3, 16,    0, 0, 0)    
        date_range_from = datetime.datetime(2015, 12, 1,    0, 0, 0) # 2015, 11, 20
        date_range_to = datetime.datetime(2015, 12, 15,    0, 0, 0)            
        print("Date range customized:",date_range_from,"to",date_range_to)
    
    # Load all relevant legs, in order of start-time
    # NOTE: In PostgreSQL, seems like there is no max number of parameters in the IN clause
    legs_db_rows = legs_dal.load_legs(ids_to_process, date_range_from, date_range_to)
    if legs_db_rows.rowcount > 0:
        max_trip_id_per_user = trips_dal.get_max_trip_id_per_user(date_range_from, date_range_to, ids_to_process)
        # Algorithm settings: 
        idle_times = {'ALL': datetime.timedelta(minutes = 10), 'CAR':datetime.timedelta(minutes = 5)} # defaults: 10, 5
        URBAN_LEG_MAX_TRAVEL_DISTANCE = 100 # km; default: 100
        trips = tslib.trip_detection.extract_trips_from_legs(legs_db_rows, max_trip_id_per_user, 
                                                             idle_times, 
                                                             urban_leg_max_km = URBAN_LEG_MAX_TRAVEL_DISTANCE)
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
    else:
        trips = []
        print()
        print("Note: No legs to process at the moment!")
        
    # Cache it just in case
    with open('./data/output/extracted-trips/extracted_trips_'+session_file_timestamp+'.data', 'wb') as file:
        pickle.dump(trips, file)

    print("---- ENDED ----")
    print("We have processed these date ranges:",date_range_from,"to",date_range_to)
    w.stop()
    elapsed_extract = w.get_elapsed()


# ======================================================================================
# Compute alternatives and store them --------------------------------
class ComputeAlternativesThread(tslib.threads.MyThread):
    """ For a batch of observed trips, compute OTP trips and store them """
    def __init__(self, trips, batch_info, db_engine, threading_lock):
        super().__init__()
        self.trips = trips
        self.batch_info = batch_info
        self.db_engine = db_engine
        self.threading_lock = threading_lock
        self.stored_well = 0
        self.stored_alts_well = 0
        self.not_stored = 0
        self.ignored_alternatives = 0
        self.elapsed_compute_otp = 0
        self.elapsed_thread_run = 0
                
    def run(self):
        w = tslib.common.StopWatch()
        w.start() # ---        
        super().run()
        self.db_session = DatabaseSession(self.db_engine)
        self.db_command_transactional = DatabaseCommandsTransactional(self.db_session)
        self.db_command_non_transactional = DatabaseCommandsNonTransactional(self.db_engine)             

        trips_batch = self.trips
        print('---------- Processing trips batch, indexes', self.batch_info[0],'to',self.batch_info[1]-1,'-------------')
        # compute_missing_alternatives
        # NOTE: Makre sure to avoid race conditins with following global variables
        global stored_well
        global stored_alts_well
        global not_stored
        trips_with_computed_alts, ignored = self.compute_otp_trips(trips_batch, 
                                                                   retry_on_stored_failed_with_date_too_far=False,
                                                                   based_on_newly_extracted_trips=True)
        self.ignored_alternatives = ignored
                    
        #.compute attributes
        print("Computing attributes")
        trip_economics = TripEconomics(None)
        trip_economics.calculate_trips_alts_economics(trips_with_computed_alts)
        trip_economics.calculate_trips_economics(self.ignored_alternatives)
        # Test and overview: 
        #TEST_review_computed_alts(trips_with_computed_alts)

        print("Storing computed alternatives in DB")
        #.store the alternatives in db ('trips_alts' table)
        # & update relevant fields of the observed trips in db
        #   e.g.: start_time_for_plan field in db                
        trips_dal = dal.trips.Trips(self.db_command_transactional)
        self.db_session.start_transaction()
        try:
            # insert the new alternatives
            alts_inserted = trips_dal.store_trips_alternatives(trips_with_computed_alts)

            # update relevant fields of the observed trips 
            # update the start_time_for_plan (indicates whether the stroed otp plan alternative have been shifted or not)
            trips_dal.update_trip_starttime_shifted_for_otp_query(trips_with_computed_alts)                
            
            # commit only if all previous steps are complete
            self.db_session.commit_transaction() # WARNING. commits, if using the same 'db_session', need to be locked among threads.
            # print("DB operations trasaction successful ***")
            self.threading_lock.acquire()
            stored_well += len(trips_with_computed_alts)
            stored_alts_well += alts_inserted
            self.threading_lock.release()            
        except Exception as e:
            self.db_session.rollback_transaction()
            self.threading_lock.acquire()
            not_stored += len(trips_with_computed_alts)
            self.threading_lock.release()
            print("Error! EXCEPTION! Storing the alternatives in DB FAILED; DB session rolled back.")
            print("exception:", e)
        finally:
            pass
        w.stop()
        self.elapsed_thread_run = w.get_elapsed()
        

    def compute_otp_trips(self, ref_trips, force_date_shift_to_current_week=False, retry_on_stored_failed_with_date_too_far=False, based_on_newly_extracted_trips=False):
        """ 
        NOTE: What value to pass for 'retry_on_stored_failed_with_date_too_far', depends on whether we run periodically on a server, and some other factors.
        When running the code in good time periodically, GTFS files for OTP are up-to-date. Therefore, if a PT planning has failed with 404/406 for the original trip start-date, this means that actually no transit route or schedule existed, and we would rather NOT retry planning PT with a shifted-date. Therefore we set retry_on_stored_failed_with_date_too_far=False.
        
        Example settings typical for server/periodic runs:
            retry_on_stored_failed_with_date_too_far = False
            based_on_newly_extracted_trips = True
        
        NOTE: Failure OTP responses are also always stored in the cache DB table.
        """
        w = tslib.common.StopWatch()
        w.start() # ---
        
        otp_planer_api_uri = 'http://api.digitransit.fi/routing/v1/routers/hsl/plan'
    
        # trip planners: 
        trip_plans_dal = dal.trip_plans.TripPlans(self.db_command_non_transactional)
        webnet = WebNetworking()
        planner_config = OTPTripPlannerConfig()
        planner_config.DEBUG_MODE = DEBUG_MODE
        planner_config.FROM_NEWLY_EXTRACTED_TRIPS = based_on_newly_extracted_trips
        # NOTE: Important settings, adjust depending on what is the nature of ref_trips 
        #planner_config.RETRY_ON_ALL_STORED_PLANS = True
        #planner_config.RETRY_ON_ALL_STORED_OTP_ERRORS = True
        planner_config.RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR = retry_on_stored_failed_with_date_too_far
        if force_date_shift_to_current_week:
            planner_config.PLAN_ONLY_WITH_SHIFTED_DATE = True
        planner = OTPTripPlanner(webnet, trip_plans_dal, otp_planer_api_uri, planner_config,
                                 self.threading_lock) # is passed a DAL class that has a non-transactional Command object
    
        #.prepare the list of trips of Trip class type
        trip_objects_for_otp_query = ref_trips
        
        # Plan otp trips and attach the resulting alternatives to each observed Trip object
        # Also stores the (OTP) route plans or errors in 'trip_plans' table, as cache        
        trips_with_computed_alts, ignored_alternatives = tslib.trip_computation.compute_trips_alternatives(
                                                            planner,
                                                            trip_objects_for_otp_query,
                                                            desired_modes=['WALK', 'BICYCLE', 'CAR', 'PUBLIC_TRANSPORT'])
            
        print("Total no of OTP records restored from DB cache =", planner.no_of_loaded_plans_from_cache)
        print("Total no of new OTP queries sent =", planner.no_of_queries_sent)
        print("Total no of ignored plans not linked to observed trips =", len(ignored_alternatives))
        
        w.stop()
        self.elapsed_compute_otp = w.get_elapsed()
        
        return trips_with_computed_alts, ignored_alternatives

# --------------------------------
trips_loaded = trips # Usually, on a server and running periodically, this is what we need
#trips_loaded = session_data.observed_trips
threads = []
stopwatch_compute = tslib.common.StopWatch()

if COMPUTE_ALT_TRIPS and len(trips_loaded) > 0:
    stopwatch_compute.start()

    print(); print('Computing alternative trips ...')
    print('Observed trips: Count =', len(trips_loaded))
    
    # filter out trips outside target otp region
    trips_within_region = []
    trips_outside_region = []
    for trip in trips_loaded:
        if tslib.trip_detection.is_trip_in_region(trip, TARGET_REGION_FOR_OTP):
            trips_within_region.append(trip)
        else:
            trips_outside_region.append(trip)
    print('Computing only for trips with OD located within',TARGET_REGION_FOR_OTP,'region; Count =',len(trips_within_region),'observed trips; ...'); print()

    # For parallel:
    MAX_THREAD_COUNT = 4
    MAX_BATCH_SIZE = 100 # NOTE: Need a max batch-size, for example to avoid OTP server overload and connection refusal
                         # TODO: Maybe POST and GET are different? 
                         #       If error is due to actual connections, possible to use the same tcp/ip connection?    
    ideal_batch_size = tslib.threads.get_ideal_batch_size(trips_within_region, MAX_THREAD_COUNT)
    batch_size = min(ideal_batch_size, MAX_BATCH_SIZE)  # example custom values: 25, 50, 100    
    #batch_size = 12 # Custom batch size. Comment if not intended
    util = tslib.threads.get_util(trips_within_region, MAX_THREAD_COUNT, batch_size)
    run_rounds = tslib.threads.get_run_rounds(trips_within_region, MAX_THREAD_COUNT, batch_size)
    report_parallel_settings() 
    # 
    mylock = threading.Lock()

    stored_well = 0
    stored_alts_well = 0
    not_stored = 0
    OTPTripPlanner.reset_queires_sent()
    
    # Loop of compute trips -------------------------
    for i in range(0, len(trips_within_region), batch_size):        
        tslib.threads.wait_until_have_free_thread_capacity(threads, MAX_THREAD_COUNT)
        
        batch_from = i
        batch_to = min(i+batch_size, len(trips_within_region))
        trips_batch = trips_within_region[batch_from: batch_to]        
        
        thread = ComputeAlternativesThread(trips_batch, batch_info=(batch_from, batch_to), db_engine=db_engine, threading_lock=mylock)
        threads.append(thread)
        thread.start()

    # Finally, wait for all the threads to complete
    tslib.threads.wait_until_all_threads_end(threads)
    print("Now we continue.")
    print()
    
    # Summarize threads
    ignored_alternatives = []    
    for th in threads:
        ignored_alternatives.extend(th.ignored_alternatives)
    
    stopwatch_compute.stop()
    # --------------------------------------------------

    if DEBUG_MODE:
        OTPTripPlanner.save_queires_sent_to_file('./logs/trip_plan_queries_'+session_file_timestamp+'.csv')            
        save_ignored_trips_brief_to_file(ignored_alternatives, './logs/computed_trips_ignored_'+session_file_timestamp+'.csv')
    
    print()
    # TODO: OTPTripPlanner variables (.eg. __no_of_queries_sent) are not thread safe with += operation. Use a lock if multithreading.
    print("Total no of OTP records restored from DB cache =", OTPTripPlanner.get_no_of_loaded_plans_from_cache())
    print("Correct plans =", OTPTripPlanner.get_no_of_correct_plans_loaded_from_cache())    
    print("Planning errors =", OTPTripPlanner.get_no_of_loaded_plans_from_cache() - OTPTripPlanner.get_no_of_correct_plans_loaded_from_cache())
    print("Total no of new OTP queries sent =", OTPTripPlanner.get_no_of_queries_sent())
    print("Correct plans =", OTPTripPlanner.get_no_of_queries_sent()-OTPTripPlanner.get_no_of_planning_errors_from_queries())
    print("Planning errors =", OTPTripPlanner.get_no_of_planning_errors_from_queries())
    print("Total no of deleted (and replaced) plans in our DB cache =", OTPTripPlanner.get_no_of_deleted_plans_from_cach())
    print("Total no of ignored plans not linked to observed trips =", len(ignored_alternatives))
    
    print()
    print("Total no of trips that their alternatives were linked and stored in trips_alts table =", stored_well)
    print("Total no of alternatives linked and stored in trips_alts table =", stored_alts_well)
    print("Total no of trips with failed storing or linking of alternatives =", not_stored)
    print("---- ENDED ----")
    print()

stopwatch_all.stop()
print("Elapsed for extracting trips:", round(elapsed_extract),'seconds')
print("Elapsed for computing alternative trips:", round(stopwatch_compute.get_elapsed()),'seconds')    
i = 0
for th in threads:
    print('\tthread',i,'elapsed',round(th.elapsed_thread_run))
    i += 1
print("Elapsed total:", round(stopwatch_all.get_elapsed()),'seconds')
print()

if COMPUTE_ALT_TRIPS and DEBUG_MODE and len(trips_loaded) > 0:
    save_extracted_trips_brief_to_file(trips_within_region, './data/output/extracted-trips/extracted_trips_'+session_file_timestamp+'_within_region.csv')
    save_extracted_trips_brief_to_file(trips_outside_region, './data/output/extracted-trips/extracted_trips_'+session_file_timestamp+'_outside_region.csv')

if COMPUTE_ALT_TRIPS:
    report_parallel_settings()
    # Ideal Util value is 1.0
    # Recommendation: Set batch_size to 'ideal_batch_size' to achieve util = 1.0
    # if util < 1: Number of parallel threads ran would be less than max possible parallel threads
        

    