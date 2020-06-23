#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 16:50:49 2019

@author: mehrdad
"""

import numpy as np
import pandas as pd
#import shapely.geometry as geo
import tslib.gis
import tslib.mining
import tslib.trip

from pyfiles.common.modalchoice import ModalChoice
from pyfiles.common.trip import Trip
from commonlayer.common_helper_class import CommonHelper 


# ----------------------------------------------------------------------

PT_MODES = ['BUS', 'TRAM', 'RAIL', 'SUBWAY', 'FERRY', 'PT_SMALL_SHARE', 'PT_MULTIMODE']
PT_SINGLE_MODES = ['BUS', 'TRAM', 'RAIL', 'SUBWAY', 'FERRY']

# ----------------------------------------------------------------------


def filter_incorrect_detections(trips, max_speed, max_roundtrip_od_distance, min_traveled_to_od_distance_coeff):
    rounds = get_roundtrips(trips, max_roundtrip_od_distance, min_traveled_to_od_distance_coeff)
    
    # It is OK for 'od_distance' to be ZERO, but 'travelled-distance' should be > 0
    #b = trips[trips.speed > max_speed]
    b = trips[(trips.speed > 150) | (trips.distance==0)] 
        
    # np.sum(trips.od_speed > trips.speed) # TODO: what are these?!!!

    bad_trips = pd.concat([rounds, b]).drop_duplicates()
    good_trips = trips[~trips.index.isin(bad_trips.index.values)]
    
    return good_trips, bad_trips, rounds

def get_correct_trips(trips, min_route_distance, min_urban_speed, max_urban_speed, max_walk_speed):
    # TODO! For now ... IMPORTANT to AVOID ERROR in delta_active_distance     
    trips = trips[trips.distance >= trips.od_distance2] # TODO: review why distance has error    
    trips = trips[(trips.distance > min_route_distance) & (trips.speed <= max_urban_speed) & (trips.speed >= min_urban_speed)]
    
    # apply the expected walk speed range:
    trips = trips[(trips.mainmode!='WALK') | (trips.speed < max_walk_speed)]
    
    return trips
    
def get_roundtrips(legs, max_od_distance, min_traveled_to_od_distance_coeff):
    coeff = 1/min_traveled_to_od_distance_coeff
    T = legs[legs.distance > 0] # It is OK for 'od_distance' to be ZERO, but 'travelled-distance' should be > 0
    return T[(T.od_distance < max_od_distance) & (T.od_distance/T.distance < coeff)]

def get_circle_trips(legs, min_traveled_to_od_distance_coeff):
    coeff = 1/min_traveled_to_od_distance_coeff
    T = legs[legs.distance > 0] # It is OK for 'od_distance' to be ZERO, but 'travelled-distance' should be > 0
    return T[T.od_distance/T.distance < coeff]

#def get_path_points_boundaries(path):   
#    route = pd.DataFrame(path, columns={'lats', 'lons'})
#    return (np.min(route.lats), np.min(route.lons)), (np.max(route.lats), np.max(route.lons))
#
#def get_legs_boundaries(df):
#    A = df.apply(lambda x: get_path_points_boundaries(x.path_human_readable), axis=1)        
#    B = pd.DataFrame(data=A.values.tolist(), columns={'a', 'b' }, index=df.index)
#    return B

def filter_by_region_from_path(df, region_name):
    B = tslib.gis.get_legs_boundaries(df)        
    olats = B.a.apply(lambda x: x[0])
    olons = B.a.apply(lambda x: x[1])
    dlats = B.b.apply(lambda x: x[0])
    dlons = B.b.apply(lambda x: x[1])
        
    return __filter_by_region(df, region_name, olats, olons, dlats, dlons)
    

def filter_by_region_from_OD(df, region_name):
    olats = df.origin.apply(lambda x: x[0])
    olons = df.origin.apply(lambda x: x[1])
    dlats = df.destination.apply(lambda x: x[0])
    dlons = df.destination.apply(lambda x: x[1])
    
    return __filter_by_region(df, region_name, olats, olons, dlats, dlons)
    
def __filter_by_region(df, region_name, olats, olons, dlats, dlons):    
    #Filter by region
    #AND point(geometry(t.origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
    #AND point(geometry(t.destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
    if region_name=='Helsinki':
        # df = df[np.logical_and(dlons>24.572978, dlons<25.216365, dlats>60.100104, dlats<60.336453)]
        df = df[(olons>24.572978) & (olons<25.216365) & (olats>60.100104) & (olats<60.336453)]
        df = df[(dlons>24.572978) & (dlons<25.216365) & (dlats>60.100104) & (dlats<60.336453)]
    elif region_name=='Jätkäsaari':
        # Jätkäsaari region rectangular boundaries ------------------------------------------------------
        #	(bottom left: 60.147222, 24.900635 
        #	 top right: 60.162214, 24.925655)        
        df_origins = df[(olons>24.900635) & (olons<24.925655) & (olats>60.147222) & (olats<60.162214)]
        df_destinations = df[(dlons>24.900635) & (dlons<24.925655) & (dlats>60.147222) & (dlats<60.162214)]        
        df = pd.concat([df_origins, df_destinations])
    elif region_name=='Jätkäsaari Large':
        # Greater Jätkäsaari rectangular boundaries ---------------------------------------------------------
        # Left Bottom: 60.145601 24.895571
        # Top Right: 60.168201 24.931923
        df_origins = df[(olons>24.895571) & (olons<24.931923) & (olats>60.145601) & (olats<60.168201)]
        df_destinations = df[(dlons>24.895571) & (dlons<24.931923) & (dlats>60.145601) & (dlats<60.168201)]        
        df = pd.concat([df_origins, df_destinations])
        
    return df

# -----------------------------------------------------------------------------------
def init_trips(trips):
    trips['start_date'] = trips.start_time.apply(lambda x: x.date())
    trips['duration_in_min'] = trips.duration.apply(tslib.common.duration_to_minutes)    
    trips['origin'] = list(zip(trips.olat.values, trips.olon.values))    
    trips['destination'] = list(zip(trips.dlat.values, trips.dlon.values))    
    trips['speed'] = (trips.distance/1000.0)/(trips.duration_in_min/60) # km/h    
    trips['od_speed'] = (trips.od_distance/1000.0)/(trips.duration_in_min/60) # km/h    
    trips['od_distance2'] = tslib.gis.get_point_distance_vecotrized(trips.olat, trips.olon, trips.dlat, trips.dlon)
    #trips['od_distance2'] = trips.apply(lambda x: tslib.gis.get_point_distance(x.origin,x.destination), axis=1)        
    compute_distances_by_modegroup(trips)
    

def compute_distances_by_modegroup(trips):
    # TODO OLD REMOVE
    #    trips['walk_distance'] = trips.distance_by_mode.apply(lambda x: json.loads(x)['WALK'])
    #    trips['bike_distance'] = trips.distance_by_mode.apply(lambda x: json.loads(x)['BICYCLE'])
    #    trips['ebike_distance'] = trips.distance_by_mode.apply(lambda x: json.loads(x)['EBICYCLE'])
    trips['walk_distance'] = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'WALK'))
    trips['bike_distance'] = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'BICYCLE'))
    trips['ebike_distance'] = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'EBICYCLE'))
    trips['active_distance'] = trips.walk_distance + trips.bike_distance + trips.ebike_distance    
    trips['car_distance'] = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'CAR'))      
    trips['pt_distance'] = np.round(trips.distance - (trips.car_distance + trips.active_distance))

    
def compute_leg_counts(trips): # Called only after legs on the same vehicle (unnecessarily divided) are combined (i.e. inter-leg idle times discarded)
    trips['leg_count'] = trips.multimodal_summary.apply(tslib.trip.get_leg_count)
    
    trips['walk_leg_count'] = trips.multimodal_summary.apply(lambda x: tslib.trip.get_mode_leg_count(x, 'WALK'))
    trips['bike_leg_count'] = trips.multimodal_summary.apply(lambda x: tslib.trip.get_mode_leg_count(x, 'BICYCLE'))
    trips['ebike_leg_count'] = trips.multimodal_summary.apply(lambda x: tslib.trip.get_mode_leg_count(x, 'EBICYCLE'))
    
    trips['pt_leg_count'] = trips.multimodal_summary.apply(tslib.trip.get_pt_leg_count)
    trips['car_leg_count'] = trips.multimodal_summary.apply(tslib.trip.get_mode_leg_count, args=['CAR'])
    trips['motorized_leg_count'] = trips.pt_leg_count + trips.car_leg_count
    
    trips['bus_leg_count'] = trips.multimodal_summary.apply(tslib.trip.get_mode_leg_count, args=['BUS'])
    trips['metro_leg_count'] = trips.multimodal_summary.apply(tslib.trip.get_mode_leg_count, args=['SUBWAY'])
    # TODO: Warning, if we have mode-names such as 'EBICYCLE', 'ECAR', etc., str.count() could be misleading
    trips['train_leg_count'] = trips.multimodal_summary.apply(lambda x: x.count('RAIL'))
    trips['tram_leg_count'] = trips.multimodal_summary.apply(lambda x: x.count('TRAM'))
    trips['ferry_leg_count'] = trips.multimodal_summary.apply(lambda x: x.count('FERRY'))

def compute_trasfer_counts(trips): # Called only after legs on the same vehicle (unnecessarily divided) are combined (i.e. inter-leg idle times discarded)
    trips['pt_transfer_count'] = trips.pt_leg_count.apply(tslib.trip.get_pt_transfer_count)
   

def make_backwards_compatible_with_first_paper_code(observed_trips, computed_trips, observed_vs_computed_deltas, substitutes):
    # --- Load and prepare for backwards-compatiblity with the code of first paper ---------------------------------------
    #trips_and_alts = pd.read_csv("./"+input_folder+"/observed trips and computed time-relevant alts (ebike).csv")
    dft1 = pd.merge(observed_trips, substitutes, left_index=True, right_index=True, how='left')
    dft2 = pd.merge(dft1, observed_vs_computed_deltas, left_index=True, right_index=True, how='left')
    dft3 = pd.merge(dft2, computed_trips[['mode']], left_index=True, right_index=True, how='left', suffixes=['','_alt'])
    dft3.rename(columns={'mode_alt':'altmode'}, inplace=True)
    dft3.reset_index(inplace=True)
    dft3.fillna(0.0, inplace=True)
    dft3.rename(columns={'plan_id':'alt_plan_id'}, inplace=True)
    trips_and_alts = dft3
    #trips_and_alts = dft3.set_index(drop=False, keys=['user','trip'])
    
    # Important: 
    #   This should only include: car to low-carbon (for backwards compatibility to the code used in the first paper)
    from_modes = ['CAR']
    to_modes = list(computed_trips['mode'].unique())
    to_modes.remove('CAR')
    car_trips_with_shift = tslib.modal_shift.get_trips_with_shift(observed_trips, computed_trips, substitutes, from_modes, to_modes)
    dft1b = pd.merge(observed_trips, car_trips_with_shift[[]], left_index=True, right_index=True, how='inner')
    dft2b = pd.merge(dft1b, observed_vs_computed_deltas, left_index=True, right_index=True, how='inner')
    dft3b = pd.merge(dft2b, computed_trips[['mode']], left_index=True, right_index=True, how='inner', suffixes=['','_alt'])
    dft3b.rename(columns={'mode_alt':'altmode'}, inplace=True)
    dft3b.reset_index(inplace=True)
    dft3b.fillna(0.0, inplace=True)
    transferables  = dft3b   # the length is equal to car_trips_with_shift
    #transferables = dft.set_index(drop=False, keys=['user','trip','plan_id'])
    
    trips_all_details = observed_trips.reset_index()
    
    #---------------------------------------------------------------------------
    # Prepare for backward compatibility with the code of first paper ----------
    trips_and_alts['emission_reduced'] = trips_and_alts.deltaE
    trips_and_alts['active_distance_increased'] = -trips_and_alts.delta_AD
    trips_and_alts['walking_distance_increased'] = -trips_and_alts.delta_walk_D
    trips_and_alts['bike_distance_increased'] = -trips_and_alts.delta_bike_D
    
    transferables['emission_reduced'] = transferables.deltaE
    transferables['active_distance_increased'] = -transferables.delta_AD
    transferables['walking_distance_increased'] = -transferables.delta_walk_D
    transferables['bike_distance_increased'] = -transferables.delta_bike_D
    
    return trips_all_details, trips_and_alts, transferables

# ---------------------------------------------------------------
def make_trips_df_ready_for_matlab(df):
    dft = df.copy()

#    keySet =   {'CAR', 'FERRY', 'BUS', 'TRAM', 'RAIL', 'SUBWAY' , 'BICYCLE', 'RUN', 'WALK'};
#    valueSet = [1, 2, 3, 4, 5, 6, 7, 8, 9];   
    # TODO ... why RUN and WALK have the same key vaue 8?????
    modemap = dict(CAR=1, FERRY=2, BUS=3, TRAM=4, RAIL=5, SUBWAY=6, BICYCLE=7, RUN=8, WALK=8, EBICYCLE=10)
    dft['mode'] = dft['mode'].apply(lambda x: modemap[x])
    dft.altmode = dft['altmode'].apply(lambda x: modemap[x])
    transfermap = dict(t=1, f=0)
    dft.transferable = dft.transferable.apply(lambda x: transfermap[x])
    
    # process differently, the data from different sources
    if dft['duration'].dtype == ('O'):
        duration = pd.DatetimeIndex(dft.duration)    
        minutes = duration.hour*60 + duration.minute + duration.second/60.0
    else:
        minutes = dft.duration.dt.total_seconds()/60
    dft.duration = minutes
    
    if 'start_time' in dft.columns:
        dft = dft.drop(columns='start_time')

    if 'origin' in dft.columns:
        dft = dft.drop(columns='origin')
    if 'destination' in dft.columns:
        dft = dft.drop(columns='destination')
    
    return dft


# ================= trip extraction ===========================
    
# works based on a state-diagram approach:
# 'actvity location' is a state and 'leg' is a transition from one state to another
# note: refer to paper notes
def extract_trips_from_legs(legs_db_rows, max_trip_id_per_user, idle_times, urban_leg_max_km):
    trips = []
    trip = None        
    # leg_index = 0 #TODO: not needed anymore?
    lastleg = None
    at_activity_location = True # first trip (of each user*) starts with first leg record (one reason is to avoid 'shifted trip extraction')
    at_new_user = False
    lastuserid = None
    
    # TODO, NOTE!: are there more problems in detecting trip_started_here (because of mode detection delay) ??? 
    
    two_leg_round_trips = 0
    returned_to_inermediate_destination = 0
    
    # TODO: Is the db_res closed and erased once iteration reaches end of the rows?!!!
    for leg_row in legs_db_rows:
        #print leg['time_start'], leg['time_end'], leg['activity'], leg['line_type']                    

        leg = dict(leg_row.items()) # Because we want a copy to change fields just in case
                
        if leg['activity'] != 'STILL' and leg['user_id'] is not None: 
                    # skip STILL legs
            # skip over different mode-detections of same leg! (trick: now our query sorts by 'USER', 'LIVE', 'PLANNER')
            if lastleg is not None and leg['id'] == lastleg['id']:
                #print("NOTE! more than one mode for leg",leg['id'],"; ")
                #print("    activity:", lastleg['activity'], lastleg['line_type'], lastleg['line_name'], lastleg['line_source'])
                #print("    activity:", leg['activity'], leg['line_type'], leg['line_name'], leg['line_source'])
                continue # Do NOT update the leg.mode based on this record (the top-most mode on the list is the priority)
        
            # Important line!!! to adapt new schema change leg--mode specially for USER-changed mode            
            leg['activity'] = ModalChoice.get_leg_activity_name(leg)
            leg['line_type'] = ModalChoice.get_leg_line_type(leg)
            
            # detect arriving at a new user's leg record *:
            if leg['user_id'] != lastuserid:
                # reset trip_id and other params for the new user:
                trip_id_index = max_trip_id_per_user[max_trip_id_per_user.user_id == leg['user_id']].max_trip_id.values[0]
                lastuserid = leg['user_id']
                at_new_user = True
        
            # detect 'activity locations' ***: 
            if not at_new_user and lastleg is not None:                                             
                legs_time_distance = leg['time_start'] - lastleg['time_end']
                if legs_time_distance > idle_times['ALL']: # TODO: and other conditions ...                        
                    at_activity_location = True # last trip ends here & next trip starts here
                # between two car legs:
                #   e.g., assuming there cannot be more than 5 minutes wait at traffic light or intersection
                #   TODO: how about short stops to do something?! Quite difficult to detect
                # Note: order of conditions below os so, to run faster
                elif (legs_time_distance > idle_times['CAR'] and legs_time_distance <= idle_times['ALL'] and\
                      ModalChoice.is_car_leg(leg) and ModalChoice.is_car_leg(lastleg)):
                    at_activity_location = True
                    print("leg-IDs:",lastleg['id'],"->",leg['id'],"; From one car-leg to another car-leg; New trip started; Max idle-time considered =",idle_times['CAR'])
                else:
                    at_activity_location = False

                # Detect the 2-leg round trips. Save them as two separate trips                
                if not at_activity_location:
                    last_leg_OD_D = tslib.gis.get_point_distance((lastleg['dlat'],lastleg['dlon']), (lastleg['olat'],lastleg['olon']))                    
                    D = tslib.gis.get_point_distance((leg['dlat'],leg['dlon']), (lastleg['olat'],lastleg['olon']))
                    if(last_leg_OD_D > tslib.mining.OD_CLUSTER_RADIUS and D < tslib.mining.OD_CLUSTER_RADIUS/2):
                        if len(trip.legs) == 1:
                            print("leg-IDs:",lastleg['id'],"->",leg['id'],"; WARNING! Detected two-leg round trip; Ending current trip here; current-Destination to last-Origin =",np.round(D),"(meters);",
                                  "last_leg_OD_distance=",np.round(last_leg_OD_D))
                            at_activity_location = True
                            two_leg_round_trips += 1
                            pass
                        else:
                            # strange leg sequence!
                            print("leg-IDs:",lastleg['id'],"->",leg['id'], "WARNING!! Strange leg sequence; This leg returned to an intermediate destination of trip; D =",np.round(D),
                                  "(km); But we continute anyways!; Current trip leg-count =", len(trip.legs))
                            trip.has_a_return_to_intermediate_destination = True
                            returned_to_inermediate_destination += 1
                            pass
                        
                # Detect 'non-urban' leg by looking at travel distance. Save legs so far as a separate trip.
                # e.g. Maybe the person went from home to central train station, then traveled to another city
                if not at_activity_location:
                    if 'distance_km' in leg and leg['distance_km'] is not None and leg['distance_km'] > urban_leg_max_km:
                        print("leg-IDs:",lastleg['id'],"->",leg['id'],"WARNING! Detected long leg, assumed as non-urban; Ending current trip here; Current trip leg-count=", len(trip.legs),
                              ';',"leg.distance_km=",leg['distance_km'],'(km)')
                        at_activity_location = True
                        
            
            # act accordingly at 'activity location' or when a new user
            if at_new_user or at_activity_location:
                if trip is not None: # if we had started a trip and it's still open-ended
                    # end current trip here: 
                    trip.destination = CommonHelper.geoJSON_to_pointRow(lastleg['destination'])
                    trip.destination_tuple = lastleg['destination_tuple']
                    trip.endtime = lastleg['time_end'] 
                    trips.append(trip) # add it to the collection of extracted trips *
                    trip = None
                # start a new trip from the current leg:
                trip_id_index += 1
                trip = Trip()
                trip.user_id = leg['user_id']
                trip.device_id = leg['device_id']                    
                trip.id = trip_id_index
                trip.plan_id = 0 # this is the actual trip (we're processing only the actual recorded trips in this function)
                trip.origin = CommonHelper.geoJSON_to_pointRow(leg['origin'])
                trip.origin_tuple = leg['origin_tuple']
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
        trip.destination_tuple = lastleg['destination_tuple']
        trip.endtime = lastleg['time_end']          
        trips.append(trip)

    print ("extract_trips_from_legs():: Total number of detected trips =", len(trips))    
    print ("extract_trips_from_legs():: Total number of detected and FIXED two-leg round trips =", two_leg_round_trips)
    print ("extract_trips_from_legs():: Total number of detected round legs to intermediate destination (not fixed) =", returned_to_inermediate_destination)    
    
    return trips



def get_trips_by_mode(trips, desire_modes):
    trips = trips[trips['mainmode'].isin(desire_modes)]
    return trips.copy()

def get_alts_by_planid(trips, plan_ids):
    # in trip_plans DB table, supposed to be ['WALK', 'BICYCLE', 'CAR', 'PUBLIC_TRANSPORT'] as: 1, 2, 3,  4,5,6
    return trips[trips.index.get_level_values(2).isin(plan_ids)]



# ============== emission calculation ===============
# CO2 grams/passenger-km, i.e. *After* dividing CO2-grams/km by the average passengers in vehicle ('occupancy'):
# Used for paper2:
CO2_E_PKM = {"BUS":52, "TRAM":0, "RAIL":0, "SUBWAY":0, "FERRY":389, 
             "CAR":89, # with occpancy of 1.7: "CAR":89, 
             "BICYCLE":0, "EBICYCLE":0, 
             "WALK":0, "RUN":0}
# Reference:
#   Cars (See the CO2 section): 
#       For an overal summary (not car specific), click on: 'Passenger cars on average'
#          lipasto.vtt.fi/yksikkopaastot/henkiloliikennee/tieliikennee/henkilo_tiee.htm       
#      lipasto.vtt.fi/yksikkopaastot/henkiloliikennee/tieliikennee/henkiloautote/hakeskimaarine.htm
#      lipasto.vtt.fi/yksikkopaastot/henkiloliikennee/tieliikennee/henkiloautote/hayhte.htm
#   Metro, Tram and Train:
#       lipasto.vtt.fi/yksikkopaastot/henkiloliikennee/raideliikennee/henkilo_raidee.htm
#       Converting energy consumption per pkm (kWh) to emission:
#          http://lipasto.vtt.fi/yksikkopaastot/infoe_raide.htm
#          http://lipasto.vtt.fi/yksikkopaastot/standardi.htm#5
#          Possible sources regarding CO2 of producing the electricity used by tram/metro/train:
#               www.helen.fi/en/company/energy/energy-production/origin-of-energy
#               www.helen.fi/en/company/energy/energy-production/energy-production2
#               energychallenge.hel.fi/
#               search for: helsinki electricity source of trams and trains energy

# TODO: How about emissions other than CO2, like CO, NOx, PM ?!
def calc_emission_by_distances(distances, mode_str):
    return distances/1000 * CO2_E_PKM[mode_str]

# The approach here is batch computation (per-trip-leg calculation not needed)
# This is possible now that we already have the per-trip-leg distances, from the Trip Extraction phase
def compute_trips_emissions(trips):
    car_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'CAR'))
    bus_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'BUS'))
    tram_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'TRAM'))
    metro_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'SUBWAY'))
    train_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'RAIL'))
    ferry_Ds = trips.distance_by_mode.apply(lambda x: tslib.trip.get_att_by_mode(x, 'FERRY'))
    
    car_Es = calc_emission_by_distances(car_Ds, 'CAR')
    bus_Es = calc_emission_by_distances(bus_Ds, 'BUS')
    tram_Es = calc_emission_by_distances(tram_Ds, 'TRAM')
    metro_Es = calc_emission_by_distances(metro_Ds, 'SUBWAY')
    train_Es = calc_emission_by_distances(train_Ds, 'RAIL')
    ferry_Es = calc_emission_by_distances(ferry_Ds, 'FERRY')

    trip_Es = car_Es + bus_Es + tram_Es + metro_Es + train_Es + ferry_Es
    
    return trip_Es


# ============== mainmode classification per trips ===============

# The approach here is batch computation (per-trip-leg calculation not needed)
# The per-leg summaries already calculated in the Trip Eetraction phase    
def compute_mainmode_of_PT_trips(trips):
    # Note: PT_SMALL_SHARE does not make sense for computed trips because we specifically ask OTP for the desired mode (walk, bike, PT)
    #       At the moment we do not compute multimodal trips that involve e.g. both bike and PT or bike and car.

    pt_trips = trips[trips.pt_leg_count > 0]
    # test and verification:
    #   pt_trips.reset_index().plan_id.value_counts()
    #       NOTE: Around 450 PT computed trips have been saved with plan_id < 4 !
    #   pt_trips.pt_distance.describe()
    #       min is 27 meters!
    
    # set the mainmodes
    revise1 = pt_trips[pt_trips.pt_leg_count == pt_trips.bus_leg_count]
    trips.loc[trips.index.isin(revise1.index), 'mainmode'] = 'BUS'

    revise2 = pt_trips[pt_trips.pt_leg_count == pt_trips.metro_leg_count]
    trips.loc[trips.index.isin(revise2.index), 'mainmode'] = 'SUBWAY'
    
    revise3 = pt_trips[pt_trips.pt_leg_count == pt_trips.train_leg_count]
    trips.loc[trips.index.isin(revise3.index), 'mainmode'] = 'RAIL'

    revise4 = pt_trips[pt_trips.pt_leg_count == pt_trips.tram_leg_count]
    trips.loc[trips.index.isin(revise4.index), 'mainmode'] = 'TRAM'    

    revise5 = pt_trips[pt_trips.pt_leg_count == pt_trips.ferry_leg_count]
    trips.loc[trips.index.isin(revise5.index), 'mainmode'] = 'FERRY'
    
    single_mode_pt_trips = pd.concat([revise1, revise2, revise3, revise4, revise5])
    revise_multimode = pt_trips[~ pt_trips.index.isin(single_mode_pt_trips.index)]    
    trips.loc[trips.index.isin(revise_multimode.index), 'mainmode'] = 'PT_MULTIMODE'

   
    
def compute_mainmode_of_non_PT_trips(trips):
    #. Detect based on leg counts
    #. Plus, filter against plan_id, that reflects what mainmode was originally asked from OTP to plan
    #   Now the alt computation function sets plan_id according to 'plan_id_base = MODES_PLAN_IDS[mode]'
    
    # Walk
    walk_alts = trips[trips.walk_leg_count == trips.leg_count]
    trips.loc[trips.index.isin(walk_alts.index), 'mainmode'] = 'WALK'
    # discard_computed_trips_not_matching_intended_mode
    bad_walk_plans = walk_alts[walk_alts.reset_index().plan_id.values != 1]    
    revise = tslib.trip_detection.get_alts_by_planid(bad_walk_plans, [4,5,6]) # only can be PT alts    
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'PT_PLANNED_AS_WALK'
    revise = tslib.trip_detection.get_alts_by_planid(bad_walk_plans, [2])
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'BICYCLE_PLANNED_AS_WALK'
    revise = tslib.trip_detection.get_alts_by_planid(bad_walk_plans, [3])
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'CAR_PLANNED_AS_WALK'    
    
    # Bike
    bike_alts = trips[trips.bike_leg_count > 0]
    trips.loc[trips.index.isin(bike_alts.index), 'mainmode'] = 'BICYCLE'
    bad_bike_plans = bike_alts[bike_alts.reset_index().plan_id.values != 2]    
    revise = tslib.trip_detection.get_alts_by_planid(bad_bike_plans, [1,3,4,5,6,7])
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'SOMETHING_PLANNED_AS_BIKE'

    # E-Bike
    ebike_alts = trips[trips.ebike_leg_count > 0]
    trips.loc[trips.index.isin(ebike_alts.index), 'mainmode'] = 'EBICYCLE'
    bad_plans = ebike_alts[ebike_alts.reset_index().plan_id.values != 7]    
    revise = tslib.trip_detection.get_alts_by_planid(bad_plans, [1,2,3,4,5,6])
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'SOMETHING_PLANNED_AS_EBIKE'
    
    # Car
    car_alts = trips[trips.car_leg_count > 0]
    trips.loc[trips.index.isin(car_alts.index), 'mainmode'] = 'CAR'
    bad_car_plans = car_alts[car_alts.reset_index().plan_id.values != 3]    
    revise = bad_car_plans
    trips.loc[trips.index.isin(revise.index), 'mainmode'] = 'SOMETHING_PLANNED_AS_CAR'
  
    # redundant data column, backwards compatible
    trips['old_mode'] = trips['mode'] # Keep old values
    trips['mode'] = trips['mainmode']
    
