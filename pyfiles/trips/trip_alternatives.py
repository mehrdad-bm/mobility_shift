import datetime
from copy import deepcopy

from pyfiles.common_helpers import (pointRow_to_geoText, round_dict_values, DateTime_to_Text, DateTimeDelta_to_Text, point_distance)
from pyfiles.common.modalchoice import (PublicTransportModesTemplate)
from pyfiles.common.modalchoice import (ModalChoice, CarNonCarEnum)
from commonlayer.logger import(log, loge, logi, logexc)
from commonlayer.common_helper_class import (CommonHelper)
from pyfiles.common.trip import(Trip)

MAX_MODE_DETECTION_DELAY = 500 # (meters) In other words: inaccuracy (delay) in detecting transition point. We have latency in making sure of the mode change 

# -----------------------------------------

UserModalChoiceTemplate = {'CAR':0, 'PUBLIC_TRANSPORT':0, 'BICYCLE':0, 'WALK':0}

PlanIDModeTemplate = {"plan_id":None, "mode": None}
BestModalChoiceByParamTemplate = {'time':deepcopy(PlanIDModeTemplate), 'cost':deepcopy(PlanIDModeTemplate), \
                                  'emission':deepcopy(PlanIDModeTemplate), 'cals':deepcopy(PlanIDModeTemplate), 'comfort':deepcopy(PlanIDModeTemplate)}

CarPublicTemplate = {'CAR':0, 'PUBLIC_TRANSPORT':0}
CLCarPublicTemplate = {'time':deepcopy(CarPublicTemplate), 'cost':deepcopy(CarPublicTemplate), \
                       'emission':deepcopy(CarPublicTemplate), 'cals':deepcopy(CarPublicTemplate), 'comfort':deepcopy(CarPublicTemplate)}                       

CarPublicBikeTemplate = {'CAR':0, 'PUBLIC_TRANSPORT':0, 'BICYCLE':0}
CLCarPublicBikeTemplate = {'time':deepcopy(CarPublicBikeTemplate), 'cost':deepcopy(CarPublicBikeTemplate), \
                           'emission':deepcopy(CarPublicBikeTemplate), 'cals':deepcopy(CarPublicBikeTemplate), 'comfort':deepcopy(CarPublicBikeTemplate)}

CarPublicWalkTemplate = {'CAR':0, 'PUBLIC_TRANSPORT':0, 'WALK':0}
CLCarPublicWalkTemplate = {'time':deepcopy(CarPublicWalkTemplate), 'cost':deepcopy(CarPublicWalkTemplate), \
                           'emission':deepcopy(CarPublicWalkTemplate), 'cals':deepcopy(CarPublicWalkTemplate), 'comfort':deepcopy(CarPublicWalkTemplate)}

PublicBikeTemplate = {'BICYCLE':0, 'PUBLIC_TRANSPORT':0}
CLPublicBikeTemplate = {'time':deepcopy(PublicBikeTemplate), 'cost':deepcopy(PublicBikeTemplate), \
                       'emission':deepcopy(PublicBikeTemplate), 'cals':deepcopy(PublicBikeTemplate), 'comfort':deepcopy(PublicBikeTemplate)}                       

CarPublicBikeWalkTemplate = {'CAR':0, 'PUBLIC_TRANSPORT':0, 'BICYCLE':0, 'WALK':0} #TODO , can influene priority while comparing, if use list [] and order it ??
CLCarPublicBikeWalkTemplate = {'time':deepcopy(CarPublicBikeWalkTemplate), 'cost':deepcopy(CarPublicBikeWalkTemplate), \
                           'emission':deepcopy(CarPublicBikeWalkTemplate), 'cals':deepcopy(CarPublicBikeWalkTemplate), 'comfort':deepcopy(CarPublicBikeWalkTemplate)}

lowEmissionOrder = {"WALK":0, "RUN":0, "BICYCLE":1, "EBICYCLE":2, "TRAM":3, "RAIL":3, "SUBWAY":3, "BUS": 5, "FERRY":20, "CAR":10}  #TODO check references

MODES_FOR_OTP_PLAN_QUERY = ['WALK', 'BICYCLE', 'CAR', 'PUBLIC_TRANSPORT']
MODES_PLAN_IDS = {'WALK':1, 'BICYCLE':2, 'CAR':3, 'PUBLIC_TRANSPORT':4}

# -----------------------------------------
class TripAlternatives:
    def __init__(self, trip_planner):
        self.comparison_list_car_public = {} # example: {13:{'time':{'CAR':3, 'transit':7}, 'cost':{'CAR':6, 'transit':4}}, 6:{'cost':{'CAR':6, 'transit':4}}}
        self.comparison_list_car_public_bike = {}
        self.comparison_list_car_public_walk = {}
        self.comparison_list_public_bike = {}        
        self.comparison_list_car_public_bike_walk = {}
        self.user_modalchoice_list = {}
        self.planner = trip_planner        
    
    # for each trip plans its alternatives and adds them to trip.alternative_trips
    def plan_trip_alternatives(self, trips, min_od_distance, od_d_diff_coeff, 
                               desiredModes = MODES_FOR_OTP_PLAN_QUERY):
        trips_skipped = []
        for trip in trips:            
            # filter our very short trips and,
            # try to filter out the 'badly' detected trips, or 'round-trips', 'walking/running exercise', etc.
            # (do NOT waste time planning alternatives if not needed)
# OLDER CODE commented out:            
#            if trip.od_distance > min_od_distance and trip.distance < od_d_diff_coeff * trip.od_distance:                            
            print(">> Computing alternatives for trip ID:",trip.id) #TODO temp for moprim
                        
            for mode in desiredModes:
                try:
                    # assumptions, adjusting parameters, related cals, some kinematics, etc.:
                    max_walk_distance = MAX_MODE_DETECTION_DELAY * 2  # e.g. 500m walk to start bus stop ... 500m walk to end bus stop
                                        # somehow max_walk_distance is equal to mode-detection-error (transitoin point error) threshold in our system
                                        # this could be also max_distance_between_busstops / 2 !!  (if we have a detection between two bus stops) 
                                        # 1000 m (e.g. 500 m walking at each trip end) gives good results for user id 13 )                        
                    num_of_itineraries = 3 # default is 3
                    maxTransfers = 2  # seems like this param didn't have any effect!
                    show_intermediate_stops = "True"
                    # TODO: is there a param 'max waiting time' too?        
                    
                    # TODO: IMPORTANT: for PT plans, should this also shift back start-time same as mass_transit_match_planner? 
                    # maybe not if it's not important to time-match with the realized trip
                    
                    # query for a trip plan (it either makes a new trip plan (eg. from OTP) or retrieves from cache)
                    res, planned_trips, planning_res = self.planner.plan_a_trip(trip, mode, num_of_itineraries, max_walk_distance, show_intermediate_stops) 
                    
                    if res == 1:                        
                        for planned_trip in planned_trips:
                            planned_trip.plan_id = len(trip.alternative_trips) + 1 # get next plan_id *
                            trip.alternative_trips.append(planned_trip)                            
                        # TODO: update the original plan field (later in code trips rows are stored in DB):
                        if planning_res.is_desired_trip_date_shifted: 
                            trip.shifted_starttime_for_publictransport_tripplan = planning_res.desired_trip_shifted_starttime
                            if planning_res.desired_trip_shifted_starttime is None:
                                raise Exception("plan_trip_alternatives(): planning_res.is_desired_trip_date_shifted True, but planning_res.desired_trip_shifted_starttime is None")
                    elif res == 0:
                        loge(["ERROR in plan_trip_alternatives(): trip:", trip.user_id, trip.id, ": mode", mode, ": planning error:", planning_res.to_Text()])
                except Exception as e:                        
                    logexc(["(!) EXCEPTION catched in plan_trip_alternatives(): trip:", trip.user_id, trip.id, ": mode", mode, ": Exception:"], e)
#            else:
#                print(">> Skipped computation of alternatives for trip ID:",trip.id,"!") #TODO temp for moprim                
#                trips_skipped.append(trip)
                
        return trips_skipped
                
    # for each trip plans its alternatives and adds them to trip.alternative_trips
    def plan_trip_alternatives_new(self, trips, desired_modes = MODES_FOR_OTP_PLAN_QUERY):
        trips_processed = 0
        number_of_input_trips = len(trips)
        # compute alternatives per obsevred trip
        for trip in trips:
            trips_processed += 1
            print("-------------- trip",trips_processed,"/",number_of_input_trips,": trip (",trip.user_id, trip.id, ") --------------")
                        
            for mode in desired_modes:
                try:
                    # assumptions, adjusting parameters, related cals, some kinematics, etc.:
                    max_walk_distance = MAX_MODE_DETECTION_DELAY * 2  # e.g. 500m walk to start bus stop ... 500m walk to end bus stop
                                        # somehow max_walk_distance is equal to mode-detection-error (transitoin point error) threshold in our system
                                        # this could be also max_distance_between_busstops / 2 !!  (if we have a detection between two bus stops) 
                                        # 1000 m (e.g. 500 m walking at each trip end) gives good results for user id 13 )                        
                    num_of_itineraries = 3 # default is 3
                    maxTransfers = 2  # seems like this param didn't have any effect!
                    show_intermediate_stops = "True"
                    # TODO: is there a param 'max waiting time' too?        
                    
                    # TODO: IMPORTANT: for PT plans, should this also shift back start-time same as mass_transit_match_planner? 
                    # maybe not if it's not important to time-match with the realized trip
                    
                    # a few fixes, just in case
                    trip.starttime = trip.starttime.replace(microsecond = 0)
                    trip.endtime = trip.endtime.replace(microsecond = 0)
                    
                    # query for a trip plan (it either makes a new trip plan (eg. from OTP) or retrieves from cache)
                    res, plan, planning_res = self.planner.plan_a_trip_new(trip, mode, num_of_itineraries, max_walk_distance, show_intermediate_stops) 
                    
                    if res == 1:
                        # attach the computed alternative to the observed trip
                        #   go through all trip-leg-chains suggested, to build a collection of Trip objects
                        alts_added = 0
                        plan_id_base = MODES_PLAN_IDS[mode]
                        for itin in plan['itineraries']: 
                            planned_trip = Trip()
                            planned_trip.update_from_otp_trip_plan(trip, planning_res.is_desired_trip_date_shifted, plan, itin)
                                                        
#                            if mode=='PUBLIC_TRANSPORT' and len(planned_trip.legs)==1 and planned_trip.legs[0]['mode']=='WALK':
#                                #print("len(planned_trip.legs):", len(planned_trip.legs)) 
#                                #print(planned_trip.legs[0]['mode'])
#                                #logi("plan_trip_alternatives_new():: NOTE!!! planner returned a single WALK leg for PUBLIC_TRANSPORT. Not saving it.")
#                                pass
#                            else:
                            planned_trip.plan_id = plan_id_base + alts_added
                            trip.alternative_trips.append(planned_trip)   
                            alts_added += 1
                            
                        # IMPORTANT: update the original plan field (later in code trips rows are stored in DB):
                        #   NOTE: is_desired_trip_date_shifted and the shifted date only apply to PUBLIC_TRANSPORT requested mode
                        #         is same for all itins returned by PT OTP query. Therefore, in the 'trips_alts' table, it reperesents all plan_ids of PT alternatives
                        
                        # print("SUCCESS; Planned itin(s) :); ")
                    elif res == 0:
                        loge(["ERROR in plan_trip_alternatives(): trip ("+str(trip.user_id)+" "+str(trip.id)+ ": mode "+mode+": planning error:"+planning_res.to_Text()])
                    
                    # THIS applies only to queries for public transport
                    if planning_res.is_desired_trip_date_shifted and mode == 'PUBLIC_TRANSPORT': 
                        print("TEMP MESSAGE: updating the trip's shifted-date field =", planning_res.desired_trip_shifted_starttime)
                        # update the trip's shifted-date field
                        trip.shifted_starttime_for_publictransport_tripplan = planning_res.desired_trip_shifted_starttime
                        if planning_res.desired_trip_shifted_starttime is None:
                            raise Exception("plan_trip_alternatives(): planning_res.is_desired_trip_date_shifted True, but planning_res.desired_trip_shifted_starttime is None")

                except Exception as e:                        
                    logexc(["(!) EXCEPTION catched in plan_trip_alternatives(): trip:", trip.user_id, trip.id, ": mode", mode, ": Exception:"], e)
                
        return trips
    
    
    def show_trips_and_alternatives(self,  trips, show_only_summary = False):
        # show calculated params:
#        for trip in trips:
#            self.display_trip_economics(trip)
#            for tripalt in trip.alternative_trips:
#                self.display_trip_economics(tripalt)
#            print ""
        print ("-------------- {} trips ---------------".format(len(trips)))
        
        if not show_only_summary:
            self.display_trip_economics_header_csv()
            self.display_trip_economics_units_csv()
            for trip in trips:
                self.display_trip_economics_csv(trip)
                for tripalt in trip.alternative_trips:
                    self.display_trip_economics_csv(tripalt)
                print ("")
        
    
    
    
    def HACK_compute_ebike_alternatives(self, trips): 
        ebike_trips = []
        for trip in trips:
            ebike_alt = None                        
            for alt in trip.alternative_trips:
                if alt.mainmode == 'BICYCLE':
                    # compute ebike alternative -----
                    # create a new alternative
                    ebike_alt = deepcopy(alt) #almost all values of ebike trip is same as bike
                    # duration and calories defer, and maybe also emission defers
                    
                    # change the values that need recalculation
                    speed_coeff = 1.161290323 # speed of ordinary bike is 15.5 km/h and e-bike is 18 km/h
                    duration_coeff = 1/speed_coeff
                    
                    ebike_alt.mainmode = 'EBICYCLE' # TODO: also edit multimodal_summary 
                    ebike_alt.duration = CommonHelper.multiply_duration(ebike_alt.duration, duration_coeff)
                    
                    ebike_alt.plan_id = 1 + max(trip.alternative_trips, key=lambda x : x.plan_id).plan_id
                    
                    # TODO, revise later
#                    for item in ebike_alt.duration_by_mode.iteritems():
#                        newleg = {}
#                        if item[0] == 'BICYCLE':
#                            item[0] = 'EBICYCLE'
#                            legduration = CommonHelper.str_to_DateTimeDuration(item[1])                            
#                            item[1] = CommonHelper.multiply_duration(legduration, duration_coeff)
#                            #leg[1] = legduration
#                    
#                    for legmode, legduration in ebike_alt.duration_by_mode.iteritems():
#                        if legmode == 'BICYCLE':
#                            legmode = 'EBICYCLE'
#                            legduration = CommonHelper.str_to_DateTimeDuration(legduration)                            
#                            legduration = CommonHelper.multiply_duration(legduration, duration_coeff)
#                            #leg[1] = legduration
                            
                    # calculate total duration of trip and leg-durations
                    total_legs_duration = datetime.timedelta(0)
                    for legmode, legduration in ebike_alt.duration_by_mode.iteritems():
                        legduration = CommonHelper.str_to_DateTimeDuration(legduration) # convert to datetime                     
                        if legmode == 'BICYCLE':                           
                            legduration = CommonHelper.multiply_duration(legduration, duration_coeff)                        
                        #ebike_alt.add_duration(leg['mode'], legduration) # for now 'total' trip duration is NOT calculated in this function
                        total_legs_duration += legduration
                    #ebike_alt.add_duration(intermediateMode, ebike_alt.duration - total_legs_duration) #if duration from OTP and duration computated here do not match                    
                    ebike_alt.duration = total_legs_duration
                            
                        
                    ebike_alt.duration_by_mode['BICYCLE'] = datetime.timedelta(0)
                    ebike_alt.add_duration('EBICYCLE', ebike_alt.duration)
                    
#                    for leg in ebike_alt.legs:
#                        if leg['mode'] == 'BICYCLE':
#                            leg['mode'] = 'EBICYCLE'
#                            leg['duration'] = leg['duration'] * duration_coeff
#                            
#                    # calculate total duration of trip and leg-durations
#                    for leg in ebike_alt.legs:
#                        legduration = leg['duration']
#                        ebike_alt.add_duration(leg['mode'], legduration) # for now 'total' trip duration is NOT calculated in this function
#                        total_legs_duration += legduration
#                    #ebike_alt.add_duration(intermediateMode, ebike_alt.duration - total_legs_duration) #if duration from OTP and duration computated here do not match                    
#                    ebike_alt.duration = total_legs_duration
                    
                    ebike_alt.endtime = ebike_alt.starttime + ebike_alt.duration
                                        
                    break
            
            # add the computed ebike to alternative list
            if ebike_alt is not None:
                trip.alternative_trips.append(ebike_alt)
                ebike_trips.append(ebike_alt)
                
        return trips, ebike_trips

    #---- first order by E (emission) -------------------
    def compare_trip_alternatives_emission_then_time(self, trips, excluded_modes = {}):                
        for trip in trips:
            fastest_choices = self.__get_lowemission_timerelevant_choices(trip.alternative_trips, excluded_modes)                        
            best_fastest_choice = self.__get_best_lowemission_timerelevant_choice(fastest_choices) 
            if best_fastest_choice is not None:
                has_gap, has_plus = self.__get_gap_and_plus(trip, best_fastest_choice)                
            else:
                has_gap = False
                has_plus = False
                loge(["(!) best_fastest_choice is None: fastest_choices list:", fastest_choices, "for trip:", trip.user_id, trip.id, ": trip has {} alternatives".format(len(trip.alternative_trips))])
                    
            #greenest_choices = self.__get_greenest_choices(trip.alternative_trips)
            #healthiest_choices = self.__get_healthiest_choices(trip.alternative_trips)
            
            # update the trip object
            trip.fastest_choices = fastest_choices
            trip.best_fastest_choice = best_fastest_choice
            trip.has_gap = has_gap
            trip.has_plus = has_plus
            trip.update_mainmode_concise()            
            if trip.best_fastest_choice is not None:
                trip.best_fastest_choice.update_mainmode_concise()                

        return trips

    def __get_lowemission_timerelevant_choices(self, alternative_trips, excluded_modes):
        bestest = []
        try:
            # TODO: WARNING: //maybe implement using Loops, if deepcopy is CPU hungry
            # loop1: find the absolute_fastest (skip alts with mainmode = excluded_modes)
            # loop2: find all bestest (skip alts with mainmode = excluded_modes)
            # TODO: also research about performance of lambda ... 
            alts = deepcopy(alternative_trips)
                        
            # exlude modes we don't want in this comparison (e.g. ignore BICYCLE, assuming travelers don't have a bike)
            alts = filter(lambda x: x.mainmode not in excluded_modes, alts)
            
            # find the fastest alternative
#            alts.sort(key = lambda x: x.duration) # now the fastest trip is at top
            if len(alts) > 0:
                absolute_fastest = min(alts, key = lambda x: x.duration)
#                absolute_fastest = alts[0]
                        
            # sort on alt.emission
            alts.sort(key = lambda x: x.emission)
                        
            # sort on custom emission+activity priority
            # //TODO IMPORTANT, REVISE IF NEEDED
            # our order of low-emission and activity is now: {walk, bike, ebike, (tram, metro, train), bus, car, ferry}
            for alt in alts:
                alt.lowemission_order = deepcopy(lowEmissionOrder[alt.mainmode])                
            alts.sort(key = lambda x: x.lowemission_order) # now the most suitable trip is at top

            if len(alts) > 0:                
                # iterate through all alts, add them to results, as long as trip-duration is within our margin
                MARGIN = datetime.timedelta(minutes = 3) #TODO: make it an input cofig value
                for alt in alts:
                    if alt.duration - absolute_fastest.duration <= MARGIN:
                        bestest.append(alt)
        except Exception as e:
            logexc("(!) Exception in __get_fastest_choices()", e);
        except:
            logexc("(!) Exception in __get_fastest_choices() UNDEFINED Exception", None);
        
        return bestest

    def __get_best_lowemission_timerelevant_choice(self, fastest_choices):        
        # fastest_choices should have been sorted by trip duration
        good_choice = None
        if len(fastest_choices) == 0:
            return good_choice
        good_choice = fastest_choices[0] # (note: the list is already ordered by emissoin => lowest emission is already at top, if no sustainble was in list, then most probably Car is already at top)        
        return good_choice


    #---- first order by T (travel time) -----------------
    def compare_trip_alternatives(self, trips, excluded_modes = {}, non_preferred_modes = {}):                
        for trip in trips:
            fastest_choices = self.__get_fastest_choices(trip.alternative_trips, excluded_modes)                        
            best_fastest_choice = self.__get_best_fastest_choice(fastest_choices, non_preferred_modes) #e.g. also consider sustainability
            if best_fastest_choice is not None:
                has_gap, has_plus = self.__get_gap_and_plus(trip, best_fastest_choice)                
            else:
                has_gap = False
                has_plus = False
                loge(["(!) best_fastest_choice is None: fastest_choices list:", fastest_choices, "for trip:", trip.user_id, trip.id, ": trip has {} alternatives".format(len(trip.alternative_trips))])
                    
            #greenest_choices = self.__get_greenest_choices(trip.alternative_trips)
            #healthiest_choices = self.__get_healthiest_choices(trip.alternative_trips)
            
            # update the trip object
            trip.fastest_choices = fastest_choices
            trip.best_fastest_choice = best_fastest_choice
            trip.has_gap = has_gap
            trip.has_plus = has_plus
            trip.update_mainmode_concise()            
            if trip.best_fastest_choice is not None:
                trip.best_fastest_choice.update_mainmode_concise()                

        return trips
        
    def __get_best_fastest_choice(self, fastest_choices, non_preferred_modes):        
        # fastest_choices should have been sorted by trip duration
        good_choice = None
        if len(fastest_choices) == 0:
            return good_choice
        for choice in fastest_choices: # iterate to find first desired fast mode
            if choice.mainmode not in non_preferred_modes: 
                good_choice = choice
                break
        if good_choice is None: # but if no sustianble mode is among the fastest list, then just choose first mode
            good_choice = fastest_choices[0]
        return good_choice
            
    def __get_gap_and_plus(self, trip, best_fastest_choice):    
        # realized vs potentials
        # deduce gaps according to a table
        has_gap = (ModalChoice.get_car_noncar_mode(trip.mainmode) == CarNonCarEnum.CAR and 
                ModalChoice.get_car_noncar_mode(best_fastest_choice.mainmode) == CarNonCarEnum.NONCAR)        
        has_plus = (ModalChoice.get_car_noncar_mode(trip.mainmode) == CarNonCarEnum.NONCAR and 
                ModalChoice.get_car_noncar_mode(best_fastest_choice.mainmode) == CarNonCarEnum.CAR)
                
        return has_gap, has_plus

    def __get_fastest_choices(self, alternative_trips, excluded_modes):
        fastest = []
        try:
            # TODO: WARNING: //maybe implement using Loops, if deepcopy is CPU hungry
            # loop1: find the absolute_fastest (skip alts with mainmode = excluded_modes)
            # loop2: find all fastest (skip alts with mainmode = excluded_modes)
            # TODO: also research about performance of lambda ... 
            alts = deepcopy(alternative_trips)

            # exlude modes we don't want in this comparison (e.g. ignore BICYCLE, assuming travelers don't have a bike)
            alts = filter(lambda x: x.mainmode not in excluded_modes, alts)
            # sort on alt.duration, to easily get the absolute minimum
            alts.sort(key = lambda x: x.duration) # now the fastest trip is at top
            
            if len(alts) > 0:
                absolute_fastest = alts[0] # now the fastest is the first one
                
                # iterate through all alts, add them to results, as long as trip-duration is within our margin
                MARGIN = datetime.timedelta(minutes = 3) #TODO: make it an inpt cofig value
                for alt in alts:
                    if alt.duration - absolute_fastest.duration > MARGIN:
                        break
                    else:
                        fastest.append(alt)
        except Exception as e:
            logexc("(!) Exception in __get_fastest_choices()", e);
        except:
            logexc("(!) Exception in __get_fastest_choices() UNDEFINED Exception", None);
        
        return fastest

    def compare_trip_alternatives_old(self, trips):                
        for trip in trips:
            # compare params of the trip and its alt trips in order to set pros & cons of modal-choices per trip 
            # (eg. alt trip #2 with WALK->CAR is the fastest choice => 'WALK->CAR' is faster modal-choice for this trip):
            best_modalchoice_by_param_car_public = self.get_best_modalchoice_by_param_for_trip(trip, CarPublicTemplate)
            best_modalchoice_by_param_car_public_bike = self.get_best_modalchoice_by_param_for_trip(trip, CarPublicBikeTemplate)
            best_modalchoice_by_param_car_public_walk = self.get_best_modalchoice_by_param_for_trip(trip, CarPublicWalkTemplate)                        
            best_modalchoice_by_param_public_bike = self.get_best_modalchoice_by_param_for_trip(trip, PublicBikeTemplate)                                   
            best_modalchoice_by_param_car_public_bike_walk = self.get_best_modalchoice_by_param_for_trip(trip, CarPublicBikeWalkTemplate)                                   

            # summarize (cumulative) pros and cons for per user *:
            # (eg. of total 10 trips of user 1: 'WALK->CAR' is the fastest modal-choice in 8 trips and 'BICYCLE' in 2 trips)
            self.increase_pros_for_user(trip.user_id, self.comparison_list_car_public, CLCarPublicTemplate, best_modalchoice_by_param_car_public)
            self.increase_pros_for_user(trip.user_id, self.comparison_list_car_public_bike, CLCarPublicBikeTemplate, best_modalchoice_by_param_car_public_bike)
            self.increase_pros_for_user(trip.user_id, self.comparison_list_car_public_walk, CLCarPublicWalkTemplate, best_modalchoice_by_param_car_public_walk)
            self.increase_pros_for_user(trip.user_id, self.comparison_list_public_bike, CLPublicBikeTemplate, best_modalchoice_by_param_public_bike)
            self.increase_pros_for_user(trip.user_id, self.comparison_list_car_public_bike_walk, CLCarPublicBikeWalkTemplate, best_modalchoice_by_param_car_public_bike_walk)
                        
            # get what user has chosen (from the actual trip) -----------------
            # pass this: self.user_modalchoice_list                         
            self.__increase_modalchoice_for_user(trip.user_id, trip, self.user_modalchoice_list)            
            
    def __get_public_transport_concise_mode(self, mode):
        if mode in PublicTransportModesTemplate:
            return 'PUBLIC_TRANSPORT' 
        else:
            return mode

    def __increase_modalchoice_for_user(self, user_id, trip, user_modalchoice_list):
        log(["increase_modalchoice_for_user:: ..."])
        log(["trip.mainmode:",trip.mainmode])
        chosenmode = trip.mainmode
        if chosenmode in PublicTransportModesTemplate:
            chosenmode = 'PUBLIC_TRANSPORT' 
        log(["chosenmode:",chosenmode])

        if user_id not in user_modalchoice_list:
            user_modalchoice_list[user_id] = deepcopy(UserModalChoiceTemplate)            

        if chosenmode in user_modalchoice_list[user_id]:
            user_modalchoice_list[user_id][chosenmode] += 1    
    
    def get_best_modalchoice_by_param_for_trip(self, trip, desired_modes_template):
        # find the best modal-choice per trip depending on the target param (eg. 'time', 'cals', ...):
        mintime = None # TODO: or compare with original trip?!
        mincost = None
        maxcals = None
        minemission = None
        maxcomfort = None
        pros = deepcopy(BestModalChoiceByParamTemplate)
        # pros_detailed = deepcopy(BestModalChoiceByParamTemplate) # TODO later
        modes_to_compare = []
        for mode, val in desired_modes_template.iteritems():
#            if mode == 'PUBLIC_TRANSPORT':
#                for public_transport_mode in PublicTransportModesTemplate:
#                    modes_to_compare.append(mode)                    
            modes_to_compare.append(mode)
        
        log([""])
        log(["get_best_modalchoice_by_param_for_trip:: ...:"])
        log(["modes_to_compare:", modes_to_compare])
                
        #if trip.user_id not in comparison_list:
        #    comparison_list[trip.user_id] = desiredCLTemplate #TODO old code?! remove?
        
        # find the min val or max val depending on the target param 
        # (eg. for 'cals' we should find the tripalt (modal-choice chain) with largest 'cals' val)
        for tripalt in trip.alternative_trips:
            log(["tripalt.mainmode:",tripalt.mainmode])
            mainmode = tripalt.mainmode
            if mainmode in PublicTransportModesTemplate:
                mainmode = 'PUBLIC_TRANSPORT' 
            log(["mainmode:",mainmode])
            
            if mainmode in modes_to_compare:
                if mintime is None or tripalt.duration < mintime: #TODO : what if == ???
                    mintime = tripalt.duration                    
                    pros['time'] = {"plan_id":tripalt.plan_id, "mode": mainmode}
                if mincost is None or tripalt.cost < mincost:
                    mincost = tripalt.cost
                    pros['cost'] = {"plan_id":tripalt.plan_id, "mode": mainmode}
                if maxcals is None or tripalt.calories > maxcals:
                    maxcals = tripalt.calories
                    pros['cals'] = {"plan_id":tripalt.plan_id, "mode": mainmode}
                if minemission is None or tripalt.emission < minemission:
                    minemission = tripalt.emission
                    pros['emission'] = {"plan_id":tripalt.plan_id, "mode": mainmode}
                if maxcomfort is None or tripalt.comfort > maxcomfort:
                    maxcomfort = tripalt.comfort                    
                    pros['comfort'] = {"plan_id":tripalt.plan_id, "mode": mainmode}

        log([trip.user_id,trip.device_id, trip.id,":"," pros:",pros])
        return pros            

    def increase_pros_for_user(self, user_id, comparison_list, cl_desired_template, best_modalchoice_by_param): 
        log([""])
        log(["increase_pros_for_user ...:"])
        log(["cl_desired_template:",cl_desired_template])
        log(["best_modalchoice_by_param:",best_modalchoice_by_param])
        if user_id not in comparison_list:
            comparison_list[user_id] = deepcopy(cl_desired_template)
        log(["comparison_list before calcs:",comparison_list])
        
        for param, choice in best_modalchoice_by_param.iteritems():
            if choice['mode'] is not None:
                comparison_list[user_id][param][choice['mode']] += 1

        log(["comparison_list after calcs:",comparison_list])

    #--------------------------------------------------------------------------------------------------    
    def display_trip_economics(self, trip):
        print (trip.user_id,"|",trip.id, ",", trip.plan_id, \
              "|", trip.multimodal_summary, \
              "|", DateTime_to_Text(trip.starttime), "to", DateTime_to_Text(trip.endtime), \
              "| from ", pointRow_to_geoText(trip.origin), "--> to", pointRow_to_geoText(trip.destination), \
              "| time:", DateTimeDelta_to_Text(trip.duration), "| cost:", round(trip.cost, 2), round_dict_values(trip.cost_by_mode, 2), \
              "| cals:", int(round(trip.calories)), round_dict_values(trip.calories_by_mode, 0), \
              "| emission:", int(round(trip.emission)), round_dict_values(trip.emission_by_mode, 0), \
              "| comfort:", trip.comfort, "| distance: ", int(round(trip.distance)), round_dict_values(trip.distance_by_mode, 0)
              )
        
    def display_trip_economics_header_csv(self):
        print ("user-id; device_id; trip-id; trip-plan-id; multimodal summary; start-time;end-time;trip-time;cost;calories;emission;comfort;distance;;from;to;;"\
               "cost by mode;calories by mode;emission by mode;distance by mode")

    def display_trip_economics_units_csv(self):
        print (";;;;;;;;(eur);(cals);(co2 kg);(%);(km);;;;;(eur);(cals);(co2 grams);(m)")
        
    def display_trip_economics_csv(self, trip):                 
        print (trip.user_id,"|", trip.device_id,"|", trip.id, "|", trip.plan_id, \
              "|", trip.multimodal_summary, \
              "|", DateTime_to_Text(trip.starttime), "|", DateTime_to_Text(trip.endtime), \
              "|", DateTimeDelta_to_Text(trip.duration), "|", round(trip.cost, 2), \
              "|", int(round(trip.calories)), "|", round(trip.emission/1000.0, 1), \
              "|", trip.comfort, "|", round(trip.distance/1000.0, 1), \
              "||", pointRow_to_geoText(trip.origin), "|", pointRow_to_geoText(trip.destination),\
              "||", round_dict_values(trip.cost_by_mode, 2), "|", round_dict_values(trip.calories_by_mode, 0), \
              "|", round_dict_values(trip.emission_by_mode, 0),"|", round_dict_values(trip.distance_by_mode, 0)
              )

    def display_trip_alternatives_comparison_summary(self):
        # show summary of pros and cons per user:
        logi(["Showing summary of pros and cons per user: ...:"])
        logi([""])
        logi(["Car vs. Public Transport:"])
        for user, comparison_list in self.comparison_list_car_public.iteritems():
            logi(["user", user, comparison_list])

        logi([""])
        logi(["Car vs. Public Transport vs. Bike:"])
        for user, comparison_list in self.comparison_list_car_public_bike.iteritems():
            logi(["user", user, comparison_list])

        logi([""])
        logi(["Car vs. Public Transport vs. Walk:"])
        for user, comparison_list in self.comparison_list_car_public_walk.iteritems():
            logi(["user", user, comparison_list])

        logi([""])
        logi(["Public Transport vs. Bike:"])
        for user, comparison_list in self.comparison_list_public_bike.iteritems():
            logi(["user", user, comparison_list])

        logi([""])
        logi(["Car vs. Public Transport vs. Bike vs. Walk:"])
        for user, comparison_list in self.comparison_list_car_public_bike_walk.iteritems():
            logi(["user", user, comparison_list])

        logi([""])
        logi(["You chose:"])
        for user, modalchoices in self.user_modalchoice_list.iteritems():
            logi(["user", user, modalchoices])
        
