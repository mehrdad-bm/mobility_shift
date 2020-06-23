# ~~~ this class/file should be in package (namespace) BLL ~~~

import datetime
from pyfiles.common.modalchoice import ModalChoice
from pyfiles.common.trip import Trip
from commonlayer.common_helper_class import CommonHelper 
from commonlayer.logger import (log, logi, loge)


class TripBuilder:
    def __init__(self, db_session, trips_dal, legs_dal):
        self.db_session = db_session
        self.trips_dal = trips_dal
        self.legs_dal = legs_dal

    # trip extraction ----------------------------------------------------------------
    # works based on a state-diagram approach:
    # 'actvity location' is a state and 'leg' is a transition from one state to another
    # note: refer to paper notes
    def get_trips_from_legs(self, ids_to_process, date_range_start, date_range_end):        
        # traverses trips table (first: load all relevant subsequent legs) .........
        # TODO: memoray management: large memory needed if a lot of trips ** ...
        #   A1: no problem now ... even with 100,000 trips and assuming 1KB per trip-record --> only 100 MB memoray usage
        #   A2: no problem if each time we load trips of one user (?)    
        legs =  self.legs_dal.load_legs(ids_to_process, date_range_start, date_range_end)                                    

        trips = []
        trip = None        
        # leg_index = 0 #TODO: not needed anymore?
        lastleg = None
        INTERLEG_IDLE_TIME_THRESHOLD = datetime.timedelta(minutes = 10)
        INTERLEG_IDLE_TIME_SPECIAL_CASE_MIN = datetime.timedelta(minutes = 5)
        at_activity_location = True # first trip (of each user*) starts with first leg record (one reason is to avoid 'shifted trip extraction')
        at_new_user = False
        lastuserid = None
        
        # TODO, NOTE!: are there more problems in detecting trip_started_here (because of mode detection delay) ??? 
        
        for leg_row in legs:                
            #print leg['time_start'], leg['time_end'], leg['activity'], leg['line_type']            
            leg = dict(leg_row.items())
            
            if leg['activity'] != 'STILL': # skip STILL legs
                # skip over different mode-detections of same leg! (trick: now our query sorts by 'USER', 'LIVE', 'PLANNER')
                if lastleg is not None and leg['id'] == lastleg['id']:
                    logi(["NOTE! more than one mode for leg", leg['id'], "------"])
                    logi([lastleg['activity'], lastleg['line_type'], lastleg['line_name'], lastleg['line_source']])
                    logi([leg['activity'], leg['line_type'], leg['line_name'], leg['line_source']])
                    logi("")
                    continue # do NOT update the leg.mode based on this record (the top-most mode on the list is the priority)
            
                # TODO: important line!!! to adapt new schema change leg--mode specially for USER-changed mode            
                leg['activity'] = ModalChoice.get_leg_activity_name(leg)
                leg['line_type'] = ModalChoice.get_leg_line_type(leg)
                
                # detect arriving at a new user's leg record *:
                if leg['user_id'] != lastuserid:
                     # reset trip_id and other params for the new user:
                    trip_id_index = self.trips_dal.get_next_user_trip_id(leg['user_id'], date_range_start, date_range_end)
                    lastuserid = leg['user_id']
                    at_new_user = True
            
                # detect 'activity locations' ***: 
                if not at_new_user and lastleg is not None:                                             
                    legs_time_distance = leg['time_start'] - lastleg['time_end']
                    if legs_time_distance > INTERLEG_IDLE_TIME_THRESHOLD: # TODO: and other conditions ...                        
                        at_activity_location = True # last trip ends here & next trip starts here
                    elif (legs_time_distance > INTERLEG_IDLE_TIME_SPECIAL_CASE_MIN and\ # between two car legs
                          legs_time_distance <= INTERLEG_IDLE_TIME_THRESHOLD and\
                          ModalChoice.is_car_leg(leg) and ModalChoice.is_car_leg(lastleg)
                          ):
                        at_activity_location = True
                    else:
                        at_activity_location = False
                
                # act accordingly at 'activity location' or when a new user
                if at_new_user or at_activity_location:
                    if trip is not None: # if we had started a trip and it's still open-ended
                        # end current trip here: 
                        trip.destination = CommonHelper.geoJSON_to_pointRow(lastleg['destination'])
                        trip.endtime = lastleg['time_end'] 
                        trips.append(trip) # add it to the collection of extracted trips *
                        trip = None
                    # start a new trip here:
                    trip_id_index += 1
                    trip = Trip()
                    trip.user_id = leg['user_id']
                    trip.device_id = leg['device_id']                    
                    trip.id = trip_id_index
                    trip.plan_id = 0 # this is the actual trip (we're processing only the actual recorded trips in this function)
                    trip.origin = CommonHelper.geoJSON_to_pointRow(leg['origin'])
                    trip.starttime = leg['time_start']

                if trip is not None: # save non-STILL legs to current trip
                    trip.append_trafficsense_leg(leg)

                #leg_index += 1 # TODO: not needed anymore?
                lastleg = leg      
                if at_new_user:                       
                    at_new_user = False
        #loop ends------------------------
        # deal with the last remaining leg:             
        if trip is not None: # if we've started a trip and it's still open-ended
            # end current trip here
            trip.destination = CommonHelper.geoJSON_to_pointRow(lastleg['destination'])
            trip.endtime = lastleg['time_end']          
            trips.append(trip)
                    
        return 1, trips        


    def update_trips_and_alternatives(self, ids_to_process, custom_date_range_start, custom_date_range_end, trips):
        print (">> Storing trips & their alternatives into 'trips_alts' table ......................")
        self.trips_dal.delete_trips_to_legs(ids_to_process, custom_date_range_start, custom_date_range_end)        
        self.trips_dal.delete_trips(ids_to_process, custom_date_range_start, custom_date_range_end)
        self.trips_dal.store_trips(ids_to_process, trips)

        print ("" )
        print (">> Storing trip-to-legs relations into 'trips_to_legs' table ......................"    )
        self.trips_dal.store_trips_to_legs(ids_to_process, trips)

    def update_trips_and_alternatives_moprim(self, ids_to_process, id_start, id_end, trips):
        print (">> Storing trips & their alternatives into 'trips_alts' table ......................")
        self.trips_dal.delete_trips_by_id(ids_to_process, id_start, id_end)
        self.trips_dal.store_trips(ids_to_process, trips)

    def update_alternatives(self, ids_to_process, id_start, id_end, trips):
        print (">> Storing alternatives into 'trips_alts' table ......................")
        self.trips_dal.delete_trips_by_id(ids_to_process, id_start, id_end)
        self.trips_dal.store_trips(ids_to_process, trips)
        llll
        
    def HACK_update_onlys_ebike_alternatives(self, ids_to_process, custom_date_range_start, custom_date_range_end, trips):
        print (">> Storing ONLY ebike alternatives into 'trips_alts' table ......................")
        #self.trips_dal.delete_trips_to_legs(ids_to_process, custom_date_range_start, custom_date_range_end)        
        self.trips_dal.HACK_delete_ebike_trips(ids_to_process, custom_date_range_start, custom_date_range_end)
        self.trips_dal.store_trips(ids_to_process, trips)

        print ("" )
        print (">> Storing trip-to-legs relations into 'trips_to_legs' table ......................"    )
        self.trips_dal.store_trips_to_legs(ids_to_process, trips)
