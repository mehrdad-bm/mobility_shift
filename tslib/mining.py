#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 12:34:10 2019

@author: mehrdad
"""

import tslib.plot
import tslib.stats
import tslib.common
import pandas as pd
import numpy as np
import random
from sklearn.model_selection import train_test_split

# --- Algorothm constants and settings --------------------------------------
#mining_settings = {
#        'FILTER_ACTIVE_TRAVELLER': False,
#        'FILTER_NONACTIVE_TRAVELLER': False,
#        'FILTER_JÄTKÄSAARI': False,
#        }


# For trip detection, filtering noise:
MIN_VALID_URBAN_SPEED = 3 #(km/h) Note: Min walk speed is 0.94 m/s ~= 3.5 km/h
MAX_VALID_URBAN_SPEED = 150 #(km/h), for example based on tentative max intra-city train speed
MAX_VALID_WALK_SPEED = 5.5
TRAVELED_DISTANCE_TO_OD_DISTANCE_COEFF = 2.0

# For detection of main-mode of multimodal trips:
MIN_DISTANCE_SHARE_OF_MAINMODE = 0.7

# For clustering ODs of trips
OD_CLUSTER_RADIUS = 1000 # (in meters) # values: 250, 500, 1000
ROUTE_CLUSTER_RADIUS = 1000 # (in meters) # values: 250, 500, 1000
CLUSTERING_MAX_DELTA_OF_TRAVEL_DISTANCE = 2000

# For visualization and filtering of trip clusters, frequent/non-frequent, etc:
MIN_MODE_DETECTION_ERROR = 0.99 # default and the most reliable results: 0.99 (influenced by the TS mode detection noise)
MIN_MODAL_SHIFT_RAIO = 0.999 # Set to 0.9999 to get only car trips with 'consistent' modal shift
MIN_REPETITION_OF_FREQUENT_TRIPS = 3 # default: 3



FILTER_ACTIVE_TRAVELLER = False # Note: Enable this, only if needed
FILTER_NONACTIVE_TRAVELLER = False
MIN_DAYS_FOR_ACTIVE = 30 # default is 30


# -------------------------------------------------------------------

def filter_by_active_users(df, user_stats_df, min_needed_active_days = MIN_DAYS_FOR_ACTIVE):
    #Filter by active users
    active_users_df = user_stats_df[user_stats_df.active_days >= min_needed_active_days]
    df = df[df.user.isin(active_users_df.user.unique())]    
    return df
    
def filter_by_non_active_users(df, user_stats_df, min_needed_active_days = MIN_DAYS_FOR_ACTIVE):
    #Filter by active users
    nonactive_users_df = user_stats_df[user_stats_df.active_days < min_needed_active_days]
    df = df[df.user.isin(nonactive_users_df.user.unique())]    
    return df


def filter_by_clustes_per_person(observed_, trips_of_clusters_, min_clusters):
    # distribution of trip clusters---
    g = trips_of_clusters_.groupby(['user','cluster_index','D_cluster_index'])
    cluster_repetition1 = g.user.count().sort_values()
    
    dft = cluster_repetition1.to_frame('cluster_repetition').reset_index()
    clusters_per_person = dft.groupby('user').cluster_repetition.count().sort_values()
    clusters_per_person = clusters_per_person.rename('clusters')

    active_persons = (clusters_per_person[clusters_per_person >= min_clusters]).index.values
    # 72 people
    
    # now see how many days per person?
    filtered_trips = observed_[observed_.index.get_level_values(0).isin(active_persons)]
    
    return filtered_trips, active_persons


# -----------------------------------------------------------------------
# Try to normalize distributions, by reduing number of person-days of persons who have many recorded days
def normalize_by_days_per_person(observed_):
    # TODO: maybe later:
#    filtered_trips_indices = tslib.common.load_dataframe_from_file('./data/output/', 'more_even_trips_by_person_days___')
#    if len(filtered_trips) > 0:
#        pass
#    else:
#       compute the filtered_trips_indices
    
    days_per_person = observed_.groupby(['user']).start_date.unique().apply(len).sort_values()
    days_per_person = days_per_person.rename('days')

    threshold1 = days_per_person.mean() + days_per_person.std()
    threshold2 = days_per_person.mean() + 2 * days_per_person.std()    
    MAX_DAYS = np.round(threshold1, 0) # default: mean + 2 x std = 35

    all_persons = observed_.index.get_level_values(0).unique().values
    bad_persons = (days_per_person[days_per_person > MAX_DAYS]).to_frame('recorded_days').reset_index()

    # TODO TRY WITH random seed of  None, different results every time?
    sel_users = []
    sel_trips = []
    p1 = 1.0                
    random_seed = 123456 # defaul None. Chooses a different sample every time
    for person in all_persons:
        trips_of_person = observed_[(observed_.index.get_level_values(0) == person)]
        days_of_person = trips_of_person.start_date.unique()
        days_of_person.sort()
        
        if len(days_of_person) > MAX_DAYS:
            # randomly select N days from all days of cluster:
            sample_size = MAX_DAYS
            temp, some_days = train_test_split(days_of_person, test_size=int(p1*sample_size), random_state=random_seed)
            # pick all trips of the selected days
            selected_trips = trips_of_person[trips_of_person.start_date.isin(some_days)]
        else:
            # OK to choose all days
            selected_trips = trips_of_person 
            
        sel_users.extend(selected_trips.index.get_level_values(0).to_list())
        sel_trips.extend(selected_trips.index.get_level_values(1).to_list())
        
    filtered_trips_indices = pd.DataFrame({'user':sel_users, 'trip':sel_trips})    
    # TODO: maybe later
    #tslib.common.save_dataframe_to_file('./data/output/', 'trips_indices_filtered_by_person_days', filtered_trips_indices)

    filtered_trips = pd.merge(observed_, filtered_trips_indices.set_index(['user', 'trip']), left_index=True, right_index=True)
    
    return filtered_trips

def normalize_by_repetitions_per_cluster(trips_of_clusters__):
# Try to normalize cluster-size distribution, by reduing number of repetitions of clusters with large cluster-sizes    
    g = trips_of_clusters__.groupby(['user','cluster_index','D_cluster_index'])
    cluster_repetition1 = g.user.count().sort_values()
    
    threshold1 = cluster_repetition1.mean() + cluster_repetition1.std()
    threshold2 = cluster_repetition1.mean() + 2*cluster_repetition1.std()
    
    MAX_CLUSTER_SIZE = np.round(threshold2, 0) # default: mean + 2 x std = 35
    bad_clusters = (cluster_repetition1[cluster_repetition1 > MAX_CLUSTER_SIZE]).to_frame('cluster_repetition').reset_index()
    
    # TODO!!! THEN SHOLUD REMOVE THAT DAY FROM ALL CLUSTERS OF THAT PERSON!!!
    #   OTHERWISE MESSES UP THE PER-DAY ANALYSIS. 
    #   PER-DAY TOTAL DISTANCES ARE QUITE IMPORTANT
    
    sel_users = []
    sel_trips = []
    p1 = 1.0                
    random_seed = 123456 # defaul None. Chooses a different sample every time
    for cluster in bad_clusters.itertuples():        
        trips_of_this_cluster = trips_of_clusters__[(trips_of_clusters__.user==cluster.user) & 
                                                  (trips_of_clusters__.cluster_index==cluster.cluster_index) & 
                                                  (trips_of_clusters__.D_cluster_index==cluster.D_cluster_index)]

        days_of_cluster = trips_of_this_cluster.start_date.unique()
        days_of_cluster.sort()
        
        # Estimate N: How many days to choose, to have certain number of trips of this cluster:
        avg_trips_per_day = len(trips_of_this_cluster) / len(trips_of_this_cluster.start_date.unique())
        max_days = int(MAX_CLUSTER_SIZE/avg_trips_per_day)
        
        # randomly select N days from all days of cluster:
        sample_size = max_days
        temp, some_days = train_test_split(days_of_cluster, test_size=int(p1*sample_size), random_state=random_seed)
        
        # pick all trips of the selected days
        selected_trips = trips_of_this_cluster[trips_of_this_cluster.start_date.isin(some_days)]
        sel_users.extend(selected_trips.user.to_list())
        sel_trips.extend(selected_trips.trip.to_list())   
    normalized_trips_of_bad_clusters = pd.DataFrame({'user':sel_users, 'trip':sel_trips})


    good_clusters = (cluster_repetition1[cluster_repetition1 <= MAX_CLUSTER_SIZE]).to_frame('cluster_repetition').reset_index()    
    sel_users = []
    sel_trips = []
    for cluster in good_clusters.itertuples():        
        trips_of_this_cluster = trips_of_clusters__[(trips_of_clusters__.user==cluster.user) & 
                                                  (trips_of_clusters__.cluster_index==cluster.cluster_index) & 
                                                  (trips_of_clusters__.D_cluster_index==cluster.D_cluster_index)]
        sel_users.extend(trips_of_this_cluster.user.to_list())
        sel_trips.extend(trips_of_this_cluster.trip.to_list())   
    trips_of_good_clusters = pd.DataFrame({'user':sel_users, 'trip':sel_trips})

    # merge :
    final_trips = pd.concat([trips_of_good_clusters, normalized_trips_of_bad_clusters])
    tslib.common.save_dataframe_to_file('./data/output/', 'trips_of_clusters_normalzied_by_cluster_size', final_trips)
    

def choose_one_trip_per_cluster(trips_of_clusters, observed, choose_from_majority_mode = True):
    tt = trips_of_clusters.join(observed.start_time, on=['user','trip'], rsuffix='_observed')
    clusters_g = tt.groupby(['user', 'cluster_index', 'D_cluster_index'])

    # Select one trip from each cluster
    how_to_choose = 'random' # ['random', 'latest_trip']
    sel_trips = dict()
    for key, trips in clusters_g:
        if len(trips) > 1:
            if choose_from_majority_mode:
                mode_with_largest_share = trips.mainmode.value_counts().idxmax()
                trips = trips[trips.mainmode == mode_with_largest_share]
                raise Exception('choose_one_trip_per_cluster():: choose_from_majority_mode Not implemented yet')
            if how_to_choose == 'random':
                row = random.randrange(len(trips))
                sel = trips.iloc[row]
                index = sel.name
                if index is None:
                    raise('index was None while selecting one trip per cluster')
            elif how_to_choose == 'latest_trip':
                index = trips.start_time.idxmax() # Select e.g. the latest trip of each cluster
                sel = trips.loc[index]
                #sel = trips[trips.index == index]
                #sel = trips[trips.start_time == trips.start_time.max()]
                #trip_dict = sel.to_dict(orient='index')            
            trip_dict = {index: sel.to_dict()}
        else:
            trip_dict = trips.to_dict(orient='index')
        sel_trips.update(trip_dict)
    dft = pd.DataFrame(data=sel_trips).transpose()
    one_trip_per_cluster = observed.join(dft.set_index(['user', 'trip'])[[]], how='inner')
    
    return one_trip_per_cluster
    

# --------------------------------------------------------------------------------
    
def select_input_trip_data(choice_of_input_data, session_data):
    if choice_of_input_data == 1:
        print("--- choice_of_input_data: All observed trips ---")
        observed_trips = session_data.observed_trips
            
    elif choice_of_input_data == 2:
        observed_trips = filtered_trips_by_clusters_per_person
    
    elif choice_of_input_data == 3:
        # only trips-of-clustered previously computed and filtered by a MAX cluter-size
        trips_of_clusters_normalzied_by_cluster_size = tslib.common.load_dataframe_from_file(
                            './data/output/', 
                            'trips_of_clusters_normalzied_by_cluster_size')
        dft = trips_of_clusters_normalzied_by_cluster_size.set_index(['user', 'trip'])
        
        observed_trips = pd.merge(observed_trips, dft, 
                                   left_index=True, right_index=True,
                                   how='inner') # get only the trips of selected clusters    
        
    elif choice_of_input_data == 4: # Default, preferred especially for some parameter correlation plotting
        print("--- choice_of_input_data: Cut the extra person-days ---")
        # reduce extra person-days, so that:
        #   their recorded days is more evenly distributed compared to original loaded data    
        observed_trips = normalize_by_days_per_person(session_data.observed_trips) 
        
    elif choice_of_input_data == 5: # Return only one trip of each cluster
        print("--- choice_of_input_data: Return only one trip of each cluster ---")            
        observed_trips = choose_one_trip_per_cluster(session_data.trips_of_clusters_without_trip_info,
                                                     session_data.observed_trips)
        
    elif choice_of_input_data == 6:
        print("--- choice_of_input_data: Only 'active' participants with a minimum number of recorded days ---")        
        MIN_PERSONDAYS_FOR_PERSON = 15
        days_per_person = session_data.observed_trips.groupby(['user']).start_date.unique().apply(len).sort_values()
        days_per_person = days_per_person.rename('days')
    
        days_per_person_active = days_per_person[days_per_person >= MIN_PERSONDAYS_FOR_PERSON]
        travelers_active = days_per_person_active.index.values
        observed_trips = session_data.observed_trips[session_data.observed_trips.index.get_level_values(0).isin(travelers_active)]
        
        raise Exception('Being implemented...')
    
    
    # IMPORTANT: Fit other datasets to include only indexes selected above
    if choice_of_input_data != 1:
        computed_trips = session_data.computed_trips.merge(observed_trips[[]], left_index=True, right_index=True)
        substitutes_no_time_limit = session_data.substitutes_no_time_limit.merge(observed_trips[[]], left_index=True, right_index=True)
        deltas = session_data.deltas.merge(observed_trips[[]], left_index=True, right_index=True)
    
        travelers = observed_trips.index.get_level_values(0).unique().values
        traveler_stats = session_data.traveler_stats[session_data.traveler_stats.user.isin(travelers)]    
            
        trips_of_clusters_without_trip_info = session_data.trips_of_clusters_without_trip_info.merge(observed_trips[[]], left_on=['user', 'trip'], right_index=True)
    else:
        computed_trips = session_data.computed_trips
        substitutes_no_time_limit = session_data.substitutes_no_time_limit
        deltas = session_data.deltas
        travelers = session_data.travelers
        trips_of_clusters_without_trip_info = session_data.trips_of_clusters_without_trip_info
        traveler_stats = session_data.traveler_stats
    
    
    return observed_trips, computed_trips, substitutes_no_time_limit, deltas, travelers, traveler_stats, trips_of_clusters_without_trip_info

# --------------------------------------------------------------------------------
    
    
def discard_distance_and_activedistance_outliers(T):
    lower, upper = tslib.stats.get_outliers_range(T.active_distance)
    filtered = tslib.stats.get_non_outliers(T, 'active_distance', lower, upper)     
    
    lower, upper = tslib.stats.get_outliers_range(T.distance)
    filtered = tslib.stats.get_non_outliers(filtered, 'distance', lower, upper)
    
    return filtered

    
def compute_days_per_person(trips):
    days_per_person = trips.groupby(['user']).start_date.unique().apply(len).sort_values()
    days_per_person = days_per_person.rename('days')
    
    return days_per_person
    
# ----------------------------------------------------------------------------------

# create a snapshot of how anticipated travel behavior will be after certain modal shifts -----------
def split(observed, computed, substitutes, from_mode, to_modes, remove_per_trip_alt_duplicates,
          deltaT_threhold=None, deltas=None):
    
    from_to_alt = tslib.modal_shift.get_trips_with_shift(observed, computed, 
                                                         substitutes, 
                                                         from_mode, to_modes)
    from_to_alt = from_to_alt.join(computed[['pt_transfer_count', 'leg_count', 'duration_in_min']])
    
    #dft = substitutes_no_time_limit_.reset_index()
    print("from_to_alt:",from_to_alt.shape)
    
    # For PT alts, choose only one alt per trip:
    # could be also for other alt modes, just in case of bugs and modes not matching plan-ids
    #  dft = from_to_alt.reset_index()
    if remove_per_trip_alt_duplicates:
        from_to_alt_no_duplicates = tslib.modal_shift.get_unique_alt_per_observed_trip(from_to_alt)
        #from_to_alt_no_duplicates = dft.drop_duplicates(subset=['user', 'trip'])
    else:
        from_to_alt_no_duplicates = from_to_alt
    # now we should have only one alt per observed trip
    print("from_to_alt_no_duplicates:",from_to_alt_no_duplicates.shape)
    
    # filter by deltaT threshold if requested
    print('deltaT_threhold=',deltaT_threhold)
    if deltaT_threhold is not None:
        dft = from_to_alt_no_duplicates.join(deltas['deltaT'], how='inner')
        from_to_alt_no_duplicates = tslib.modal_shift.get_alts_passing_deltaT_threshold(dft, deltaT_threhold)
        from_to_alt_no_duplicates.drop(columns='deltaT', inplace=True)                
    print("from_to_alt_no_duplicates, after deltaT threshold:",from_to_alt_no_duplicates.shape)
    
    from_to_alt_details = from_to_alt_no_duplicates[[]].join(computed, how='inner')    
    from_to_alt_details = from_to_alt_details.reset_index().drop(columns='plan_id')
    from_to_alt_details.set_index(keys=['user', 'trip'], inplace=True)
        
    # subtract from all observed trips:    
    # following gives observed trips that do not have the alternatives
    others = observed[~observed.index.isin(from_to_alt_details.index.values)]
    
    return from_to_alt_details, others


def split_old(observed, computed, substitutes, from_mode, to_modes, remove_per_trip_alt_duplicates,
          deltaT_threhold=None, deltas=None):
    
    from_to_alt = tslib.modal_shift.get_trips_with_shift(observed, computed, 
                                                         substitutes, 
                                                         from_mode, to_modes)
    from_to_alt = from_to_alt.join(computed[['pt_transfer_count', 'leg_count', 'duration_in_min']])
    
    #dft = substitutes_no_time_limit_.reset_index()
    print("from_to_alt:",from_to_alt.shape)
    
    # For PT alts, choose only one alt per trip:
    # Also for other alt modes, just in case of bugs and modes not matching plan-ids
    #  dft = from_to_alt.reset_index()
    if remove_per_trip_alt_duplicates:
        from_to_alt_no_duplicates = tslib.modal_shift.get_unique_alt_per_observed_trip(from_to_alt)
        #from_to_alt_no_duplicates = dft.drop_duplicates(subset=['user', 'trip'])
    else:
        from_to_alt_no_duplicates = from_to_alt
    # now we should have only one alt per observed trip
    print("from_to_alt_no_duplicates:",from_to_alt_no_duplicates.shape)
    
    # filter by deltaT threshold if requested
    print('deltaT_threhold=',deltaT_threhold)
    if deltaT_threhold is not None:
        dft = from_to_alt_no_duplicates.merge(deltas['deltaT'], 
                                              left_on=['user', 'trip', 'plan_id'], right_index=True, how='inner')
        from_to_alt_no_duplicates = tslib.modal_shift.get_alts_passing_deltaT_threshold(dft, deltaT_threhold)
        from_to_alt_no_duplicates.drop(columns='deltaT', inplace=True)                
    print("from_to_alt_no_duplicates, after deltaT threshold:",from_to_alt_no_duplicates.shape)
    
    from_to_alt_details = pd.merge(from_to_alt_no_duplicates, computed, 
                                   left_on=['user', 'trip', 'plan_id'], right_index=True, how='inner')
    from_to_alt_details.drop(columns='plan_id', inplace=True)
    from_to_alt_details.set_index(keys=['user', 'trip'], inplace=True)
    
    
    # subtract from all observed trips:
    from_to_alt_trip_indexes = from_to_alt_no_duplicates.set_index(keys=['user', 'trip']).index.values
    others = observed[~observed.index.isin(from_to_alt_trip_indexes)]
    
    return from_to_alt_details, others


def compute_mode_distance_shares_perday_in_temperatures(person_day_info, temperature_ranges):
    ad_2_d_in_range = []
    walk_2_d_in_range = []
    bike_2_d_in_range = []
    car_2_d_in_range = []
    pt_2_d_in_range = []
    totals_in_range = []

    for i in range(len(temperature_ranges)-1):
        bin_start = temperature_ranges[i]
        bin_end = temperature_ranges[i+1]
        person_day_in_range = person_day_info[(person_day_info.average_temperature>=bin_start) & ((person_day_info.average_temperature<bin_end))]
        
        # TODO only for one user
        # person_day_in_range = person_day_in_range[person_day_in_range.index.get_level_values(0)==2]
        
        totals = len(person_day_in_range)
        #totals = person_day_in_range.ad_2_d + person_day_in_range.car_2_d + person_day_in_range.pt_2_d            
        A = person_day_in_range.ad_2_d.sum()
        B = person_day_in_range.car_2_d.sum()
        C = person_day_in_range.pt_2_d.sum()
        
        A_bike = person_day_in_range.bike_2_d.sum()
        A_walk = person_day_in_range.walk_2_d.sum()
        
        totals_in_range.append(totals)
        ad_2_d_in_range.append(A)
        walk_2_d_in_range.append(A_walk)
        bike_2_d_in_range.append(A_bike)
        car_2_d_in_range.append(B)
        pt_2_d_in_range.append(C)
        # np.histogram(person_day_in_range.bike_2_d, 5)
    
    
    shares1 = np.array(walk_2_d_in_range) / np.array(totals_in_range)
    shares2 = np.array(bike_2_d_in_range) / np.array(totals_in_range)
    shares3 = np.array(pt_2_d_in_range) / np.array(totals_in_range)
    shares4 = np.array(car_2_d_in_range) / np.array(totals_in_range)
    
    return shares1, shares2, shares3, shares4, totals_in_range


def compute_mode_distance_shares_perday_in_precipitation(person_day_info, precipitaion_ranges):
    ad_2_d_in_range = []
    walk_2_d_in_range = []
    bike_2_d_in_range = []
    car_2_d_in_range = []
    pt_2_d_in_range = []
    totals_in_range = []

    for i in range(len(precipitaion_ranges)-1):
        bin_start = precipitaion_ranges[i]
        bin_end = precipitaion_ranges[i+1]
        person_day_in_range = person_day_info[(person_day_info.total_precipitation>=bin_start) & ((person_day_info.total_precipitation<bin_end))]
        
        # TODO only for one user
        # person_day_in_range = person_day_in_range[person_day_in_range.index.get_level_values(0)==2]
        
        totals = len(person_day_in_range)
        #totals = person_day_in_range.ad_2_d + person_day_in_range.car_2_d + person_day_in_range.pt_2_d            
        A = person_day_in_range.ad_2_d.sum()
        B = person_day_in_range.car_2_d.sum()
        C = person_day_in_range.pt_2_d.sum()
        
        A_bike = person_day_in_range.bike_2_d.sum()
        A_walk = person_day_in_range.walk_2_d.sum()
        
        totals_in_range.append(totals)
        ad_2_d_in_range.append(A)
        walk_2_d_in_range.append(A_walk)
        bike_2_d_in_range.append(A_bike)
        car_2_d_in_range.append(B)
        pt_2_d_in_range.append(C)
        # np.histogram(person_day_in_range.bike_2_d, 5)
    
    # TODO get the mean (of daily sums) in each range ?!!
    shares1 = np.array(walk_2_d_in_range) / np.array(totals_in_range)
    shares2 = np.array(bike_2_d_in_range) / np.array(totals_in_range)
    shares3 = np.array(pt_2_d_in_range) / np.array(totals_in_range)
    shares4 = np.array(car_2_d_in_range) / np.array(totals_in_range)
    
    return shares1, shares2, shares3, shares4, totals_in_range

# -------------------------------
def retrieve_missing_attribute(to_trips, attribute_name, take_missing_att_from_observed, observed_trips, computed_trips):
    if not np.isin(attribute_name, to_trips.columns):
        if take_missing_att_from_observed:
            to_trips = to_trips.join(observed_trips[attribute_name], how='inner')
        else:
            to_trips = to_trips.join(computed_trips[attribute_name], how='inner')
    return to_trips

# important generic function
def get_attribute_A_vs_B_XY(records_df, A, B, observed_trips, computed_trips, filter_outliers=True, 
                            take_missing_A_from_observed=True,
                            #take_missing_B_from_observed=False,                            
                            ):    
    print('get_attribute_A_vs_B_XY():')
    records_df = retrieve_missing_attribute(records_df, A, take_missing_A_from_observed, observed_trips, computed_trips)
    #records_df = retrieve_missing_attribute(records_df, B, take_missing_B_from_observed)
    
    # first, filter out deltaT outlers:    
    print(records_df.shape)
    if filter_outliers:
        # filter out A outliers (independently):
        lower, upper = tslib.stats.get_outliers_range(records_df[A])
        filtered1 = tslib.stats.get_non_outliers(records_df, A, lower, upper)
        print(filtered1.shape)
                
        # filter out B outliers (independently)
        lower, upper = tslib.stats.get_outliers_range(records_df[B])
        vals = tslib.stats.get_non_outliers(filtered1, B, lower, upper)
        print(vals.shape)
        
        #filtered2 = tslib.stats.get_non_outliers(records_df, B, lower, upper)
        #print(filtered2.shape)
        
        # Both:
        #vals = filtered1.merge(filtered2)
        #print(vals.shape)
    else:
        vals = records_df
    
    x = vals[A].values
    y = vals[B].values
    
    return x, y

# important generic function
def group_trips_by_attribute_range(to_trips, attrbute_name, att_val_ranges, observed, computed):
    #filtered = filter_outliers_by_deltaT_and_deltaE(to_trips)
    #a = make_observed_and_computed_from_substitutes(filtered, observed, computed) 
    a = tslib.mining.retrieve_missing_attribute(to_trips, attrbute_name, True, observed, computed)
    # named 'a' just for simple readability
    trip_groups = []
    for i in range(len(att_val_ranges)-1):
        lower = att_val_ranges[i]
        upper = att_val_ranges[i+1]
        d = a[ (a[attrbute_name] >= lower) & (a[attrbute_name] < upper)]
        trip_groups.append(d)
    return trip_groups

def group_trips_by_attribute_threshold(to_trips, att_threholds, observed, computed):
    filtered = filter_outliers_by_deltaT_and_deltaE(to_trips)
    a = tslib.mining.make_observed_and_computed_from_substitutes(filtered, observed, computed) 
    # named 'a' just for simple readability
    trip_groups = []
    for th in att_threholds:
        d = a[a[attrbute_name] <= th]
        trip_groups.append(d)
    return trip_groups



#def get_potentials_per_user(df):
#    # 'BUS', 'SUBWAY', 'BICYCLE', 'TRAM', 'FERRY', 'RAIL'
#    # 'WALK', 
#    # 'CAR'
##    alts = df[df.altmode!='CAR']
##    noalts = df[df.altmode=='CAR']
##    pts =  df[df.altmode.isin(['BUS', 'SUBWAY', 'BICYCLE', 'TRAM', 'FERRY', 'RAIL'])]
#        
#    all_trips = df.groupby(by=df.user)['user'].count()
#    
#    dfg = df.groupby(df.user)
#    
#    alts = dfg.apply(lambda x: x[x['altmode'] != 'CAR']['user'].count()) # x is each group? e.g. here, one group per each user
#    alt_ratios = 100 * alts.values/all_trips.values
#    df_alt_ratios = pd.DataFrame({'user':alts.index, 'ratio':alt_ratios })
#    
#    transfers = dfg.apply(lambda x: x[x['transferable'] == 't']['user'].count())
#    transfers_ratios = 100 * transfers.values/all_trips.values
#    df_transfer_ratios = pd.DataFrame({'user':transfers.index, 'ratio':transfers_ratios })
#
#    car_trips = dfg.apply(lambda x: x[x['mode'] == 'CAR']['user'].count())
#    transfers_by_car_ratios = np.where(car_trips.values>0, 100 * transfers.values/car_trips.values, 0)
#    df_transfer_by_car_ratios = pd.DataFrame({'user':transfers.index, 'ratio':transfers_by_car_ratios })
#    
#
#    #!traveler_all.index.isin(traveler_alts.index)
#    #np.where(traveler_all.index.isin(traveler_alt.index), traveler_alt.)
#    
#    return df_alt_ratios, df_transfer_ratios, df_transfer_by_car_ratios
#    