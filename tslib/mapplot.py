#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 17:33:49 2019

@author: mehrdad
"""

import numpy as np
import pandas as pd
#from mpl_toolkits.axes_grid1 import make_axes_locatable
#from mpl_toolkits.basemap import Basemap
import folium # Map plot library that uses OSM
from folium import plugins
import polyline
import branca.colormap
import tslib.gis


def put_marks_on_map(my_map, points, color='blue', percent_of_points=100):    
    for each in points:  
        #folium.Marker(each).add_to(my_map)
        folium.Marker(each, 
                          icon=folium.Icon(icon='arrow-down', # arrow-right, arrow-down, info-sign
                                           icon_size = (10,10), 
                                           icon_color=color,
                                           icon_anchor=(0,0),
                                           ), 
                          #size=(2,2),
                          ).add_to(my_map)

def plot_leg_route(my_map, leg, color='blue', percent_of_points=100):            
    put_marks_on_map(my_map, leg.route, color, percent_of_points)


def plot_routes(legs, filename="routes.html", percent_of_points=100):    
    lon_avg = np.average(legs.origin.apply(lambda x: x[1]))
    lat_avg = np.average(legs.origin.apply(lambda x: x[0]))
    #ave_lat = sum(p[0] for p in points)/len(points)
    #ave_lon = sum(p[1] for p in points)/len(points)
    my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=14)
    
    routes = legs.path.apply(polyline.decode)
    
    for route in routes:
        points = route
        put_marks_on_map(my_map, points, percent_of_points)
           
    my_map.save("./"+filename)

def plot_point_clusters(points, filename="ODs_clusters.html"):
    lats = points.apply(lambda x: x[0])
    lons = points.apply(lambda x: x[1])    
    
    lon_avg = np.average(lons)
    lat_avg = np.average(lats) + 0.03
    #map_tiles='OpenStreetMap'
    map_tiles='Stamen Terrain'
    #map_tiles='cartodbpositron'
    my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=12, tiles=map_tiles)
    #folium.LayerControl().add_to(my_map)
    
    # Build list of (lat, lon) values, ex: [('a', 'b'), ('a1', 'b1')]
    locations = list(zip(lats.values, lons.values))
    
    # Create a folium marker cluster
    custom_options = {'maxClusterRadius':80*2, 'chunkedLoading':1, 'spiderfyDistanceMultiplier':1}
    #custom_options = {'maxClusterRadius':int(80*1.5)}
    custom_options = {'maxClusterRadius':int(80*1)}
    marker_cluster = plugins.MarkerCluster(locations=locations, options=custom_options)
    # Add marker cluster to map
    marker_cluster.add_to(my_map)
        
    my_map.save(filename)
    
    return my_map, marker_cluster


def plot_OD_Lines(legs, filename="ODs_lines.html", line_color="blue", line_weight=0.5, line_opacity=0.5):
    lon_avg = np.average(legs.origin.apply(lambda x: x[1])) - 0.05
    lat_avg = np.average(legs.origin.apply(lambda x: x[0])) + 0.03
    #map_tiles='OpenStreetMap'
    map_tiles='Stamen Terrain'
    #map_tiles='cartodbpositron'
    my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=12, tiles=map_tiles)
    #folium.LayerControl().add_to(my_map)
    
    
    for index, leg in legs.iterrows():
#       points = legs.origin.values
#       folium.Marker(points).add_to(my_map)
#       common_trafficsense.put_marks_on_map(my_map, points)
#    
#       points = legs.destination.values
#       folium.Marker(points).add_to(my_map)
#       common_trafficsense.put_marks_on_map(my_map, points)
    
        p1 = [leg.origin[0], leg.origin[1]]
        p2 = [leg.destination[0], leg.destination[1]]
        #print ([p1, p2])
        folium.PolyLine(locations=[p1, p2], color=line_color, weight=line_weight, opacity=line_opacity).add_to(my_map)

    # colorbar
    colormap = branca.colormap.LinearColormap(caption='Repetition of unique trips', 
                                              colors=[(200, 200, 255),(0, 0, 255)], 
                                              index=[1,260], vmin=1, vmax=260)
    colormap.add_to(my_map) #add color bar at the top of the map
        
    my_map.save(filename)



def plot_heatmap(points, filename='ODs_heatmap.html', weight_vals=pd.Series(), custom_gradient=None):
    # Note: weight_vals defaul is [], meaning no specific weights # TODO: study more
    print("number of points:", len(points))
    
    lats = points.apply(lambda x: x[0])
    lons = points.apply(lambda x: x[1])
    
    lon_avg = np.average(lons)
    lat_avg = np.average(lats) + 0.03
    
    #map_tiles='OpenStreetMap'
    map_tiles='Stamen Terrain'
    #map_tiles='cartodbpositron'
    my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=12, tiles=map_tiles)
    
    
    if weight_vals.empty:
        points = list(zip(lats.values, lons.values))            
    else:
        points = list(zip(lats.values, lons.values, weight_vals))            
    #points = list(zip(legs.olat.values, legs.olon.values, 10*np.ones_like(legs.olat)))
    #max_amount = float(legs['duration_minutes'].max()) # ???

    #example gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'},
    
    hm_wide = plugins.HeatMap(data=points, 
                       min_opacity=1, 
                       radius=5, 
                       #blur=12, 
                       gradient=custom_gradient,
                       #max_zoom=1, 
                       #control=True,
                       #overlay=True,
                     )
    hm_wide.add_to(my_map)
    
    # layers *
    #folium.LayerControl().add_to(my_map)
    
    # #add color bar at the top of the map
    add_colormap_scale(my_map, 5, 50, caption='ODs per km^2')

    my_map.save(filename)
    
def add_colormap_scale(my_map, scale_left, scale_right, caption):
    # colorbar
    colormap = branca.colormap.LinearColormap(caption=caption, colors=[(0, 0, 200),(255, 0, 0)], 
                                              index=[scale_left,scale_right], 
                                              vmin=scale_left, vmax=scale_right)
    colormap.add_to(my_map) #add color bar at the top of the map
    
    
def add_scale_bar(my_map, scale_left_point, scale_right_point, font_size=11):
    # scale_left_point and scale_right_point should be manually tweaked so that p1-->p2 gives, for example, 5 km or 10 km distance as desired!
    # For example, following values give a 5 km distance-scale for Helsinki region map:
    #   [60.307873, 25.008584] #lat,lon
    #   [60.307873, 25.099400] #lat,lon 
    # Another example
    #   scale_left_point = [60.329000, 25.008584] #lat,lon
    #   scale_right_point = [60.329000, 25.099400] #lat,lon     
    p1 = scale_left_point
    p2 = scale_right_point    
    d = np.round(tslib.gis.get_point_distance(p1, p2)/1000,2)
    # print("Distance between the scale-bar's *given* left and right points:", d, "km")
    
    # draw the scale-bar:
    folium.PolyLine(locations=[p1, p2], color='black', weight=2, opacity=1, 
                    #tooltip=folium.Tooltip(str(d)+' km') # To also add a hover-over tooltop to the line
                    ).add_to(my_map)

    # scale's cross at left:
    cross_p1 = [p1[0]+0.002, p1[1]]; cross_p2 = [p1[0]-0.002, p1[1]]
    folium.PolyLine(locations=[cross_p1, cross_p2], color='black', weight=2, opacity=1).add_to(my_map)
    # scale's cross at right:
    cross_p1 = [p2[0]+0.002, p2[1]]; cross_p2 = [p2[0]-0.002, p2[1]]
    folium.PolyLine(locations=[cross_p1, cross_p2], color='black', weight=2, opacity=1).add_to(my_map)    
    # scale's cross(es) at middle:
    lon_middle = p1[1]+(p2[1]-p1[1])/2
    cross_p1 = [p1[0]+0.001, lon_middle]; cross_p2 = [p1[0]-0.001, lon_middle]
    folium.PolyLine(locations=[cross_p1, cross_p2], color='black', weight=2, opacity=1).add_to(my_map)    

    # scale numbers from 0 to d, at each cross point
    folium.map.Marker([p2[0], p2[1]], icon=folium.DivIcon(icon_size=(5,-10), icon_anchor=(0,0),
            html='<div style="width:50px; font-size:'+str(font_size)+'pt; font-weight:bold">'+ str(int(d))+ '</div>',
            )).add_to(my_map)
    folium.map.Marker([cross_p1[0], cross_p1[1]], icon=folium.DivIcon(icon_size=(5,-10), icon_anchor=(0,0),
            html='<div style="width:50px; font-size:'+str(font_size)+'pt; font-weight:bold">'+ str(np.round(d/2,1))+ '</div>',
            )).add_to(my_map)
    folium.map.Marker([p1[0], p1[1]], icon=folium.DivIcon(icon_size=(5,-10), icon_anchor=(0,0),
            html='<div style="width:50px; font-size:'+str(font_size)+'pt; font-weight:bold">'+ '0'+ '</div>',
            )).add_to(my_map)
    # write 'km'
    folium.map.Marker([p2[0], p2[1]], icon=folium.DivIcon(icon_size=(-10,+25), icon_anchor=(0,0),
            html='<div style="width:50px; font-size:'+str(font_size)+'pt; font-weight:bold">'+ 'km' +'</div>',
            )).add_to(my_map)

def add_icon(my_map, file_path, location_on_map, size=(20,30), location_padding=(0,0)):
    folium.map.Marker([location_on_map[0], location_on_map[1]], 
                      icon=folium.CustomIcon(icon_image=file_path, icon_size=size, icon_anchor=location_padding)
                     ).add_to(my_map)

# Layered from different datasets ----------------------------------------
def start_map_from_legs(legs, left_pad=-0.05, bottom_pad=0.03, zoom=12, prevent_zoom=False):
    print("start_map_from_legs(): Got",len(legs),"OD pairs")
    if len(legs) > 0:        
        lon_avg = np.average(legs.origin.apply(lambda x: x[1])) + left_pad
        lat_avg = np.average(legs.origin.apply(lambda x: x[0])) + bottom_pad       
        #map_tiles='OpenStreetMap'
        map_tiles='Stamen Terrain'
        #map_tiles='cartodbpositron'
        
        min_zoom=0
        max_zoom=18
        if prevent_zoom:
            min_zoom=zoom
            max_zoom=zoom
            
        my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=zoom, tiles=map_tiles,
                            control_scale=True, zoom_control=False, 
                            #max_bounds=True, no_wrap=True,
                            min_zoom=min_zoom, max_zoom=max_zoom,
                            #width='60%', height='60%'
                            )
        return my_map
    else:
        return None
    
def start_map_from_points(points, left_pad=0, bottom_pad=0.03, zoom=12):
    lats = points.apply(lambda x: x[0])
    lons = points.apply(lambda x: x[1])    
    lon_avg = np.average(lons) + left_pad
    lat_avg = np.average(lats) + bottom_pad
    #map_tiles='OpenStreetMap'
    map_tiles='Stamen Terrain'
    #map_tiles='cartodbpositron'
    my_map = folium.Map(location=[lat_avg, lon_avg], zoom_start=zoom, tiles=map_tiles,
                        control_scale=True, zoom_control=False)
    return my_map

def end_map(my_map, filename):
    folium.LayerControl().add_to(my_map) # layers *
    my_map.save(filename)

#-----------------------
    
def add_heatmap_layer(my_map, points, layer_name="heatmap", weight_vals=pd.Series(), custom_gradient=None):
    # Note: weight_vals defaul is [], meaning no specific weights # TODO: study more
    print("number of points:", len(points))    
    lats = points.apply(lambda x: x[0])
    lons = points.apply(lambda x: x[1])    
    
    if weight_vals.empty:
        points = list(zip(lats.values, lons.values))            
    else:
        points = list(zip(lats.values, lons.values, weight_vals))    
    plugins.HeatMap(data=points, 
                       min_opacity=1, 
                       radius=5, 
                       #blur=12, 
                       gradient=custom_gradient,
                       #max_zoom=1, 
                       #control=True,
                       #overlay=True,
                       name=layer_name,
                     ).add_to(my_map)


def add_OD_Lines(my_map, legs, line_color="blue", line_weight=0.5, line_opacity=0.5):  
    print("number of legs (or trips):", len(legs))
    for index, leg in legs.iterrows():
        p1 = [leg.origin[0], leg.origin[1]]
        p2 = [leg.destination[0], leg.destination[1]]
        #print ([p1, p2])
        folium.PolyLine(locations=[p1, p2], color=line_color, weight=line_weight, opacity=line_opacity).add_to(my_map)

def add_OD_Line(my_map, leg, line_color="blue", line_weight=0.5, line_opacity=0.5, 
                tooltip_text="", mark_destination=True):    
    p1 = [leg.origin[0], leg.origin[1]]
    p2 = [leg.destination[0], leg.destination[1]]
    #print ([p1, p2])
    folium.PolyLine(locations=[p1, p2], color=line_color, weight=line_weight, opacity=line_opacity, 
                    smooth_factor=1,
                    stroke=True,
                    line_join="miter",
                    fill=False,
                    fill_opacity = 1,
                    tooltip=folium.Tooltip(tooltip_text)).add_to(my_map)
    
    # Mark the destinations with an icon
    if mark_destination:
        folium.map.Marker([p2[0], p2[1]],                          
                          tooltip=folium.Tooltip("destination")
                            ).add_to(my_map)
        if False:
            # references for icon names:
            # https://ionicons.com/
            # 
            folium.map.Marker([p2[0], p2[1]], 
                              icon=folium.Icon(icon='arrow-down', # arrow-right, arrow-down, info-sign
                                               icon_size = (10,10), 
                                               icon_color='blue',
                                               icon_anchor=(0,0),
                                               ), 
                              #size=(2,2),
                              ).add_to(my_map)

# TODO: remove and replace with add_heatmap_layer()
def plot_heatmap_layer(my_map, points, layer_name, custom_blur, custom_gradient):
    # Note: weight_vals defaul is [], meaning no specific weights # TODO: study more
    print("number of points:", len(points))
    lats = points.apply(lambda x: x[0])
    lons = points.apply(lambda x: x[1])
    weights = list(zip(lats.values, lons.values))            

    hm_wide = plugins.HeatMap(weights, name=layer_name, 
                       min_opacity=0.8, radius=5, blur=custom_blur, 
                       #gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'},
                       gradient=custom_gradient,
                       max_zoom=1, 
                       control=True,
                       overlay=True,
                     )
    hm_wide.add_to(my_map)
    
    return my_map