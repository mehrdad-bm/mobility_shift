import json
from copy import (deepcopy)
from datetime import timedelta

from pyfiles.common_helpers import (geoLoc_to_pointRow, geoJSON_to_pointRow, 
                                    OTPTimeStampToNormalDateTime, OTPDurationToNormalDuration, 
                                    shift_time_to_specific_date)
from pyfiles.common.user import (User)
from pyfiles.common.modalchoice import (ModalChoice)


class Trip:
    """ a Trip is a collection of Legs
        tirp is door-to-door whereas leg does not have to be        
    """
    
    def __init__(self, trip_row = None):
        if trip_row is None:
            self.user_id = None
            self.device_id = None                
            self.id = None
            self.plan_id = None
            
            self.origin = None # NOTE: of type TS 'point', but only one field: {"geojson": <GeoJSON of the point>}
            self.destination = None # NOTE: of type TS 'point', but only one field: {"geojson": <GeoJSON of the point>}
            self.starttime = None
            self.endtime = None       

            self.legs = [] # collection of type 'legs' table row

            # trip economics values:
            self.distance = None
            self.od_distance = None
            self.duration = None
            self.cost = None
            self.calories = None
            self.emission = None
            self.comfort = None
            self.distance_by_mode = {}                        
            self.duration_by_mode = {}                
            self.cost_by_mode = {}
            self.calories_by_mode ={}
            self.emission_by_mode ={}
            
            self.alternative_trips = [] # a collection of type:class Trip
            self.user = None # TODO is this used now?!
            self.has_transitLeg = False
            
            self.multimodal_summary = None
            self.mainmode = None        
            
            self.shifted_starttime_for_publictransport_tripplan = None
            self.notes = None 
            self.has_a_return_to_intermediate_destination = False
            self.legs_without_points = []
        else:
            self.user_id = trip_row['user_id']
            self.device_id = trip_row['device_id']                
            self.id = trip_row['id']
            self.plan_id = trip_row['plan_id']
            
            self.origin = geoJSON_to_pointRow(trip_row['origin'])
            self.destination = geoJSON_to_pointRow(trip_row['destination'])
            self.starttime = trip_row['start_time']
            self.endtime = trip_row['end_time']

            self.legs = [] # collection of type 'legs' table row

            # trip economics values:
            self.distance = trip_row['distance']
            self.od_distance = trip_row['od_distance']
            self.duration = trip_row['duration']
            self.cost = trip_row['cost']
            self.calories = trip_row['calories']
            self.emission = trip_row['emission']
            self.comfort = trip_row['comfort']
            # TODO following !!!
            self.distance_by_mode = json.loads(trip_row['distance_by_mode'])
            self.duration_by_mode = json.loads(trip_row['time_by_mode'].replace("'", '"'))
            self.cost_by_mode = json.loads(trip_row['cost_by_mode'].replace("'", '"'))
            self.calories_by_mode =json.loads(trip_row['calories_by_mode'].replace("'", '"'))
            self.emission_by_mode =json.loads(trip_row['emission_by_mode'].replace("'", '"'))
            
            self.alternative_trips = [] # a collection of type:class Trip
            self.user = None # TODO is this used now?!
            self.has_transitLeg = False # TODO, what to set?!!
            
            self.multimodal_summary = trip_row['multimodal_summary']
            self.mainmode = trip_row['mainmode']
            
            self.shifted_starttime_for_publictransport_tripplan = trip_row['start_time_for_plan']
            self.notes = trip_row['notes']        

            self.has_a_return_to_intermediate_destination = False
            self.legs_without_points = []
                 
    
    def update_from_otp_trip_plan(self, desired_trip, is_desired_trip_date_shifted, plan, itin):        
        # set trip's attributes ........................
        self.user_id = desired_trip.user_id
        self.device_id = desired_trip.device_id
        self.id = desired_trip.id            
        itin_starttime = OTPTimeStampToNormalDateTime(itin['startTime'])
        itin_endtime = OTPTimeStampToNormalDateTime(itin['endTime'])
        # self.shifted_starttime_for_publictransport_tripplan = itin_starttime # no need to use this field for alternative plans? (plan_id > 0)
        
        # TODO: NOTE: starttime/endtime of planned PT itinerary may differ *a bit* (e.g. some minutes)
        #             from the desired trip's start-time/endtime
        if is_desired_trip_date_shifted:            
            # Revert the alternative trip's date back to the original observed trip's date, 
            # i.e. store with the original dates, as if it could happen on the original observed trip's date
            self.starttime = shift_time_to_specific_date(itin_starttime, desired_trip.starttime)
            self.endtime = shift_time_to_specific_date(itin_endtime,  desired_trip.endtime)
            #print(itin_starttime, "to", self.starttime)    
        else: 
            self.starttime = itin_starttime 
            self.endtime = itin_endtime
            
        self.origin = geoLoc_to_pointRow(plan['from']['lat'], plan['from']['lon']) # TODO: are there cases where plan's origin{lat,lon} differ a bit from desired trip origin?!
        self.destination = geoLoc_to_pointRow(plan['to']['lat'], plan['to']['lon']) # TODO: are there cases where plan's destination{lat,lon} differ a bit from desired trip destination?!
        # self.legs = itin['legs'] #TODO remove old code?
        # set trip's legs ........................
        self.append_otp_legs(itin['legs'], is_desired_trip_date_shifted, desired_trip.starttime, desired_trip.endtime)
        
    
    def append_otp_legs(self, otpLegs, is_desired_trip_date_shifted, desired_date_start,  desired_date_end):
        for leg in otpLegs:
            self.append_otp_leg(leg, is_desired_trip_date_shifted, desired_date_start, desired_date_end)
    
    def append_otp_leg(self, otpLeg, is_desired_trip_date_shifted, desired_date_start, desired_date_end): # adding legs retrieved from OTP
        leg = deepcopy(otpLeg) # TODO: WARNING !!! is this neede?!!

        leg['is_otp_leg'] = True
        leg['is_moprim_leg'] = False
        leg_starttime = OTPTimeStampToNormalDateTime(leg['startTime'])
        leg_endtime = OTPTimeStampToNormalDateTime(leg['endTime'])        
        # leg['time_start_for_plan'] = leg_starttime # TODO ? no need for this field?
        # leg['time_end_for_plan'] = leg_endtime    # TODO ? no need for this field?                
        if is_desired_trip_date_shifted:
            leg['time_start'] = shift_time_to_specific_date(leg_starttime,  desired_date_start) # TODO: NOTE: starttime of plan may differ from desired trip start-time (???)
            leg['time_end'] = shift_time_to_specific_date(leg_endtime,  desired_date_end)
        else:
            leg['time_start'] = leg_starttime
            leg['time_end'] = leg_endtime
        # TODO IMPORTANT!!! - do this also for details:
        #leg['from']['arrival']
        #leg['from']['departure']
        #leg['to']['arrival']
        #leg['to']['departure']
        #   leg['intermediateStops'][i]['arrival]
        #   leg['intermediateStops'][i]['departure]
        
        leg['duration'] = OTPDurationToNormalDuration(leg['duration'])
        if leg['transitLeg'] == True:
            self.has_transitLeg = True # NOTE: TODO: not needed anymore?!        
            
        self.legs.append(leg)
    
    def append_moprim_leg(self, leg_row):
        leg = dict(leg_row.items())
        # NOTE: leg['origin'] and leg['destination'] are of type GeoJSON
        leg['is_otp_leg'] = False
        leg['is_moprim_leg'] = True
        leg['transitLeg'] = False # NOTE: important field assignment       
        leg['alerts'] = None # Note: ... used later to estimate 'comfort' param 
                
        self.legs.append(leg)        
    
    def append_trafficsense_leg(self, leg_row): # adding legs detected by TS from actual trips
        leg = dict(leg_row.items())
        # NOTE: leg['origin'] and leg['destination'] are of type GeoJSON
        leg['is_otp_leg'] = False
        leg['is_moprim_leg'] = False
        leg['distance'] = None 
        leg['mode'] = 'NOT_CONVERTED' #TODO ...
        leg['transitLeg'] = False # NOTE: important field assignment       
        leg['alerts'] = None # Note: ... used later to estimate 'comfort' param 
        
        if leg['activity'] == 'IN_VEHICLE' and leg['line_type'] is None: #driving
            leg['mode'] = 'CAR'
        elif leg['activity'] == 'IN_VEHICLE' and leg['line_type'] is not None: #public transport
            leg['mode'] = leg['line_type']
            leg['transitLeg'] = True # NOTE: important field assignment
            self.has_transitLeg = True # NOTE: TODO: not needed anymore?!
            if leg['mode'] == 'TRAIN':
                leg['mode'] = 'RAIL'            
        elif leg['activity'] == 'WALKING':
            leg['mode'] = 'WALK'
        elif leg['activity'] == 'RUNNING':
            leg['mode'] = 'RUN'
        elif leg['activity'] == 'ON_BICYCLE':
            leg['mode'] = 'BICYCLE'
        #TODO add condition for eBike
        # TODO; 'ON_FOOT' ?!!!
        
        self.legs.append(leg)        
        # print "appended TS leg:", leg            

    def add_duration(self, mode, duration):
        if mode not in self.duration_by_mode:
            self.duration_by_mode[mode] = timedelta(0)
        self.duration_by_mode[mode] += duration
        #self.duration += duration # TODO: now trip's whole duration is calculated at once
        
    def add_cost(self, mode, cost):
        if mode not in self.cost_by_mode:
            self.cost_by_mode[mode] = 0    
        self.cost_by_mode[mode] += cost
        self.cost += cost
        
    def add_calories(self, mode, cals):
        if mode not in self.calories_by_mode:
            self.calories_by_mode[mode] = 0    
        self.calories_by_mode[mode] += cals
        self.calories += cals
        
    def add_emission(self, mode, emission):
        if mode not in self.emission_by_mode:
            self.emission_by_mode[mode] = 0    
        self.emission_by_mode[mode] += emission
        self.emission += emission

    def add_travelled_distance(self, mode, distance):
        if mode not in self.distance_by_mode:
            self.distance_by_mode[mode] = 0    
        self.distance_by_mode[mode] += distance
        self.distance += distance
    
    def get_distance_by_mode(self, mode):
        if mode not in self.distance_by_mode:
            self.distance_by_mode[mode] = 0    
        return self.distance_by_mode[mode]

    def update_mainmode_concise(self):
        self.mainmode_concise = ModalChoice.get_car_noncar_mode(self.mainmode)
        
