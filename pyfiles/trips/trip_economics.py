
from datetime import timedelta
from pyfiles.common.modalchoice import (PublicTransportModesTemplate)
from commonlayer.logger import (logi, loge, log, logexc)
from commonlayer.common_helper_class import (CommonHelper)


MAX_GPS_ERROR = 50 # (in meters) TODO: if error larger than this, we've discarded that point?? 
MAX_VEHICLE_LENGTH = 50 # TODO: eg, how about trains?


#NOTE: OTP modes ref: http://dev.opentripplanner.org/apidoc/0.15.0/ns0_TraverseMode.html
#TODO update code: TRAM, RAIL, SUBWAY emission should NOT be 0, as it sould include emission from electricity production
PassengerByMode = None # Not used here yet
emissionsPerPassengerKmByMode = None # Not used here yet
# Not used yet: emissionsPerKmByMode = PassengerByMode x emissionsPerPassengerKmByMode
# NOTE! Following values are *after* considering avg passengers per transit vehicle (except* 'CAR' for which passenger/car is retrieved from user profile)
# First paper:
emissionsPerKmByMode = {"WALK":0, "RUN":0, "BUS": 73, "TRAM":0, "RAIL":0, "FERRY":389, "CAR":171, "SUBWAY":0, "BICYCLE":0, "EBICYCLE":0} # g/passenger-km
# Second paper: TODO: recalc
# emissionsPerKmByMode = {"WALK":0, "RUN":0, "BUS": 52, "TRAM":0, "RAIL":0, "FERRY":389, "CAR":89, "SUBWAY":0, "BICYCLE":0, "EBICYCLE":0} # g/passenger-km

caloriesPerKmByMode = {"WALK":72.3, "RUN":72.3, "BICYCLE":16.2, "EBICYCLE":13} #NOTE: refer to sushi docs (walk cals = run cals)

oneTimeCostByMode = {"BUS":3 , "TRAM":1.5, "RAIL":3, "FERRY":3, "SUBWAY":3}  # eur
monthlyCostByMode = {"BUS":102 , "TRAM":102, "RAIL":102, "FERRY":102, "SUBWAY":102} # eur #TODO assumption: there's one monthly pass covering all modes

intermediateMode = 'OTHER'

# TODO values for now based on Volkswagen Golf 1.4 90 KW Trendline (Or Equivalent New Car)
# TODO get from user profile later
fuelPer100KmByVehicleType = {"hatchback": 9.3} # unit: litre/100km
fuelCostPerLiterByCity = {"helsinki": 1.6} # eur
depreciationPerKmByVehicleType = {"hatchback": 0.0625} # eur
carInsurance = 200 # eur

# TODO: get from user profile later
has_montly_pass = True
passengers_per_car = 1
avg_trips_per_day = 2


# -------- trip economics, comparison, SUSHI, etc. --------------------------    
class TripEconomics:
    def __init__(self, legs_dal):
        self.legs_dal = legs_dal

    def calculate_trips_economics(self, trips):
        # calculate params for each trip
        for trip in trips:
            # calculate params per trip (each trip has a modal-choice chain eg. WALK->CAR that results in certain param values e.g.: time:x, cost:y, ...):
            self.__calculate_trip_economics(trip)

    def calculate_trips_alts_economics(self, trips):
        # calculate params for all alternative trips assigned to each trip
        for trip in trips:
            # calculate params per alt-trip (each trip has a modal-choice chain eg. WALK->CAR that results in certain param values e.g.: time:x, cost:y, ...):
            for tripalt in trip.alternative_trips:
                self.__calculate_trip_economics(tripalt)                
        
    def __calculate_trip_economics(self, trip):
        # note: order is partly important
        #try:
            self.__get_trip_time(trip)
            self.__get_trip_distances(trip)
            self.__get_trip_cost(trip)
            self.__get_trip_calories(trip)
            self.__get_trip_emission(trip)
            self.__get_trip_comfort(trip)                
            self.get_trip_mainmode(trip)
            self.get_trip_multimodal_summary(trip)
        #except Exception as e:
        #    loge(["trip:",trip.user_id,"|",trip.device_id,"|",trip.id,"|",trip.plan_id, " - (!) EXCEPTION catched in calculate_trip_economics():", e])
    
    def get_trip_mainmode(self, trip):
        if len(trip.legs)>0:
            trip.mainmode = None
            if len(trip.legs) == 1:
                leg = trip.legs[0]
                trip.mainmode = leg['mode']
            else:
                for leg in trip.legs: # TODO need to change later? #TODO: how to have a 'main mode' for multimodal trips? eg.: walk -> bike -> train -> bike -> walk
                    if leg['mode'] in {'CAR', 'BICYCLE'} or leg['mode'] in PublicTransportModesTemplate:
                        trip.mainmode = leg['mode']
                        break
                        
            startted_with_walk = (trip.legs[0]=='WALK')
            ended_with_walk = (trip.legs[-1]=='WALK')
            
            if trip.mainmode is None: # TODO: improve later. possible exceptions when this wouldn't recognize 'WALK'?
                trip.mainmode = trip.legs[0]['mode']
        else:
            print("Warning! A trip with no legs!","(",trip.user_id, trip.id,")")
            trip.mainmode = 'NO_LEG'
            
    def get_trip_multimodal_summary(self, trip):
        modalstr = ""
        for leg in trip.legs:
            if modalstr != "":
                modalstr += "->"
            modalstr += leg['mode']
        trip.multimodal_summary = modalstr
   
    def __get_trip_time(self, trip):
        trip.duration = trip.endtime - trip.starttime
        trip.duration_by_mode = {}
        total_legs_duration = timedelta(0)
        for leg in trip.legs:
            legduration = leg['duration']
            trip.add_duration(leg['mode'], legduration) # for now 'total' trip duration is NOT calculated in this function
            total_legs_duration += legduration
        trip.add_duration(intermediateMode, trip.duration - total_legs_duration) #if duration from OTP and duration computated here do not match
            
    def __get_trip_distances(self, trip):
        trip.od_distance = CommonHelper.point_distance(trip.origin, trip.destination)
        #TODO TEMP
        #if trip.od_distance == 0:
        #   print("WARNING!!! in __get_trip_distances(): od_distance is 0, for trip ID:",trip.id," OD:",trip.origin, trip.destination)
        trip.legs_without_points = []
        trip.distance = 0
        trip.distance_by_mode = {}
        for leg in trip.legs:            
            # distance by mode .....:
            # first calcualtes and SETs leg['distance'] values ... TODO!!! should be done elsewhere for example during leg-detection?
            if leg['is_moprim_leg']:
                pass #TODO: for legs retrieved from OTP, presumably, leg['distance'] is accurate enough (is point-to-point based)
            elif leg['is_otp_leg']:
                pass #TODO: for legs retrieved from OTP, presumably, leg['distance'] is accurate enough (is point-to-point based)
            else: #i.e: leg from original points recorded by user device
                leg['od_distance'] = CommonHelper.point_distance(CommonHelper.geoJSON_to_pointRow(leg['origin']), CommonHelper.geoJSON_to_pointRow(leg['destination'])) 
            
                # Calc travelled-distance, point to point based here, OR Write a plsql-like function that does so on DB server
                leg_points_rows = self.legs_dal.get_leg_points(leg)           
                leg['distance'] = self.__calculate_trajectory_distance(leg_points_rows)
                if leg_points_rows.rowcount == 0:
                    log(["Warning in __get_trip_distances()!: legs_dal.get_leg_points(leg) returned ZERO points. For leg ("+str(leg['user_id'])+' '+
                          str(trip.id)+" "+str(leg['id'])+ "; device_id="+str(leg['device_id'])+'; '+str(leg['time_start'])+', '+str(leg['time_end'])])
                    trip.legs_without_points.append(leg)
            # add up leg-distances to total trip.distance: 
            trip.add_travelled_distance(leg['mode'], leg['distance']) # NOTE: 'total distance' of trip is increased inside this function
            
    
    # TODO: verify this function, with round-trip trips for example ******
    def __calculate_trajectory_distance(self, point_rows):
        maxDistanceForPointMatch = MAX_GPS_ERROR + MAX_VEHICLE_LENGTH
        
        distance = 0
        if point_rows.rowcount > 1:
            oldpoint = point_rows.fetchone()['coo']
            for leg_point in point_rows:
                point = leg_point['coo']                
                #coo = json.loads(point)['coordinates']
                #(coo[1], coo[0])                
                p2p_distance = CommonHelper.point_distance_byGeoJSON(point,  oldpoint)
                if p2p_distance >= maxDistanceForPointMatch:
                    distance += p2p_distance
                    oldpoint = point                  
            if oldpoint != point: #exception ... don't miss the last one
                p2p_distance = CommonHelper.point_distance_byGeoJSON(point,  oldpoint)
                distance += p2p_distance
                #print('__calculate_trajectory_distance():: Did not miss the last point!!!!!!!!!!!!!!!!!!!')
        return distance
    
    def __get_trip_cost(self, trip):
        trip.cost = 0
        trip.cost_by_mode = {}
        paid_for_transit = False
        for leg in trip.legs:
            # TODO: assumption, if user pays for one ticket for 'tram', can get on 'bus' with the same ticket (TODO: later consider: ticket expires in ?? minutes)
            legcost = self.__get_leg_cost(leg)
            if leg['transitLeg'] == True and paid_for_transit:
                legcost = 0                
            if leg['transitLeg'] == True:
                paid_for_transit = True
            trip.add_cost(leg['mode'], legcost) # NOTE: 'total cost' of trip is increased inside this function

    def __get_leg_cost(self, leg):                        
        if leg['mode'] == 'CAR':            
            cost = ((leg['distance']/1000.0)/100.0) * fuelPer100KmByVehicleType['hatchback'] * fuelCostPerLiterByCity['helsinki'] + \
                   (leg['distance']/1000.0) * depreciationPerKmByVehicleType['hatchback'] + \
                   carInsurance/(365 * avg_trips_per_day)                               
            # note: refer to 'greener transportation ...' doc files
            #Trip cost = distance * gallon/km * petrol-price + 
            #            parking cost + 
            #            (yearly maintenance and costs)/(365 * trips-per-day)                        
            cost = cost/passengers_per_car
        elif leg['transitLeg'] == True:
            if has_montly_pass:
                cost_per_trip = float(monthlyCostByMode[leg['mode']])/(30.0 * avg_trips_per_day)
                cost = cost_per_trip
            else:
                cost = oneTimeCostByMode[leg['mode']] #TODO add condition for monthly ticket
        else:
            cost = 0
        return cost
               
    def __get_trip_calories(self, trip):
        trip.calories = 0
        trip.calories_by_mode = {}
        trip.add_calories('WALK', self.get_trip_calories_by_mode(trip, 'WALK'))
        trip.add_calories('RUN', self.get_trip_calories_by_mode(trip, 'RUN'))
        trip.add_calories('BICYCLE', self.get_trip_calories_by_mode(trip, 'BICYCLE'))
        trip.add_calories('EBICYCLE', self.get_trip_calories_by_mode(trip, 'EBICYCLE'))
#        cals = 0
#        cals += self.get_trip_calories_by_mode(trip, 'WALK')
#        cals += self.get_trip_calories_by_mode(trip, 'RUN')
#        cals += self.get_trip_calories_by_mode(trip, 'BICYCLE')
#        cals += self.get_trip_calories_by_mode(trip, 'EBICYCLE')                                
#        trip.calories = cals        

    def get_trip_calories_by_mode(self, trip, mode):
        cals = (trip.get_distance_by_mode(mode)/1000.0) * caloriesPerKmByMode[mode]
        return cals
            
    def __get_trip_emission(self, trip):    
        trip.emission = 0
        trip.emission_by_mode = {}
        for leg in trip.legs:
            #legemission = self.get_leg_emission(leg)
            #trip.emission += legemission
            trip.add_emission(leg['mode'], self.__get_leg_emission(leg))
            
    def __get_leg_emission(self, leg):                
        emission = (leg['distance']/1000.0) * emissionsPerKmByMode[leg['mode']]
        return emission

    def __get_trip_comfort(self, trip):    
        trip.comfort = 50 # (%)
        # traverse all alerts of each leg
        try:
            for leg in trip.legs:            
                if 'alerts' in leg and leg['alerts'] is not None:
                    for alert in leg['alerts']:
                        if 'alertHeaderText' in alert and alert['alertHeaderText'] == 'Unpaved surface': #TODO is this even bad in case of 'WALK' or 'BICYCLE'?
                            trip.comfort -= 10
        except Exception as e:
            logexc(["trip:",trip.user_id,"|",trip.device_id,"|",trip.id,"|",trip.plan_id, " - (!) EXCEPTION catched in trip_economics.get_trip_comfort():"], e)
