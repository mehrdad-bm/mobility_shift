import json
from datetime import datetime
from datetime import timedelta
from copy import deepcopy
from commonlayer.logger import(log, loge, logi, logexc)
from pyfiles.common_helpers import (DateTime_to_Text)

class TripPlanningResult:
    def __init__(self):
        self.error_code = 0
        self.error_msg = ''
        self.error_message = ''
        self.is_desired_trip_date_shifted = False
        self.desired_trip_shifted_starttime = None
        self.planning_query = ''

    def to_Text(self):
        try:
            #return str(self.error_code)+ ", "+ self.error_msg+ ", "+ self.error_message
            return "{}, {}, {}".format(self.error_code, self.error_message, self.error_msg)
        except Exception as e:
            logexc(">> (!) EXCEPTION catched in TripPlanningResult::to_Text(): ", e)

class StoredPlanLoadResult: 
    def __init__(self):
        self.res = 0
        self.plan = None
        self.error = None
        self.planning_response = None
        self.is_otp_error = False
        self.date_was_shifted_forward = False
        self.shifted_starttime = None
        self.plan_made_before = False
        self.already_restored_the_shifted_date_plan = False
        
    def set(self, res, plan, error, planning_response, is_desired_trip_date_shifted, shifted_plan, is_otp_error, plan_made_before, already_restored_the_shifted_date_plan):
        self.res = res
        self.plan = plan
        self.error = error
        self.planning_response = planning_response
        self.date_was_shifted_forward = is_desired_trip_date_shifted
        if shifted_plan is not None:
            self.shifted_starttime = shifted_plan.starttime
        else:
            self.shifted_starttime = None
        self.is_otp_error = is_otp_error
        self.plan_made_before = plan_made_before
        self.already_restored_the_shifted_date_plan = already_restored_the_shifted_date_plan


class TripPlannerConfig:
    def __init__(self):
        # run settings and config
        self.RETRY_ON_ALL_STORED_PLANS = False   # repeats OTP trip planning always (even if such trip plan has been already stored in our cache 'trip_plans' DB table)

class TripPlannerBase:
    # static members and functions -----------------
    __no_of_queries_sent = 0
    __no_of_deleted_plans_from_cache = 0
    __no_of_planning_errors_from_queries = 0
    __no_of_loaded_plans_from_cache = 0
    __no_of_correct_plans_loaded_from_cache = 0
    
    @classmethod
    def reset_stats(cls):
        cls.__reset_no_of_queries_sent()
        cls.__reset_no_of_deleted_plans_from_cache()
        cls.__reset_no_of_planning_errors_from_queries()
        cls.__reset_no_of_loaded_plans_from_cache()
        cls.__reset_no_of_correct_plans_loaded_from_cache()
        
    @classmethod
    def __reset_no_of_queries_sent(cls):
        cls.__no_of_queries_sent = 0        
    @classmethod
    def _increase_no_of_queries_sent(cls):
        cls.__no_of_queries_sent += 1
    @classmethod
    def get_no_of_queries_sent(cls):
        return cls.__no_of_queries_sent
    
    @classmethod
    def __reset_no_of_deleted_plans_from_cache(cls):
        cls.__no_of_deleted_plans_from_cache = 0        
    @classmethod
    def _increase_no_of_deleted_plans_from_cach(cls, count):
        cls.__no_of_deleted_plans_from_cache += count
    @classmethod
    def get_no_of_deleted_plans_from_cach(cls):
        return cls.__no_of_deleted_plans_from_cache
    
    @classmethod
    def __reset_no_of_planning_errors_from_queries(cls):
        cls.__no_of_planning_errors_from_queries = 0        
    @classmethod
    def _increase_no_of_planning_errors_from_queries(cls):
        cls.__no_of_planning_errors_from_queries += 1
    @classmethod
    def get_no_of_planning_errors_from_queries(cls):
        return cls.__no_of_planning_errors_from_queries

    @classmethod
    def __reset_no_of_loaded_plans_from_cache(cls):
        cls.__no_of_loaded_plans_from_cache = 0        
    @classmethod
    def _increase_no_of_loaded_plans_from_cache(cls):
        cls.__no_of_loaded_plans_from_cache += 1
    @classmethod
    def get_no_of_loaded_plans_from_cache(cls):
        return cls.__no_of_loaded_plans_from_cache
    
    
    @classmethod
    def __reset_no_of_correct_plans_loaded_from_cache(cls):
        cls.__no_of_correct_plans_loaded_from_cache = 0        
    @classmethod
    def _increase_no_of_correct_plans_loaded_from_cache(cls):
        cls.__no_of_correct_plans_loaded_from_cache += 1
    @classmethod
    def get_no_of_correct_plans_loaded_from_cache(cls):
        return cls.__no_of_correct_plans_loaded_from_cache
    
    
    # ----------------------------------------------------
    
    def __init__(self, webnet, trip_plans_dal, api_url, config):
        self.webnet = webnet
        self.trip_plans_dal = trip_plans_dal
        self.api_url = api_url
        self.config = config

    def _make_error_collection(self, id, message, msg):
        error = {}
        error["id"] = id
        error["message"] = message
        error["msg"] = msg
        return error
    
    def _make_response_collection(self, plan, error):
        response_collection = {}
        response_collection['plan'] = plan
        response_collection['error'] = error
        return response_collection

    def _parse_webnet_response(self, webres, response_content_str):
        if webres:                        
            self._increase_no_of_queries_sent()
            # parse the returned response string ---
            res, plan, error, all_response = self._parse_planning_response(response_content_str)
            if self._has_trip_planning_error(all_response): 
                self._increase_no_of_planning_errors_from_queries()
            return res, plan, error, all_response            
        else:
            # webnet failed:
            res = 0
            response_collection = self._make_response_collection(
                None, 
                self._make_error_collection(0, "webnet.send_http_get() returned False", response_content_str))            
            return res, response_collection['plan'], response_collection['error'], response_collection

    def _has_trip_planning_error(self, planning_response):            
        if 'error' in planning_response and planning_response['error'] is not None and \
        planning_response['error']['id'] > 0: # Now, our custom erros, exceptions and so on have error-id = 0
            return True
        else:
            return False

    def plan_a_trip(self, reference_trip, desired_transport_mode):
        pass        

    def _query_a_trip_plan(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops):
        pass
    
    def _restore_a_trip_plan_from_cache(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance):
        pass
        
        
    def _parse_planning_response(self, response_content_str):
        pass

    # ~~~ cache functinality (trip_plans DB table) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _store_planning_error(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, planning_response):
        res, count = self.trip_plans_dal.delete_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance)
        if res: 
            self._increase_no_of_deleted_plans_from_cach(count)
        self.trip_plans_dal.store_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, planning_response) 

    def _store_planning_result(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, planning_response):
        if self.config.RETRY_ON_ALL_STORED_PLANS:
            res, count = self.trip_plans_dal.delete_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance)
            if res:
                self._increase_no_of_deleted_plans_from_cach(count)
        self.trip_plans_dal.store_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, planning_response) 

    def _load_plan_already_stored(self, trip, mode, num_of_itineraries, max_walk_distance):        
        res, plan_rows = self.trip_plans_dal.load_trip_plan(trip, mode, num_of_itineraries, max_walk_distance)                        
        if res and plan_rows.rowcount > 0:
            #print("TEMP MESSAGE: TRIP-PLAN LOADED FROM DB. trip (",trip.user_id,trip.id,"), for mode", mode)

            plan_row = plan_rows.fetchone()            
            plan_json_str = '{}'
            if type(plan_row['plan']) == dict:
                plan_json_str = json.dumps(plan_row['plan'])
                #print("TEMP MESSAGE: trip ID",trip.id,", for mode", mode,": plan_row['plan'] is dict. Converted to json-str")
            else:
                plan_json_str = plan_row['plan']
                
            self._increase_no_of_loaded_plans_from_cache()

            return self._parse_planning_response(plan_json_str) # pass the DB Row's 'plan' field to this function
        else:
            #print("TEMP MESSAGE: TRIP-PLAN NOT FOUND IN DB. trip (",trip.user_id,trip.id,"), for mode", mode)
            res = 0
            response_collection = self._make_response_collection(
                None, 
                self._make_error_collection(0, "trip_plan not found in DB", "Such trip plan not stored in trip_plans before"))                                                    
            return res, response_collection['plan'], response_collection['error'], response_collection
            #return self._parse_planning_response(planning_response)        
            # return 0, None, json.loads('{"id":0, "msg":"", "message":"Such trip plan not stored before"}'), None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    @classmethod
    # TODO OLD CODE. This was changed during Moprim data processing
#    def find_same_journey_time_this_week(cls, original_date_time):
#        # find date of the same weekday, but for current week (to avoid querying old dates that results in error from HSL)
#        date_thisweek = datetime.today() + timedelta(days = (original_date_time.weekday() - datetime.today().weekday()))
#        time_thisweek = datetime.combine(date_thisweek.date(), original_date_time.time())
#        log(["find_same_journey_time_this_week():: original_date_time:",original_date_time," --> same_journey_time_this_week:", time_thisweek])
#        return time_thisweek            

    # probably a better approach ... because algorithm depends on the current day (of calculation)
    def find_same_journey_time_this_week(cls, original_date_time):
        # find date of the same weekday, but for current week (to avoid querying old dates that results in error from HSL)              
        if original_date_time.weekday() < datetime.today().weekday():
            reference_date = datetime.today() + timedelta(weeks = 1)
        else:
            reference_date = datetime.today()  
        date_thisweek = reference_date + timedelta(days = (original_date_time.weekday() - reference_date.weekday()))        
        time_thisweek = datetime.combine(date_thisweek.date(), original_date_time.time())
        log(["find_same_journey_time_this_week():: original_date_time:"+DateTime_to_Text(original_date_time)+
              " --> same journey time this or next week:" + DateTime_to_Text(time_thisweek) ])
        return time_thisweek            

    def _shift_trip_to_current_week(self, trip):
        trip_with_shifted_date = deepcopy(trip)            
        trip_with_shifted_date.starttime = self.find_same_journey_time_this_week(trip.starttime)
        trip_with_shifted_date.endtime = self.find_same_journey_time_this_week(trip.endtime)
        return trip_with_shifted_date

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

