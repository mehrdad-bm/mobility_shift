#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 11:44:50 2020

@author: mehrdad
@email: bagheri_mehrdad@hotmail.com
"""
# Custom plot functions

import matplotlib.pyplot as plt
import tslib.plot
import tslib.stats
import numpy as np
from numpy.polynomial.polynomial import polyfit


def plot_hist(vals, bins=None, x_label='', y_label='', color=None, show_mean_line=False, 
              show_N_title=False, show_default_ticks=False, label=None, show_as_fractions=False
              #show_decmial_bins=False, bin_demicals=1
              ):
    plt.figure()    
    (n, bins, patches) = tslib.plot.plot_hist(vals, bins=bins, color=color, label=label, show_as_fractions=show_as_fractions)
    if not show_default_ticks:
        plt.xticks(bins.round(0))    
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    if show_mean_line:
        tslib.plot.add_mean_vline(vals, show_mean_val=False, round_digits=0)
    if show_N_title:
        plt.title('(N='+ str(len(vals)) +')')
    plt.show()

def plot_shares(x, y, x_label='', y_label=''):
    plt.figure()
    plt.plot(np.array(x)/100, np.array(y)/100)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    tslib.plot.xticks_to_percentage_easy(plt)
    tslib.plot.yticks_to_percentage_easy(plt)
    tslib.plot.add_grid(plt)
    plt.show()

def plot_line(x, y, x_label='', y_label='', marker='o', linestyle='-', color=None):
    plt.figure()
    if x is None:
        plt.plot(y, marker=marker, linestyle=linestyle, color=color)
    else:
        plt.plot(x, y, marker=marker, linestyle=linestyle, color=color)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    tslib.plot.add_grid(plt)
    plt.show()

def plot_bar_for_hist_vals(bins, vals, x_label='', y_label='', xlabel_rotation='vertical', decimal=None, delim =' to '):
    plt.figure()
    x = list(range(1, len(vals)+1, 1))    
    plt.bar(x=x, height=vals, width=0.9, linewidth=0.5, edgecolor='black')
    plt.xticks(ticks=x, 
               labels=tslib.plot.bins_to_pairticks(bins, decimal, delim), 
               rotation=xlabel_rotation)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.show()
    
def plot_hist_as_bar(edges, vals, x_label='', y_label='', width=0.8, color=None, align='center', create_and_show_figure=True):
    if create_and_show_figure:
        plt.figure()
    plt.bar(x=edges[:-1], height=vals, 
            color=color, 
            width=width, 
            linewidth=0.5, 
            edgecolor='black',
            align=align #'edge'
            )
    plt.xlabel(x_label)
    plt.ylabel(y_label)        
    if create_and_show_figure:
        plt.show()

def plot_multiple_lines(x, y_list, colors, line_labels, x_label='', y_label='', make_y_axis_percentage=False,
                        marker=None, linewidth=None):
    plt.figure()
    i = 0
    for y in y_list:
        if len(line_labels) > 0:
            plt.plot(x, y, color=colors[i], label=line_labels[i],
                     marker=marker, linewidth=linewidth)
        else:
            plt.plot(x, y, color=colors[i], 
                     marker=marker, linewidth=linewidth)            
        i += 1
    plt.xticks(x)
    if make_y_axis_percentage:
        tslib.plot.yticks_to_percentage_easy(plt)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    tslib.plot.add_legend(plt, 9, marker_size_scale=1)
    tslib.plot.add_grid(plt)
    plt.show()
    
def add_multiple_limit_markers(x, y_list, colors, line_labels=[]):    
    i = 0
    for y in y_list:
        plt.plot(x, y, color=colors[i], marker='_', markersize=10, linewidth='0.001')
        i += 1    


# ------------------------------------------------------------------------------------------
def plot_deltaX_deltaY_scatter(x, y, 
                               from_mode_str, target_mode_str, 
                               x_label, y_label,
                               datapoint_color=None, 
                               datapoint_size=0.15, 
                               polyfit_degree=2,                           
                               prev_plot_y_lims=np.nan,
                               draw_fitted_functin=False, plot_2dhist=False, 
                               show_mean_lines=False, show_mean_spot=False,
                               show_title_with_N=False,
                               figure_name=None):    
    # fit a line:
    coeffs = polyfit(x, y, deg=polyfit_degree) # Least-squares fit of a polynomial to data.
    f_x = np.poly1d(coeffs)    # f_x = b + m * x
    #
    
    title_str = 'Shift from '+from_mode_str+' to '+target_mode_str+'  (N='+str(len(x))+')'
    label_str = from_mode_str+' to '+target_mode_str
    
    plt.figure(figure_name)
    
    #tslib.plot.customize_plot(14)
    plt.scatter(x, y, s=datapoint_size, label=label_str, color=datapoint_color)
#    plt.xlabel("deltaE (CO2 kg)")
#    plt.ylabel("deltaT (minutes)")
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #tslib.plot.add_grid(plt)
    tslib.plot.add_h_zero_line()
    tslib.plot.add_v_zero_line()
#    tslib.plot.add_mean_hline(y, 'of deltaT', show_mean_val=False)
#    tslib.plot.add_mean_vline(x, 'of deltaE', show_mean_val=False)
    if show_mean_lines:
        tslib.plot.add_mean_vline(x, 'of x', show_mean_val=False)
        tslib.plot.add_mean_hline(y, 'of y', show_mean_val=False)
        
    if show_mean_spot:
        tslib.plot.add_mark_on_scatter(x.mean(), y.mean(), label='mean of x and y', marker='x', size=5)
    
    # plot the fitted function line
    if draw_fitted_functin:
        prev_x_lims = plt.xlim()
        prev_y_lims = plt.ylim()
        plt.plot(np.unique(x), f_x(np.unique(x)), '-', color='red', label='fitted function', linewidth=1)
        plt.ylim(prev_y_lims)
    if not np.isnan(prev_plot_y_lims):
        print("changing ylim")
        plt.ylim(prev_plot_y_lims)
    tslib.plot.add_legend(plt, marker_size_scale=10, location='upper right')
    #plt.title(title_str, fontdict={'fontsize':14, 'fontweight':'bold'})
    if show_title_with_N:
        plt.title(title_str)
    plt.show()
    
    if plot_2dhist:
        plt.figure()
        tslib.plot.init_plot_settings(width=4, height=3.5) # * set figure dimensions        
        tslib.plot.customize_plot(11)
        plt.hist2d(x,y, 10)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        tslib.plot.add_grid(plt)
        tslib.plot.add_h_zero_line()
        tslib.plot.add_v_zero_line()
        plt.title(title_str, fontdict={'fontsize':14, 'fontweight':'bold'})
        plt.show()
    
    return f_x


# ----------------------------------------------------------
def compute_and_plot_cdf(vals, label, x_label='', y_label='', color=None, bins=100, linewidth=1, font_size=10):
    pdf, cdf, ccdf, edges = tslib.stats.get_pdf_and_cdf(vals, bins)
    tslib.plot.plot_cdf(cdf, edges, x_label, y_label, label=label, color=color, linewidth=linewidth, font_size=font_size)

def compute_and_plot_ccdf(vals, label, x_label='', y_label='', color=None, bins=100, linewidth=1, font_size=10):
    pdf, cdf, ccdf, edges = tslib.stats.get_pdf_and_cdf(vals, bins)
    tslib.plot.plot_cdf(1-cdf, edges, x_label, y_label, label=label, color=color,  linewidth=linewidth, font_size=font_size)

def compute_and_plot_cumulative_shares_of_samples(vals, sample_name='samples', data_point_name='data points'):
    x, y = tslib.stats.get_cumulative_shares_of_samples(vals)
    plot_shares(100*x, 100*y, 'Percentage of '+sample_name, 'Share of all '+data_point_name)

# --------------------------------------
    
def plot_mode_distance_shares_perday_in_temperatures(temperature_ranges, shares1, shares2, shares3, shares4, totals_in_temp_range, bar_width=0.7):
    plt.figure()
    tslib.plot.start_stacked_bar_for_range_vals()
    tslib.plot.plot_one_bar_stack_for_range_vals(shares1, temperature_ranges, custom_color='green', label='walk', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares2, temperature_ranges, custom_color='#00df00', previous_vals=shares1, label='bike', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares3, temperature_ranges, custom_color='blue', previous_vals=shares1+shares2, label='pt', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares4, temperature_ranges, custom_color='#bc0000', previous_vals=shares1+shares2+shares3, label='car', bar_width=bar_width)
    tslib.plot.end_stacked_bar_for_range_vals(temperature_ranges, 'Average day temperature (C)', 'Share of daily travel-distance')
    #plt.title("(N="+str(np.sum(totals_in_temp_range))+" person-days)")
    tslib.plot.add_legend(plt)
    tslib.plot.yticks_to_percentage_easy(plt)
    plt.show()    
    
def plot_mode_distance_shares_perday_in_precipitation(precip_ranges, shares1, shares2, shares3, shares4, totals_in_range, bar_width=0.8, first_range_is_no_rain=False):
    plt.figure()
    tslib.plot.start_stacked_bar_for_range_vals()
    tslib.plot.plot_one_bar_stack_for_range_vals(shares1, precip_ranges, custom_color='green', label='walk', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares2, precip_ranges, custom_color='#00df00', previous_vals=shares1, label='bike', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares3, precip_ranges, custom_color='blue', previous_vals=shares1+shares2, label='pt', bar_width=bar_width)
    tslib.plot.plot_one_bar_stack_for_range_vals(shares4, precip_ranges, custom_color='#bc0000', previous_vals=shares1+shares2+shares3, label='car', bar_width=bar_width)
    tslib.plot.end_stacked_bar_for_range_vals(precip_ranges, 'Precipitation per day (mm)', 'Share of daily travel-distance')
    #plt.title("(N="+str(np.sum(totals_in_range))+" person-days)")
    tslib.plot.add_legend(plt)
    if first_range_is_no_rain:
        ticks, tickstrs = plt.xticks()
        tickstrs[0]= 'no rain'
        tickstrs[1]= '. to '+str(precip_ranges[2])
        plt.xticks(ticks, tickstrs)
    tslib.plot.yticks_to_percentage_easy(plt)        
    plt.show()

def compute_and_plot_daily_modeshares_by_temperature(person_days, temperature_ranges):            
    shares1, shares2, shares3, shares4, totals_in_temp_range = tslib.mining.compute_mode_distance_shares_perday_in_temperatures(
                                                                    person_days, temperature_ranges)                    
    plot_mode_distance_shares_perday_in_temperatures(temperature_ranges, 
                                                                  shares1, shares2, shares3, shares4, 
                                                                  totals_in_temp_range,
                                                                  bar_width=1)    

def compute_and_plot_modeshares_by_precipitation(person_days, precip_ranges):
    shares1, shares2, shares3, shares4, totals_in_range = tslib.mining.compute_mode_distance_shares_perday_in_precipitation(
                                                                    person_days, precip_ranges)        
    plot_mode_distance_shares_perday_in_precipitation(precip_ranges, 
                                                                   shares1, shares2, shares3, shares4, 
                                                                   totals_in_range,
                                                                   bar_width=1, 
                                                                   first_range_is_no_rain=True)
    