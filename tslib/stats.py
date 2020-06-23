#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 19:24:59 2019

@author: mehrdad
"""
from scipy import stats
import numpy as np

# ----- Stats and Analysis ------------------------- #
def get_pdf_and_cdf(vals, bins):
    counts, edges = np.histogram(vals, bins)
    total = np.sum(counts)
    pdf = counts/total # probabilities in each bin
    cdf = np.cumsum(pdf)
    ccdf = 1 - cdf
    return pdf, cdf, ccdf, edges
    
def get_outliers_range(vals):
    iqr = stats.iqr(vals)
    q3, q1 = np.percentile(vals, [75, 25])
    lower_whisker = np.max([q1 - iqr*1.5, np.min(vals)])
    upper_whisker = np.min([q3 + iqr*1.5, np.max(vals)])
    #print ("Middle box (Q1 to Q3):", q1, " to ", q3)
    #print ("IQR:",iqr, " | lower_whisker: ",lower_whisker, "| upper_whisker: ",upper_whisker)
    return lower_whisker, upper_whisker
    
def get_outliers(df, vals, lower, upper):
    outliers_df = df[(vals < lower) | (vals > upper)]
    return outliers_df

def get_non_outliers(df, column_name, lower, upper):
    filtered_df = df[(df[column_name] >= lower) & (df[column_name] <= upper)]
    return filtered_df

def get_cdf_point_value(cdf, edges, target_proability):
    vals = edges[1:]
    filtered_vals = vals[cdf >= target_proability]
    point = filtered_vals[0]
    return point

def get_cumulative_shares(sample_values, smaller_shares_first=False):
    # Result of this function can be used to plot, for example:
    #   plt.plot(sample_shares, sample_value_shares)
    #   plt.hist(sample_value_shares)
    
    shares = 100 * sample_values/np.sum(sample_values) # shares of each sample's value from the total value sum
    shares = shares.sort_values(ascending = smaller_shares_first)

    value_share_list =[] # list of cumulative values
    sample_share_list = []
    i = 0
    c = 0
    total_samples = len(shares)
#    point_found = False    
    for share in shares:     
        c += share
        i += 1
        value_share_list.append(c)
        sample_share_list.append(100 * i/total_samples)
#        if not point_found and c>=50:
#            point = B.iloc[i]
#            point_found = True
    
    #TODO: use range functions_
#    step = 100/len(shares)
#    sample_share_list = list(np.arange(step,100+step,step))
    
    return sample_share_list, value_share_list


def get_cumulative_shares_of_samples(vals, smaller_shares_first=False):
    # Result of this function can be used to plot, for example:
    #   plt.plot(sample_shares, sample_value_shares)
    #   plt.hist(sample_value_shares)
    
    # cumulative share of each sample out of total sample count
    step = 1/len(vals)
    sample_shares = np.arange(step,1+step,step)
    
    # share of each sample out of total sample count
    shares = vals/vals.sum()
    shares = -np.sort(-shares)
    sample_value_shares = np.cumsum(shares)

    return sample_shares, sample_value_shares