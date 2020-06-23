#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 17:33:49 2019

@author: mehrdad
"""

import matplotlib.pyplot as plt
import matplotlib.colors
from matplotlib.ticker import PercentFormatter
import numpy as np


SAVE_FIGURES_INTO_FILE = True
SAVE_EPS_FIGURES_ALSO_AS_PNG = True
GRID_COLOR = "#aaaaaa"

# --------------------------------------
def init_plot_settings(width=6, height=6):
    plt.rcParams["figure.figsize"] = (width, height)

def customize_plot(font_size):
    plt.xticks(fontsize=font_size, fontweight='bold')
    plt.yticks(fontsize=font_size, fontweight='bold')
    plt.xlabel('', fontsize=font_size, fontweight='bold')
    plt.ylabel('', fontsize=font_size, fontweight='bold')    

# functions with better names:
def set_plot_size(width=6, height=6):
    init_plot_settings(width, height)
def set_plot_fonts(font_size):
    customize_plot(font_size)

def set_plot_style(labels_font_size = 10, tightlayout=True): # Set font and style, used by defualt for all figures
    plt.rcParams["figure.autolayout"] = tightlayout # set tight layout as default    
    plt.rcParams['font.size'] = labels_font_size
    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelsize'] = labels_font_size
    plt.rcParams['axes.labelweight'] = 'bold'
    
# --------------------------------------
def save_figure(plt, filename, transparent=False, dpi=150):
    if SAVE_FIGURES_INTO_FILE:
        file_format = filename.rpartition(".")[2]
        print("Saving figure as", file_format, "file format")
        
        if file_format=='png':
            plt.savefig(filename, bbox_inches="tight", transparent=transparent,
                        dpi=dpi,)
            
        elif file_format=='eps':
            plt.savefig(filename, bbox_inches="tight", transparent=True,
                        dpi=dpi,
                        metadata={'Creator':'Mehrdad Bagheri, Finland'},)
            
            if SAVE_EPS_FIGURES_ALSO_AS_PNG:
                plt.savefig(filename+".png", bbox_inches="tight", transparent=False,
                            dpi=300)
    else:
        print("WARNING! NOT SAVING FIGURES because option 'SAVE_FIGURES_INTO_FILE=False")
        
# --------------------------------------   
# --------------------------------------

def plot_cdf_smooth(vals, edges, x_label, y_label, smoothing_degree = 3, linewidth=2, label=None, color='black'):
    x = edges[1:]
    y = vals
    coefs = np.polyfit(x, y, smoothing_degree)
    y_poly = np.polyval(coefs, x)
    
    plt.plot(x, y_poly, color=color, linewidth=linewidth, label=label)
        
    plt.yticks(ticks=np.array(range(0,101,25))/100)

    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    add_grid(plt, axis='both')
    
    
def plot_cdf(vals, edges, x_label, y_label, font_size=10, linewidth=2, label=None, color='black', linestyle=None):
    customize_plot(font_size)
    
    x = edges[1:]
    y = vals
    plt.plot(x, y, linewidth=linewidth, color=color, label=label, linestyle=linestyle)
    
    plt.yticks(ticks=np.array(range(0,101,25))/100)
    
    plt.xlabel(x_label, fontsize=font_size, fontweight='bold')
    plt.ylabel(y_label, fontsize=font_size, fontweight='bold')    
    add_grid(plt, axis='both')
#    plt.yticks(ticks=np.arange(0, 1.1, .1))

def plot_pdf(pdf_vals, edges, x_label, y_label, font_size):
    customize_plot(font_size)
    plt.plot(edges[1:], pdf_vals, linewidth=4, color='black')
    plt.xlabel(x_label, fontsize=font_size, fontweight='bold')
    plt.ylabel(y_label, fontsize=font_size, fontweight='bold')    
    add_grid(plt, axis='both')
#    plt.yticks(ticks=np.arange(0, 1.1, .1))
    plt.yticks(ticks=np.arange(0, 1.25, .25))

# --------------------------------------
def plot_hist(vals, bins=None, weights=None, show_as_fractions=False, label=None, 
              color='black', edgecolor='gray', edge_linewidth=1, bar_width=1, opacity=1,
              show_custom_ticks=False):
    NEW_TEST_HIST_CODE = False
    if show_as_fractions:
        weights = get_hist_ratio_weights(vals)
        
    (n, bins, patches) = plt.hist(vals, bins=bins, weights=weights,
                                 color=color, rwidth=bar_width, alpha=opacity,
                                 edgecolor=edgecolor, linewidth=edge_linewidth, #1.25,
                                 label=label)
    if show_as_fractions:
        plt.ylim(0,1.)
        
    if show_custom_ticks:
        plt.xticks(bins.round(0))    
        
    elif NEW_TEST_HIST_CODE:
        plt.ylim(0, len(vals)+int(0.1*len(vals)))
        plt.axhline(len(vals), label='total', linestyle="--", linewidth=1)
    return (n, bins, patches)
    
def plot_hist_bar(vals, edges, x_label, y_label, font_size):
    customize_plot(font_size)
    plt.bar(x=edges[1:], height=vals, linewidth=4, color='black')
    plt.xlabel(x_label, fontsize=font_size, fontweight='bold')
    plt.ylabel(y_label, fontsize=font_size, fontweight='bold')    
    add_grid(plt)
#    plt.yticks(ticks=np.arange(0, 1.1, .1))
    #plt.yticks(ticks=np.arange(0, 1.25, .25)) #for PDF
    plt.yticks(ticks=np.arange(0, 125, 25))

def plot_bar_for_range_vals(vals, edges, x_label, y_label, y_lim = 0, 
                            custom_align='center', custom_color='black', custom_bar_width=1.6,
                            label='',
                            xlabel_rotation='vertical', decimal=None, delim =' to ', opacity=1):
    plt.bar(x=edges[1:], height=vals, label=label, width=custom_bar_width, linewidth=0.5, color=custom_color, 
            align=custom_align, edgecolor='black', alpha=opacity)
    plt.xticks(ticks=edges[1:], labels=bins_to_pairticks(edges, decimal, delim), rotation=xlabel_rotation)
    #plt.xticks(ticks=edges[0:len(hour_bins)-1], labels=tslib.plot.bins_to_pairticks(edges),rotation='vertical')    
    add_grid(plt, axis='y')
    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    if y_lim > 0:
        plt.ylim(0, y_lim)
    #plt.show()

#-----------------------------------------------
#-----------------------------------------------
def plot_3d_scatter(x,y,z, color_bar_label='', datapoint_size=2, datapoint_label='data point', 
                    colorbar_ticks=None,font_size=12, colormap_colors=None,
                    x_ticks=None): 
#    colors = get_color_by_range(z, maxval=np.max(z), divs=5)
#    markers = get_markers_by_range(z, maxval=np.max(z), divs=5)
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    if colormap_colors is None:
        cmap=None
    else:
        cmap = matplotlib.colors.ListedColormap(colormap_colors)
                                                 
#    cmap = matplotlib.colors.ListedColormap(['#dd9999', '#888888', 'blue', 'green'])
                                                 
    #cmap.set_over('0.25')
    #cmap.set_under('0.75')
    
    #cmap=plt.cm.get_cmap('Blues', 4)

    scatter = ax.scatter(x, y, z, 
                         c=z,           # c=colors
                         cmap=cmap,
                         marker='o',
                         s=datapoint_size, 
                         depthshade=True, zdir='z',
                         label=datapoint_label)
    
    cb = plt.colorbar(scatter, 
                 #ticks=np.arange(int(np.min(z)), int(np.max(z))+1, 5), 
                 ticks=colorbar_ticks,
                 fraction=0.025, 
                 pad=0.05,
                 #label=color_bar_label
                 )
    cb.ax.tick_params(
            #labelsize=font_size
            )
    cb.set_label(label=color_bar_label, 
                 #fontdict={'fontsize':font_size, 'fontweight':'bold'}
                 )
    
    #ax.set_zlim(np.min(z), np.max(z))
    
#    if False:
#    # produce a legend with the unique colors from the scatter
#        legend1 = ax.legend(*scatter.legend_elements(),
#                            loc="lower left", title="Classes")
#        ax.add_artist(legend1)
    return ax, fig

# --------------------------------------
# --------------------------------------
def start_stacked_bar_for_range_vals():
    pass

def plot_one_bar_stack_for_range_vals(vals, edges, custom_align='center', custom_color='black', bar_width=1.6, 
                                      previous_vals=None, label=None):
    plt.bar(#x=edges[1:], 
            x=range(len(edges)-1),
            height=vals, width=bar_width, linewidth=0.5, 
            color=custom_color, align=custom_align, edgecolor='black',
            bottom=previous_vals,
            label=label)

def end_stacked_bar_for_range_vals(edges, x_label, y_label, y_lim = 0):
    plt.xticks(#ticks=edges[1:], 
            ticks=range(len(edges)-1),
            labels=bins_to_pairticks(edges), rotation='vertical')
    #plt.xticks(ticks=edges[0:len(hour_bins)-1], labels=tslib.plot.bins_to_pairticks(edges),rotation='vertical')    
    add_grid(plt, axis='y')
    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    if y_lim > 0:
        plt.ylim(0, y_lim)

def start_multiple_lines():
    plt.figure()
    
def add_line(x, y, label='', color=None, marker=None, linewidth=None, linestyle=None):
    plt.plot(x, y, color=color, label=label,
             marker=marker, linewidth=linewidth,
             linestyle=linestyle)        
    
def end_multiple_lines(x, x_label='', y_label='', convert_y_axis_to_percentage=False, legend_location='best', legend_font_size=9, vertical_x_ticks=False):
    if vertical_x_ticks:
        rotation = 90
    else:
        rotation = 0
    plt.xticks(x, rotation=rotation)
    if convert_y_axis_to_percentage:
        yticks_to_percentage_easy(plt)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    add_legend(plt, legend_font_size, marker_size_scale=1, location=legend_location)
    add_grid(plt)
    plt.show()

# ---------------------

def set_boxplot_style(bplot, color, box_border_width):
    for patch in bplot['boxes']:
        patch.set_facecolor(color)
    for w in bplot['whiskers']:
        w.set_linewidth(box_border_width)
        w.set_color(color)
    for w in bplot['caps']:
        w.set_linewidth(box_border_width)
        w.set_color(color)
    for w in bplot['medians']:
        w.set_linewidth(box_border_width)

def add_boxplot_legend(boxplots, legend_labels, fontsize=10, location='best'):
    legend_artists = []
    for bplot in boxplots:
        legend_artists.append(bplot['boxes'][0])
    plt.legend(legend_artists, legend_labels,
               prop={'size':fontsize, 'weight':'bold'}, loc=location, framealpha=0.5)    

class BoxPlotMixed():
    def __init__(self, legend_fontsize=10, legend_location='best'):
        self.bplots = []
        self.legend_labels = []
        self.legend_fontsize = legend_fontsize
        self.legend_location = legend_location
        pass
    
    def add_box(self, one_list, color, label='', box_positions_shift=0, bar_width=0.2, 
                           show_confidence_interval=False, show_outliers=False, outlier_marker='.'):    
        positions = np.array(range(len(one_list))) + box_positions_shift        
        
        bplot = plt.boxplot(one_list, manage_xticks = False, patch_artist=True,
                            showfliers=show_outliers, positions=positions, widths=bar_width, 
                            notch=show_confidence_interval, sym=outlier_marker, #bootstrap=1000
                            )
        self.legend_labels.append(label)
        
        set_boxplot_style(bplot, color, box_border_width=2)
        print("boxplot; positions of boxes:", positions)
        self.bplots.append(bplot)
        return bplot
             
    def end(self, x_label='', y_label='', x_tick_labels=None, show_legend=True):
        plt.xlabel(x_label)
        plt.ylabel(y_label)    
        if x_tick_labels is not None:
            x_ticks = np.array(range(len(x_tick_labels)))
            plt.xticks(x_ticks, x_tick_labels)
        if show_legend:
            add_boxplot_legend(self.bplots, self.legend_labels, fontsize=self.legend_fontsize, location=self.legend_location)
        plt.show()
        


def plot_one_box_mixed_old(x_ticks, one_list, color, shift, bar_width=0.4, 
                       show_confidence_interval=False, show_outliers=False, outlier_marker='.'):
    positions = 1 + np.array(range(len(one_list))) + shift * bar_width
    cwidths = []
    for i in range(len(one_list)):
        cwidths.append(bar_width - 0.05)
    
    bplot = plt.boxplot(one_list, showfliers=show_outliers, patch_artist=True, sym=outlier_marker,
                        positions=positions, widths=cwidths,
                        notch=show_confidence_interval, 
                        labels=x_ticks,                        
                        #bootstrap=1000
                        )
    
    set_boxplot_style(bplot, color, box_border_width=2)

    print("boxplot; positions of boxes:", positions)
    print("boxplot; cwidths:", cwidths)
    
    return bplot

def end_multiple_box_old(x_label='', y_label='', legend_labels=None, legend_colors=None, x_tick_labels=None, legend_left_shift=0):
    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    if x_tick_labels is not None:
        x_ticks = np.array(range(len(x_tick_labels)))
        plt.xticks(x_ticks, x_tick_labels)    
    plt.show()    
    if legend_labels is not None:
        x_left = plt.xlim()[0] + legend_left_shift
        y_top = plt.ylim()[1]
        xstep = (plt.xlim()[1] - plt.xlim()[0])/100
        ystep = (plt.ylim()[1] - plt.ylim()[0])/100
        i = 0
        for label in legend_labels:
            plt.text(x_left+1*xstep, y_top - 6*ystep - i*11, label, backgroundcolor=legend_colors[i], color='white')                
            i+= 1
            
#        plt.text(0.8, 155.0, 'to PT', backgroundcolor='blue', color='white', weight='bold', size='small')    
#        plt.text(0.8, 140.0, 'to bike', backgroundcolor='green', color='white', weight='bold', size='small')    

            
#    
# --------------------------------------
# --------------------------------------
def start_lineplot_for_range_vals():
    plt.figure()

def plot_one_line_for_range_vals(vals, edges, custom_color='black',
                                 label='', marker=None, linewidth=None, linestyle=None):
    plt.plot(edges[1:], vals, color=custom_color,
             label=label,
             marker=marker, linewidth=linewidth,
             linestyle=linestyle)

def end_lineplot_for_range_vals(edges, x_label, y_label, y_lim = 0, x_ticks_demical=None, delim=' to '):
    plt.xticks(ticks=edges[1:], labels=bins_to_pairticks(edges, decimal=x_ticks_demical, delim=delim), rotation='vertical')
    #plt.xticks(ticks=edges[0:len(hour_bins)-1], labels=tslib.plot.bins_to_pairticks(edges),rotation='vertical')    
    add_grid(plt)
    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    if y_lim > 0:
        plt.ylim(0-1, y_lim)
    plt.show()



# --------------
def add_grid(plt, axis='both', color=GRID_COLOR, grid_behind_plots=True):
    plt.grid(axis=axis, linestyle=":", color=color)
    if grid_behind_plots:
        ax = plt.gca()
        ax.set_axisbelow(b=True)

def add_legend(plt, fontsize=10, location='best', marker_size_scale=10):
    plt.legend(prop={'size':fontsize, 'weight':'bold'}, loc=location, framealpha=0.5, markerscale=marker_size_scale)

def add_title(plt, title, fontsize=12):
    plt.title(title, fontdict={'fontsize':fontsize, 'fontweight':'bold'})

def add_h_zero_line():
    plt.axhline(0, linestyle="-", linewidth=2, color='black', alpha=0.8)
def add_v_zero_line():
    plt.axvline(0, linestyle="-", linewidth=2, color='black', alpha=0.8)

def add_y_equal_x_line(plt, x_vals, line_label=None, color='grey'):
    # draw 'f(x) = x' straight line:
    xlims=plt.xlim()
    ylims=plt.ylim()
    #print(xlims)
    #print(ylims)
    
    plt.plot([0,np.max(x_vals)], [0,np.max(x_vals)], 
              label=line_label, color=color, linestyle='--', linewidth=1)

    # reset the plot limits to the original:
    plt.xlim(xlims[0],xlims[1])
    plt.ylim(ylims[0],ylims[1])
    

def add_mean_hline(vals, title_addition='', show_mean_val=True):
    mean_val = np.mean(vals)
    label = 'mean '+title_addition
    if show_mean_val:
        label += '= '+str(np.round(mean_val, 2))
    plt.axhline(mean_val, label=label, linestyle="--", linewidth=1)
def add_mean_vline(vals, title_addition='', show_mean_val=True, round_digits=2):
    mean_val = np.mean(vals)
    label = 'mean '+title_addition
    if show_mean_val:
        label += '= '+str(np.round(mean_val, round_digits))
    plt.axvline(mean_val, label=label, linestyle="--", linewidth=1)

def add_std_hline(vals):
    mean_val = np.mean(vals)
    std_val = np.std(vals)
    plt.axhline(mean_val+std_val, label='mean+std', linestyle=":", linewidth=1)
    
# ------------------

def plot_bar_for_hist_vals(vals, edges, x_label, y_label, custom_color="black", font_size=12, x_tick_step=1):
    customize_plot(font_size)    
    plt.bar(x=edges[:-1], height=vals, color=custom_color, 
            width=1, 
            linewidth=0.5, 
            edgecolor='black'
            )
    plt.xticks(ticks=list(np.arange(min(edges),max(edges), x_tick_step)))
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #plt.grid(axis='y', linestyle=":", color=GRID_COLOR)
    add_grid(plt, axis='y')
    
def plot_bar_for_hist_vals_2(vals, edges, x_label, y_label, custom_color="black", font_size=12, x_tick_step=1):
    customize_plot(font_size)    
    plt.bar(x=edges[:-1], height=vals, color=custom_color, 
            #width=1, 
            linewidth=0.5, 
            edgecolor='black',
            #align='edge'
            )
    #plt.xticks(ticks=list(np.arange(min(edges),max(edges), x_tick_step)))
    plt.xlabel(x_label)
    plt.ylabel(y_label)    
    add_grid(plt, axis='y')

# --------------------------------------------------------------------
def plot_surface(X, Y, Z, title):
    ax = plt.axes(projection='3d')
    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap='viridis', edgecolor='none')    
    plt.title(title)
    font_size = 12
    plt.xlabel('x',fontsize=font_size, fontweight='bold')
    plt.ylabel('y',fontsize=font_size, fontweight='bold')
    plt.show()

def plot_mesh_color(X, Y, Z, title):
    plt.pcolormesh(X,Y,Z)
    plt.colorbar()
    plt.title(title)

    font_size = 12
    plt.xlabel('x',fontsize=font_size, fontweight='bold')
    plt.ylabel('y',fontsize=font_size, fontweight='bold')
    
    plt.show()
    
def plot_3d_hist(x, y, x_title, y_title, title=""):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    hist, xedges, yedges = np.histogram2d(x, y, bins=[10, 10], 
                                          #range=[[0, 4], [0, 4]]
                                          )
    
    # Construct arrays for the anchor positions of the 16 bars.
    xpos, ypos = np.meshgrid(xedges[:-1] + 0.25, yedges[:-1] + 0.25, indexing="ij")
    xpos = xpos.ravel()
    ypos = ypos.ravel()
    zpos = 0
    
    # Construct arrays with the dimensions for the 16 bars.
    dx = dy = 0.5 * np.ones_like(zpos)
    dz = hist.ravel()
    
    ax.bar3d(xpos, ypos, zpos, dx, dy, dz, zsort='average')
    
    plt.xlabel(x_title)
    plt.ylabel(y_title)
    #plt.zlabel("trips")
    plt.title(title)
    
    plt.show()

    
# Specific plots -----------------------------------------
def plot_scatter_of_deltaE_deltaActiveD(T, title, x_lim=0, y_lim=0, dot_color='black', dot_size=5):
    customize_plot(12)
    plt.scatter(T.emission_reduced/1000, T.active_distance_increased/1000, 
                #label=title,
                color=dot_color, marker='.', s=dot_size)
    plt.xlabel("Emission reduced (CO2 kg)")
    plt.ylabel("Active distance increased (km)")
    #plt.legend(['y = active distance increased'])
    plt.title(title, fontsize=14)
    
    if x_lim > 0:
        plt.xlim(0, x_lim)
        bx=0
    else:
        a,bx = plt.xlim()
        plt.xlim(0, bx)

    if y_lim > 0:
        plt.ylim(0, y_lim)
        by=0
    else:
        a,by = plt.ylim()
        plt.ylim(0, by)
    
    add_grid(plt)    
    
    return bx, by

def plot_scatter_of_deltaE_deltaActiveD_nolim(T, title, dot_color='black', dot_size=0.5):
    customize_plot(12)
    plt.scatter(T.emission_reduced/1000, T.active_distance_increased/1000, color=dot_color, marker='.', s=dot_size)
    plt.xlabel("emission reduced (CO2 kg)")
    plt.ylabel("active distance increased (km)")
    #plt.legend(['y = active distance increased'])
    plt.title(title)
    
    add_grid(plt)
    
def add_mark_on_scatter(x, y, label=None, marker='o', size=50):
    plt.scatter(x, y, s=size, marker=marker, color='black', label=label)
    
# converting and customization ------------------------------------------------------
def thousand_seperate_tick_labels(plot_ticks, pop_extra=True):
    current_ticks = list(plot_ticks[0])
    if pop_extra:
        current_ticks.pop()
    new_tick_labels = list(map(lambda x: format(int(x), ','), current_ticks))
    return new_tick_labels

def xticks_to_percentage_easy(plt, decimals=0):
    plt.gca().xaxis.set_major_formatter(PercentFormatter(1, decimals=decimals))

def yticks_to_percentage_easy(plt, decimals=0):
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1, decimals=decimals))

def ticks_to_percentage(ticks, pop_extra=True, values_are_float = False):
    l = list(ticks[0])
    if pop_extra:
        l.pop(0)
        l.pop()
    if values_are_float:
        f = lambda x: str(round(x,2))+"%"
    else:
        f = lambda x: str(int(round(x,2)))+"%"
    new_tick_labels = list(map(f, l))
    return l, new_tick_labels

def round_or_int(rval, decimal=None):    
    if decimal is not None:
        val = np.round(rval, decimal)
        if decimal==0:
            val = int(val)
        print(val)
        return val
    else:
        return rval
        
    
    
def bins_to_pairticks(bins, decimal=None, delim =' to '):
    bins_ticks=[]
    for i in range(1, len(bins)):
        a = round_or_int(bins[i-1], decimal)
        b = round_or_int(bins[i], decimal)                
        bins_ticks.append(str(a)+ delim +str(b))

    return bins_ticks

def get_hist_ratio_weights(vals):
    return np.ones(len(vals))/len(vals)
