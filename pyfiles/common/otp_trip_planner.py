
import json
import datetime
from copy import deepcopy

from pyfiles.common_helpers import (shift_time_to_specific_date, pointRow_to_geoText)
from commonlayer.logger import(log, loge, logi, logexc)
from pyfiles.common.trip import(Trip)
from pyfiles.common.modalchoice import (PublicTransportModesTemplate)
from pyfiles.common.trip_planner_base import (TripPlannerBase, TripPlanningResult, StoredPlanLoadResult, TripPlannerConfig)

# constants
OTP_ERROR_CODE_DATE_TOO_FAR = 406
OTP_ERROR_CODE_NO_PATH_POSSIBLE = 404

# run settings and config
#RETRY_ON_ALL_STORED_PLANS = True   # repeats OTP trip planning always (even if such trip plan has been already stored in our cache 'trip_plans' DB table)
#RETRY_ON_ALL_STORED_OTP_ERRORS = False  # enable, for example if OTP server algorithm changes or we can provide better O/D to suppress 'path not found 404' error
#RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR = True

class OTPTripPlannerConfig(TripPlannerConfig):
    def __init__(self):
        # run settings and config
        TripPlannerConfig.__init__(self)
        self.RETRY_ON_ALL_STORED_PLANS = False
        self.RETRY_ON_ALL_STORED_OTP_ERRORS = False  # enable, for example if OTP server algorithm changes or we can provide better O/D to suppress 'path not found 404' error
        self.RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR = False
        self.PLAN_ONLY_WITH_SHIFTED_DATE = False


class OTPTripPlanner(TripPlannerBase):

    def _query_a_trip_plan(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops):
        log("")
        log(["_query_a_trip_plan::Requesting to OTP journey planner:"])
        log(["Input desired_trip:", desired_trip.starttime, ",", desired_transport_mode])        
        
        # Send our query to OTP journey planner:        
        # Example: 
        #   querystr = "fromPlace=60.170718,24.930221&toPlace=60.250214,25.009566&date=2016/4/22&time=17:18:00&numItineraries=3&maxTransfers=3&maxWalkDistance=1500"

        if desired_transport_mode == 'PUBLIC_TRANSPORT' or desired_transport_mode in PublicTransportModesTemplate:
            querystr = """fromPlace={0}&toPlace={1}&date={2}&time={3}&numItineraries={4}&maxWalkDistance={5}&showIntermediateStops={6}""".format(
                        pointRow_to_geoText(desired_trip.origin), pointRow_to_geoText(desired_trip.destination), 
                        desired_trip.starttime.date().isoformat(), desired_trip.starttime.time().isoformat(),
                        num_of_itineraries, max_walk_distance, show_intermediate_stops
                        )
        else:
            querystr = """fromPlace={0}&toPlace={1}&date={2}&time={3}&numItineraries={4}&mode={5}""".format(
                        pointRow_to_geoText(desired_trip.origin), pointRow_to_geoText(desired_trip.destination),
                        desired_trip.starttime.date().isoformat(), desired_trip.starttime.time().isoformat(),
                        num_of_itineraries, desired_transport_mode
                        )
                        
        webres, response_content_str = self.webnet.send_http_get(self.api_url, querystr)

        if type(response_content_str) == bytes:
            response_content_str = response_content_str.decode()
        
        return self._parse_webnet_response(webres, response_content_str)
        
# TODO: OLD CODE //REMOVE                    
#        res, res_collection = self.webnet.HttpRequestWithGET(apiurl, querystr)     
#        # TODO: IMPORTANT : build_response_collection_from_response_string(res, res_str, exception_class_type, exception)
#
#        if 'plan' not in res_collection or 'itineraries' not in res_collection['plan']:
#            if 'error' in res_collection:
#                return 0, None, res_collection['error'], res_collection
#            else:
#                return 0, None, '{"id":0, "msg":"", "message":""}', res_collection
#        else:
#            return 1, res_collection['plan'], None, res_collection
    
                
    def _restore_a_trip_plan_from_cache(self, desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance):        
        is_desired_trip_date_shifted = False
        desired_trip_with_shifted_date = None        
        is_otp_error = False
        plan_made_before = False
        already_restored_the_shifted_date_plan = False
                
        #TODO important, later, possible BUG: if 'itin_starttime' (planned) differs a bit from the stored 'desired_trip.starttime' (desired) ... some plans may get lost ??!
        # one solution: use the requestedParameters['date'] and ['time'] instead of values from itin ???                
        res, plan, error, planning_response = self._load_plan_already_stored(desired_trip, desired_transport_mode, 
                                                                             num_of_itineraries, max_walk_distance)                
        #print("First try of loading plan from DB; res = ", res)
        # TODO. Changes made during Moprim
        #if res == 0 and error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE:
        #    pass
            
        # second try (adjust the old weekday to current week) from DB        
        if res == 0 and (error['id'] == OTP_ERROR_CODE_DATE_TOO_FAR \
                         #TODO: important Moprim changes!
                         # TODO: NOTE: shifting to current week only is useful for PT trips ***
                         or (error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE and desired_transport_mode=='PUBLIC_TRANSPORT')
                        ):
            log(["_restore_a_trip_plan_from_cache(): for trip ("+ str(desired_trip.user_id) + " " + str(desired_trip.id)+"), mode "+desired_transport_mode, 
                  "load from DB successful.",
                  "But trip planning HAD FAILED because loaded record has: OTP error (error['id']={})".format(error['id'])])
            log(["Loading second time from DB, with the shifted date (either 'trips.shifted_starttime_for_publictransport_tripplan' or time current week) ..."])

            is_desired_trip_date_shifted = True # ***
            desired_trip_with_shifted_date = deepcopy(desired_trip)
            if desired_trip.shifted_starttime_for_publictransport_tripplan is not None: # if already shifted in a previous run, load from DB record values
                #print("TEMP MESSAGE: references-trip shifted-date for PT planning:", desired_trip.shifted_starttime_for_publictransport_tripplan)
                desired_trip_with_shifted_date.starttime = desired_trip.shifted_starttime_for_publictransport_tripplan
            else: # if not already shifted, do it here, try for same weekday in current week 
                print("Warning! References-trip shifted-date for PT planning NULL; Shifting the date here!!!")
                desired_trip_with_shifted_date.starttime = self.find_same_journey_time_this_week(desired_trip.starttime)
            # update the end-time too, for backwards compatibility
            desired_trip_with_shifted_date.endtime = shift_time_to_specific_date(desired_trip.endtime, desired_trip_with_shifted_date.starttime) #TODO ... no separate data field for endtime ?!!! 
            #print("TEMP MESSAGE: desired_trip_with_shifted_date:", desired_trip_with_shifted_date.starttime)
            
            old_error = error
            old_planning_response = planning_response
            
            res, plan, error, planning_response = self._load_plan_already_stored(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance)                    
            if res:
                log(["SUCCESS: date shifted-forward trip plan found in DB ==> using it ..."])
                # TODO: WARNING! test dummy use only if needed to REMOVE trip-plans for test!!! 
                # TODO: WARNING! self.trip_plans_dal.delete_trip_plan(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance)
            elif self._has_trip_planning_error(planning_response):
                already_restored_the_shifted_date_plan = True
                logi(["ERROR: date shifted-forward trip plan found; But trip planning HAD FAILED again because (error['id']={})".format(error['id'])])
                # TODO: WARNING! test dummy use only if needed to REMOVE trip-plans for test!!! 
                # TODO: WARNING! self.trip_plans_dal.delete_trip_plan(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance)
            elif error['id'] == 0:
                # restore original error id and message
                error = old_error
                planning_response = old_planning_response                
                loge(["ERROR: date shifted-forward trip plan NOT found in DB"])
            #loge([""]) #TODO!!! revert

        # summarize the result:
        if res == 0 and self._has_trip_planning_error(planning_response):
            error['message'] = "_restore_a_trip_plan_from_cache() - " + error['message']            
            is_otp_error = True
        elif res == 1:
            plan_made_before = True
            self._increase_no_of_correct_plans_loaded_from_cache()

        restore_res = StoredPlanLoadResult()
        restore_res.set(res, plan, error, planning_response, 
                        is_desired_trip_date_shifted, desired_trip_with_shifted_date, 
                        is_otp_error, 
                        plan_made_before,
                        already_restored_the_shifted_date_plan)            
        return restore_res
                
    # trip planning logic, config and main calls here: 
    def plan_a_trip(self, reference_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops):
        log("")
        log(["plan_a_trip::Input reference trip: ", reference_trip.starttime, \
              ":  from ", pointRow_to_geoText(reference_trip.origin), "--> to", pointRow_to_geoText(reference_trip.destination)])

        desired_trip = deepcopy(reference_trip) # keep a copy, in order to not change the input params in the caller's scope                
        desired_trip.starttime = desired_trip.starttime.replace(microsecond = 0)
        desired_trip.endtime = desired_trip.endtime.replace(microsecond = 0)

        # query journey planner --------------:        
        is_desired_trip_date_shifted = False        
        shifted_starttime = None
        
        plan = None
        res = 0
        error = None
        planning_response = None
        restored_plan = StoredPlanLoadResult()
        
        # if such OTP plan is (requested and) stored before, just use it!
        if not self.config.RETRY_ON_ALL_STORED_PLANS:
            #TODO important, later, possible BUG: if 'itin_starttime' (planned) differs a bit from the stored 'desired_trip.starttime' (desired) ... some plans may get lost ??!
            # one solution: use the requestedParameters['date'] and ['time'] instead of values from itin ???            
            restored_plan = self._restore_a_trip_plan_from_cache(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance)
            res = restored_plan.res
            plan = restored_plan.plan
            error = restored_plan.error
            planning_response = restored_plan.planning_response
            is_desired_trip_date_shifted = restored_plan.date_was_shifted_forward
            shifted_starttime = restored_plan.shifted_starttime
                                
        # depending on config flags and other conditions:
        # . if flag set: requery regardless of whether we already have the plan in cache
        # . if not loaded from previous plans
        #   . ....
        # send trip-planning query to OTP server:
        if self.config.RETRY_ON_ALL_STORED_PLANS or \
            (not restored_plan.plan_made_before and \
             ((not restored_plan.is_otp_error) or \
              (self.config.RETRY_ON_ALL_STORED_OTP_ERRORS) or\
              (self.config.RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR and \
               (restored_plan.error['id'] == OTP_ERROR_CODE_DATE_TOO_FAR or restored_plan.error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE))\
             )\
            ):
            # TODO: important changes made to the above id condition during moprim (both 404 and 406 errors treated thesame)
            
            res, plan, error, all_response = self._query_a_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops)        
            # TODO: WARNING! dummy test only, to help regenerate the error: ValueError('No JSON object could be decoded',) is not JSON serializable
            #   error['id'] = OTP_ERROR_CODE_DATE_TOO_FAR
            
            if res == 0 \
                and (error['id'] == OTP_ERROR_CODE_DATE_TOO_FAR \
                     or error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE): #TODO: OTP_ERROR_CODE_NO_PATH_POSSIBLE added during MOprim data processing. Both 404 and 406 errors are now somehow synonyms
            # second try (adjust the old weekday to current week)
                #store this 'intermediate' error trip-plan response for later use ***
                self._store_planning_error(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response)
                
                # shift the old weekday to current week, and call OTP planner again
                logi(["plan_a_trip():: FAILED for trip ("+str(desired_trip.user_id)+ " " +str(desired_trip.id)+") -"+ desired_transport_mode+
                      ": OTP error code=",error['id']+"; Trying a second time with shifted date to current week..."])
                is_desired_trip_date_shifted = True # ***                
                desired_trip_with_shifted_date = self._shift_trip_to_current_week(desired_trip) # TODO: function algorithm has changed during Moprim ... probably suitable for other TrafficSense data sources too
                shifted_starttime = desired_trip_with_shifted_date.starttime
#               OLD CODE:                
#                desired_trip_with_shifted_date = deepcopy(desired_trip)            
#                desired_trip_with_shifted_date.starttime = self.find_same_journey_time_this_week(desired_trip.starttime)
#                desired_trip_with_shifted_date.endtime = self.find_same_journey_time_this_week(desired_trip.endtime)
                res, plan, error, all_response = self._query_a_trip_plan(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops) 
                if res == 1: 
                    #store this 'shifted' trip-plan-response for later use ***
                    self._store_planning_result(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                    log(["plan_a_trip() SUCCESS with shifted time"])
                elif res == 0 and self._has_trip_planning_error(all_response): # only save errors related to trip planning, OTP and so on (NOT the network, exceptions, own custom etc. errors)
                    #store this error trip-plan response for later use ***
                    self._store_planning_error(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
            elif res == 0 and self._has_trip_planning_error(all_response):
                #store this error trip-plan response for later use ***
                self._store_planning_error(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response)
            elif res == 1: 
                #store this trip-plan-response for later use ***
                self._store_planning_result(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                
        # summarize after trip planning is done: -------------------
        if res == 1 and (plan is None or 'itineraries' not in plan):
            if plan is not None:
                raise Exception("res == 1 but plan is: {}".format(json.dumps(plan)))
            else:
                raise Exception('res == 1 but plan is None')

        trip_planning_res = TripPlanningResult()
        if res == 0:
            if error is not None:
                trip_planning_res.error_code = error['id']
                trip_planning_res.error_msg = error['msg']
                trip_planning_res.error_message =  error['message']
                return 0, None, trip_planning_res
            else:
                return 0, None, trip_planning_res
        elif res == 1:
            if is_desired_trip_date_shifted:
                trip_planning_res.is_desired_trip_date_shifted = is_desired_trip_date_shifted
                trip_planning_res.desired_trip_shifted_starttime = shifted_starttime
        
        # build trip objects to return to caller: --------------------------
        # go through all trip-leg-chains suggested, to build a collection of Trip objects, and return it :   
        log("")
        log(["Working on the itins (routes) suggested by otp journey planner ...:"])
        itin_index = 0
        matchcount = 0
        plannedmatches = [] # TODO: choose which returned trip? 
                            # e.g. when 3 public transport trips are returned * order based on what?
        trips = []
        
        for itin in plan['itineraries']: 
            trip = Trip()
            trip.update_from_otp_trip_plan(desired_trip, is_desired_trip_date_shifted, plan, itin)

            # TODO: WARNING!! unit/integrate test. 
            # Is the diff in 'trips_alts' table because of following change?! ******************
#            trip.user_id = desired_trip.user_id
#            trip.device_id = desired_trip.device_id
#            trip.id = desired_trip.id            
#            itin_starttime = OTPTimeStampToNormalDateTime(itin['startTime'])
#            itin_endtime = OTPTimeStampToNormalDateTime(itin['endTime'])
#            # trip.shifted_starttime_for_publictransport_tripplan = itin_starttime # no need to use this field for alternative plans? (plan_id > 0)
#            if is_desired_trip_date_shifted:
#                trip.starttime = shift_time_to_specific_date(itin_starttime,  desired_trip.starttime) # TODO: NOTE: starttime of plan may differ from desired trip start-time (???)
#                trip.endtime = shift_time_to_specific_date(itin_endtime,  desired_trip.endtime)
#            else: 
#                trip.starttime = itin_starttime # TODO: NOTE: starttime.time()/endtime of planned itinerary may differ *a bit* from desired trip start-time.time/endtime (???)
#                trip.endtime = itin_endtime
#            trip.origin = geoLoc_to_pointRow(plan['from']['lat'], plan['from']['lon']) # TODO: are there cases where plan's origin{lat,lon} differ a bit from desired trip origin?!
#            trip.destination = geoLoc_to_pointRow(plan['to']['lat'], plan['to']['lon']) # TODO: are there cases where plan's destination{lat,lon} differ a bit from desired trip destination?!
#            # trip.legs = itin['legs'] #TODO remove old code?
#            trip.append_otp_legs(itin['legs'],  is_desired_trip_date_shifted, desired_trip.starttime,  desired_trip.endtime)
            
            trips.append(trip)
            
        return 1, trips, trip_planning_res


    # trip planning logic, config and main calls here: 
    def plan_a_trip_new(self, reference_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops):
        log("")
        log(["plan_a_trip::Input reference trip: ", reference_trip.starttime, \
              ":  from ", pointRow_to_geoText(reference_trip.origin), "--> to", pointRow_to_geoText(reference_trip.destination)])

        desired_trip = deepcopy(reference_trip) # keep a copy, in order to not change the input params in the caller's scope

        # query journey planner --------------:        
        is_desired_trip_date_shifted = False        
        shifted_starttime = None
        
        plan = None
        res = 0
        error = None
        planning_response = None
        restored_plan = StoredPlanLoadResult()
        
        
        if self.config.PLAN_ONLY_WITH_SHIFTED_DATE:
            # shift the old weekday to current week, and call OTP planner again
            logi(["plan_a_trip_new() Force shifting date to current week, for trip ("+str(desired_trip.user_id)+ " " +str(desired_trip.id)+") -"+ desired_transport_mode])
            is_desired_trip_date_shifted = True # ***                
            desired_trip_with_shifted_date = self._shift_trip_to_current_week(desired_trip)
            shifted_starttime = desired_trip_with_shifted_date.starttime
            res, plan, error, all_response = self._query_a_trip_plan(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops)                

            if res == 1: 
                #store this 'shifted' trip-plan-response for later use ***
                self._store_planning_result(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                logi(["plan_a_trip_new() SUCCESS with shifted time"])
            elif res == 0 and self._has_trip_planning_error(all_response): # only save errors related to trip planning, OTP and so on (NOT the network, exceptions, own custom etc. errors)
                #store this error trip-plan response for later use ***
                self._store_planning_error(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                
        else:        
            # if such OTP plan is (requested and) stored before, just use it!
            if not self.config.RETRY_ON_ALL_STORED_PLANS:
                #TODO important, later, possible BUG: if 'itin_starttime' (planned) differs a bit from the stored 'desired_trip.starttime' (desired) ... some plans may get lost ??!
                # one solution: use the requestedParameters['date'] and ['time'] instead of values from itin ???            
                restored_plan = self._restore_a_trip_plan_from_cache(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance)
                res = restored_plan.res
                plan = restored_plan.plan
                error = restored_plan.error
                planning_response = restored_plan.planning_response
                is_desired_trip_date_shifted = restored_plan.date_was_shifted_forward
                shifted_starttime = restored_plan.shifted_starttime
    
            if restored_plan.already_restored_the_shifted_date_plan:
                print("NOTE: restored_plan.already_restored_the_shifted_date_plan")
            
            # depending on config flags and other conditions:
            # . if flag set: requery regardless of whether we already have the plan in cache
            # . if not loaded from previous plans
            #   . ....
            # send trip-planning query to OTP server:
            if self.config.RETRY_ON_ALL_STORED_PLANS or \
                (not restored_plan.plan_made_before and \
                     ((not restored_plan.is_otp_error) or (self.config.RETRY_ON_ALL_STORED_OTP_ERRORS) or\
                       (self.config.RETRY_ON_STORED_OTP_ERROR_DATE_TOO_FAR and \
                            (not restored_plan.already_restored_the_shifted_date_plan) and\
                            (restored_plan.error['id'] == OTP_ERROR_CODE_DATE_TOO_FAR\
                             # TODO: NOTE: shifting date to current week only is useful for PT trips ***
                             or (restored_plan.error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE and desired_transport_mode=='PUBLIC_TRANSPORT')
                             )
                        )\
                 )\
                ):
                                                      
                
                
                # TODO: important changes made to the above id condition during moprim (both 404 and 406 errors treated thesame)
                
                res, plan, error, all_response = self._query_a_trip_plan(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops)        
                # TODO: WARNING! dummy test only, to help regenerate the error: ValueError('No JSON object could be decoded',) is not JSON serializable
                #   error['id'] = OTP_ERROR_CODE_DATE_TOO_FAR
                
                if res == 0 \
                    and (error['id'] == OTP_ERROR_CODE_DATE_TOO_FAR \
                         #TODO: OTP_ERROR_CODE_NO_PATH_POSSIBLE added during MOprim data processing. Both 404 and 406 errors are now somehow synonyms fot PT
                         # TODO: NOTE: shifting date to current week only is useful for PT trips ***
                         or (error['id'] == OTP_ERROR_CODE_NO_PATH_POSSIBLE and desired_transport_mode=='PUBLIC_TRANSPORT')                     
                        ):            
                    # second try (adjust the old weekday to current week) ---------------------
                    #store this 'intermediate' error trip-plan response for later use ***
                    self._store_planning_error(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response)
                    
                    # shift the old weekday to current week, and call OTP planner again
                    logi(["plan_a_trip_new() FAILED for trip ("+str(desired_trip.user_id)+ " " +str(desired_trip.id)+") -"+ desired_transport_mode+
                          ": OTP ERROR CODE="+str(error['id'])+"! => Trying second time with current week..."])
                    is_desired_trip_date_shifted = True # ***                
                    desired_trip_with_shifted_date = self._shift_trip_to_current_week(desired_trip) # TODO: function algorithm has changed during Moprim ... probably suitable for other TrafficSense data sources too
                    shifted_starttime = desired_trip_with_shifted_date.starttime
                    
                    res, plan, error, all_response = self._query_a_trip_plan(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, show_intermediate_stops)                
                    if res == 1: 
                        #store this 'shifted' trip-plan-response for later use ***
                        self._store_planning_result(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                        log(["plan_a_trip_new() SUCCESS with shifted time"])
                    elif res == 0 and self._has_trip_planning_error(all_response): # only save errors related to trip planning, OTP and so on (NOT the network, exceptions, own custom etc. errors)
                        #store this error trip-plan response for later use ***
                        self._store_planning_error(desired_trip_with_shifted_date, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
                elif res == 0 and self._has_trip_planning_error(all_response):
                    #store this error trip-plan response for later use ***
                    self._store_planning_error(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response)
                elif res == 1: 
                    #store this trip-plan-response for later use ***
                    self._store_planning_result(desired_trip, desired_transport_mode, num_of_itineraries, max_walk_distance, all_response) 
        
        
        # summarize after trip planning is done: -------------------
        if res == 1 and (plan is None or 'itineraries' not in plan):
            if plan is not None:
                raise Exception("res == 1 but plan is: {}".format(json.dumps(plan)))
            else:
                raise Exception('res == 1 but plan is None')

        trip_planning_res = TripPlanningResult()
        # TODO: Important change: causes that shifted date is saved in trips_alts DB table, later in code
        if is_desired_trip_date_shifted:
            trip_planning_res.is_desired_trip_date_shifted = is_desired_trip_date_shifted
            trip_planning_res.desired_trip_shifted_starttime = shifted_starttime
        if res == 0:
            if error is not None:
                trip_planning_res.error_code = error['id']
                trip_planning_res.error_msg = error['msg']
                trip_planning_res.error_message =  error['message']
                return 0, None, trip_planning_res
            else:
                return 0, None, trip_planning_res
        elif res == 1:
            return 1, plan, trip_planning_res


    def _parse_planning_response(self, response_content_str):                                
        res = 0
        try:
            # response content from OTP servers is supposed to be in JSON string format (json text)
            response_collection = json.loads(response_content_str) 
            # TODO WARNING! dummy test only to regenerate occasional error 
            #   raise Exception('No JSON object could be decoded')            
        except Exception as e:
            # build our own custom collection ---:
            response_collection = self._make_response_collection(None, self._make_error_collection(0, "(!) EXCEPTION catched in _parse_planning_response()", str(e)))
            
            # response from OTP servers is supposed to be in JSON string format (json text)
            # ==> therefore this is an exception (unexpected): 
            logexc("(!) EXCEPTION catched in _parse_planning_response(): ", e, response_content_str)
        else: # (if no exception occured)
            if 'plan' not in response_collection or \
            response_collection['plan'] is None or \
            'itineraries' not in response_collection['plan']:
                # TODO: what to do?
                #itineraries_count = len (response_collection['plan']['itineraries'])
                #if itineraries_count == 0:
                #   raise Ecception("journey planner did NOT return any itineraries!\n")
                #   print "response_collection returned:\n", response_collection, "\n"
                #   print "response_collection error section:\n", response_collection['error']
                
                # build our own custome collection ---:
                if 'error' not in response_collection or response_collection['error'] is None:
                    response_collection["error"] = self._make_error_collection(0, "unknown planning error", "no \'plan\' in response, BUT also no \'error\' field")
                response_collection['plan'] = None
            else: # everything was OK!
                res = 1
                response_collection['error'] = None        
        
        return res, response_collection['plan'], response_collection['error'], response_collection

#    def _parse_planning_response(self, result_data_dict):
#        if 'plan' not in result_data_dict or 'itineraries' not in result_data_dict['plan']:
#            #itineraries_count = len (result_data_dict['plan']['itineraries'])
#            #if itineraries_count == 0:
#            # print "journey planner did NOT return any itineraries!\n"
#            # print "result_data_dict returned:\n", result_data_dict, "\n"
#            # print "result_data_dict error section:\n", result_data_dict['error']                        
#            if 'error' in result_data_dict:
#                return 0, None, result_data_dict['error'], result_data_dict
#            else:
#                return 0, None, json.loads('{"id":0, "msg":"", "message":""}'), result_data_dict
#        else:
#            return 1, result_data_dict['plan'], None, result_data_dict                
