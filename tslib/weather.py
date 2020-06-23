#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 18:12:46 2020

@author: mehrdad
"""

import pandas as pd

def compute_daily_weather(weather_data):
#    weather_data['year'] = weather_data.weather_date.apply(lambda x: x.year)
#    weather_data['month'] = weather_data.weather_date.apply(lambda x: x.month)
#    weather_data['day'] = weather_data.weather_date.apply(lambda x: x.day)

    # compute daily stats from weather history    
    daily_date = weather_data.groupby('weather_date')['weather_date'].min()
    daily_year = (daily_date.apply(lambda x: x.year)).rename('year')
    daily_month = (daily_date.apply(lambda x: x.month)).rename('month')
    daily_day = (daily_date.apply(lambda x: x.day)).rename('day')
    daily_average_temperatures = weather_data.groupby('weather_date')['temperature'].mean()
    daily_precipitation = (weather_data.groupby('weather_date')['precipitation_1h'].sum()).rename('precipitation')
    daily_hours_recorded = (weather_data.groupby('weather_date')['weather_date'].count()).rename('hours_recorded')
    
    dft = pd.DataFrame(data={#'weather_date': daily_date, 
                       'year': daily_year, 
                       'month': daily_month, 
                       'day': daily_day, 
                       'average_temperature': daily_average_temperatures, 
                       'total_precipitation': daily_precipitation, 
                       'hours_recorded': daily_hours_recorded, 
                       })    
    return dft


def are_days_suitable_for_bike(daily_weather_, min_C, max_C, max_precipitation):
    day_is_suitable_for_bike = \
        (daily_weather_.average_temperature >= min_C) & (daily_weather_.average_temperature <= max_C) &\
        (daily_weather_.total_precipitation <= max_precipitation)
    
    return day_is_suitable_for_bike.to_frame('day_suitable_for_bike')

