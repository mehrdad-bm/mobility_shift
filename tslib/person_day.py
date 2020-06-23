#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 13:42:12 2020

@author: mehrdad
"""

import pandas as pd
import tslib.mining


class PersonDays():
    def __init__(self, trips, compute_personday_values=False):
        self.trips = trips
        
        # init our person-day dataframe:        
        g = self.trips.reset_index().groupby(by=['user', 'start_date'])
        self.person_days = g[[]].count()
        
        if compute_personday_values:
            self.compute_person_day_values()

    def compute_person_day_values(self):
        self.compute_TTperPD()
        self.compute_emission_perPD()
        self.compute_distances()
        self.compute_day_mainmodes()

    def compute_day_mainmodes(self):
        trips = self.trips.reset_index()
        g = trips.groupby(by=['user', 'start_date'])        
        mode_sums = g.mainmode.sum()        
        car_trips_perday = mode_sums.apply(lambda x: x.count('CAR'))        
        #car_is_nth_trip_of_day = mode_sums.apply(lambda x: x.find('CAR'))
        
        self.person_days = self.person_days.join(car_trips_perday.to_frame('car_trips_perday'))        
        
        
    def compute_distances(self, remove_distance_outliers = True):
        # compute person-day distanes and ratios:
        if remove_distance_outliers:
            T = tslib.mining.discard_distance_and_activedistance_outliers(self.trips).reset_index()
        else:
            T = self.trips.reset_index()
        g = T.groupby(by=['user', 'start_date'])
        #trips_per_person_day = (g.start_date.count()).to_frame('trips_per_day')
        self.person_days['total_distance_per_person_day'] = g.distance.sum()    
        self.person_days['active_distance_per_person_day'] = g.active_distance.sum()
        self.person_days['bike_distance_per_person_day'] = g.bike_distance.sum()
        self.person_days['walk_distance_per_person_day'] = g.walk_distance.sum()
        self.person_days['car_distance_per_person_day'] = g.car_distance.sum()
        self.person_days['pt_distance_per_person_day'] = g.pt_distance.sum()
        # and distance ratios per-day        
        self.person_days['ad_2_d'] = self.person_days['active_distance_per_person_day']/self.person_days['total_distance_per_person_day']
        self.person_days['car_2_d'] = self.person_days['car_distance_per_person_day']/self.person_days['total_distance_per_person_day']
        self.person_days['pt_2_d'] = self.person_days['pt_distance_per_person_day']/self.person_days['total_distance_per_person_day']    
        self.person_days['bike_2_d'] = self.person_days['bike_distance_per_person_day']/self.person_days['total_distance_per_person_day']
        self.person_days['walk_2_d'] = self.person_days['walk_distance_per_person_day']/self.person_days['total_distance_per_person_day']
    
    # compute travel-time-sum for each person-day
    def compute_TTperPD(self):
        # get the daily, per-user values (makes more sense):
        trips = self.trips.reset_index()
        g = trips.groupby(by=['user', 'start_date'])
    
        # Study further the travel time budget:
        # TTPD: travel time per day
        trips_per_person_day = (g.start_date.count()).to_frame('trips_per_day')    
        tt_per_person_day = (g.duration_in_min.sum()).to_frame('day_duration_sum')
        tt_per_person_day = tt_per_person_day.join(trips_per_person_day.trips_per_day, how='inner')    
        
        #self.tt_per_person_day = tt_per_person_day
        self.person_days = self.person_days.join(tt_per_person_day)

    # compute travel-time-sum for each person-day
    def compute_emission_perPD(self):
        # get the daily, per-user values (makes more sense):
        trips = self.trips.reset_index()
        g = trips.groupby(by=['user', 'start_date'])        
        emission_per_person_day = (g.emission.sum()).to_frame('day_emission_sum')        
        self.person_days = self.person_days.join(emission_per_person_day)        
    
#    def get_personday_dataset(self):
#        # build a table for person-days
#        person_day_info = pd.DataFrame(data={'ad_2_d': self.AD_to_D_ratios, 
#                                             'car_2_d':self.car_to_D_ratios,
#                                             'pt_2_d':self.pt_to_D_ratios,
#                                             'bike_2_d':self.bike_to_D_ratios,
#                                             'walk_2_d':self.walk_to_D_ratios})
#    
#        return person_day_info

        
    def join_with_daily_weather(self, daily_weather_history):
        self.person_days = self.person_days.join(daily_weather_history[['average_temperature', 'total_precipitation', 'year', 'month']], 
                                                 on='start_date', how='left')
    
    def discard_days_with_missing_fields(self):
        a = self.person_days[~ self.person_days.average_temperature.isna()]
        b = a[~ a.ad_2_d.isna()]
        return b
        
#    def discard_days_with_no_weather_info(self):
#        return self.person_days[~ self.person_days.average_temperature.isna()]
#
#    def discard_days_with_no_distance_ratio_info(self):
#        return self.person_days[~ self.person_days.ad_2_d.isna()]
#    