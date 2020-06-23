#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  3 13:28:57 2019

@author: mehrdad
"""


def convert_mode_to_tsmode(mode):
    modemap = dict(train='RAIL', metro='SUBWAY')    
    if mode in modemap:
        return modemap[mode]
    else:
        return str.upper(mode)
    