#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 16:38:57 2019

@author: mehrdad
"""

# class Singleton()

class LegacyDataHolder():
    def __init__(self, trips_all_details, trips_and_alts, transferables):
        self.trips_all_details = trips_all_details
        self.trips_and_alts = trips_and_alts
        self.transferables = transferables
        self.travelers = None
        
    def update_data(self, travelers):
        self.travelers = travelers        
        

class ModalShiftData():
    def __init__(self):
        pass

                                                            
class DataHolder():
    def __init__(self):
        # Settings for loading, computation and analysis in this session:
        self.settings = None # SettingsHolder()
        
        # legacy_data
        self.legacy_data = None # LegacyDataHolder()
        
        #
        self.travelers = None
        self.trips_of_clusters_without_trip_info = None
        self.observed_trips_with_noise = None
    

    def update_denoised_trip_data(self, correct_trips, 
                             observed_trips, circle_trips, round_trips, 
                             incorrect_trips):
        self.correct_trips = correct_trips   
        self.observed_trips = observed_trips        
        self.circle_trips = circle_trips
        self.round_trips = round_trips
        self.incorrect_trips = incorrect_trips


    def update_db_loaded_data(self, observed_trips, 
                                    traveler_stats,
                                    computed_trips, 
                                    weather_history):
        self.observed_trips = observed_trips  
        self.traveler_stats = traveler_stats
        self.computed_trips = computed_trips
        self.weather_history = weather_history
    
    
    def update_file_loaded_data(self, observed_trips, 
                                    traveler_stats,
                                    computed_trips, 
                                    weather_history, daily_weather_history):
        self.observed_trips = observed_trips        
        self.traveler_stats = traveler_stats
        self.computed_trips = computed_trips
        self.weather_history = weather_history
        self.daily_weather_history = daily_weather_history
    
    
    def update_modal_shift_data(self, observed_vs_computed_deltas, 
                                    time_relevant_substitutes, 
                                    substitutes_no_time_limit,
                                    day_suitable_for_bike):
        self.deltas = observed_vs_computed_deltas
        self.time_relevant_substitutes = time_relevant_substitutes
        self.substitutes_no_time_limit = substitutes_no_time_limit        
        self.day_suitable_for_bike = day_suitable_for_bike        


    def report_session_data(self):
        if self.observed_trips_with_noise is not None:            
            print("observed_trips_with_noise", self.observed_trips_with_noise.shape)        
        if self.observed_trips is not None:
            print("observed_trips", self.observed_trips.shape)
        if self.computed_trips is not None:            
            print("computed_trips", self.computed_trips.shape)
        if self.traveler_stats is not None:            
            print("traveler_stats", self.traveler_stats.shape)
        if self.weather_history is not None:            
            print("weather_history", self.weather_history.shape)
        if self.daily_weather_history is not None:            
            print("daily_weather_history", self.daily_weather_history.shape)
        if self.travelers is not None:            
            print("travelers", self.travelers.shape)
        if self.trips_of_clusters_without_trip_info is not None:            
            print("trips_of_clusters_without_trip_info", self.trips_of_clusters_without_trip_info.shape)
        if self.deltas is not None:            
            print("deltas", self.deltas.shape)
        if self.time_relevant_substitutes is not None:            
            print("time_relevant_substitutes", self.time_relevant_substitutes.shape)
        if self.substitutes_no_time_limit is not None:            
            print("substitutes_no_time_limit", self.substitutes_no_time_limit.shape)
        if self.day_suitable_for_bike is not None:            
            print("day_suitable_for_bike", self.day_suitable_for_bike.shape)

    
            
