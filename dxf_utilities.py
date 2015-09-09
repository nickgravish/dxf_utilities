# -*- coding: utf-8 -*-
"""
Scripts for staging layered dxf files for laser micro-machining

Created on Wed Sep  9 00:45:53 2015

@author: nickgravish
"""

#%%

import ezdxf
import re
import numpy as np


#%% 

def get_dxf_layer_names(dwg):
    """
    Take in a drawing handle from ezdxf, outputs list of layer names
    """    
    
    layer_names = []
    
    for layer in dwg.layers:
        name = layer.get_dxf_attrib('name')
        layer_names.append(name)
        print(name)
    
    return layer_names

#%%
def parse_layer_names(layer_names):
    """
    test function to parse layer names. Currently unused
    """
    parsenumbers = re.compile(r'\\d+')
    
    for kk, layer_name in enumerate(layer_names):
        print(kk)

#%%
def compute_bounding_box(dwg, layer):
    """
    Compute the bounding box of the current layer, computed from the lines
    that form the layer boundary
    """
    
    modelspace = dwg.modelspace()
    points = [];
    
    for e in modelspace:
        if(layer == e.get_dxf_attrib('layer') and  \
            'LINE' == e.dxftype()):
            
            points.append(e.dxf.start)
            points.append(e.dxf.end)

    min_bounding_box = np.array([])
    max_bounding_box = np.array([])
    center_point = np.array([])
    
    # skip if no lines to copy
    if(len(points) != 0):        
        # ccompute the bounding box and then the center point
        min_bounding_box =  np.array(min(points))
        max_bounding_box =  np.array(max(points))
        
        center_point = (min_bounding_box + max_bounding_box)/2
    
    return center_point, min_bounding_box, max_bounding_box
    
#%% 
def copy_all_entities_from_layer(dwg, new_dwg, layer, center_point = (0,0,0)):
    """
    Copy entities from one layer to another, with an offset to re-center the points
    in the new layer
    """    

    # skip if no lines to copy
    center_point = np.array(center_point)
    # next copy all layer entities to new file, subtract
    modelspace = dwg.modelspace()
    new_modelspace = new_dwg.modelspace()
    
    for e in modelspace:
        if(layer == e.get_dxf_attrib('layer')):
            
            if(e.dxftype() == 'LINE'):
                # center line in new coord
                start = np.array(e.dxf.start) - center_point
                end = np.array(e.dxf.end) - center_point
                
                # create line
                new_modelspace.add_line(tuple(start), tuple(end)) 
            elif(e.dxftype() == 'CIRCLE'):
                # center line in new coord
                center = np.array(e.dxf.center) - center_point
                radius = e.dxf.radius
                
                # create line
                new_modelspace.add_circle(center, radius) 
            elif(e.dxftype() == 'ARC'):
                # center line in new coord
                center = np.array(e.dxf.center) - center_point
                radius = e.dxf.radius
                start_ang = e.dxf.start_angle
                end_ang = e.dxf.end_angle
                
                # create line
                new_modelspace.add_arc(center, radius, start_ang, end_ang)
            elif(e.dxftype() == 'POLYLINE'):
                # center line in new coord
                points = [tuple(np.array(point) - center_point) for point in e.points()]                    
                
                # create line
                new_modelspace.add_polyline3d(points)    

    return new_dwg
    
#%%
def rip_layers_to_new_file(dwg):

    """
    Rips out individual layers from a layered dxf file and creates separate files.
    Sometimes useful for varying power, speed of cuts layer by layer
    
    Makes assumption that geometry is bounded by a rectangle
    """
    layer_names = get_dxf_layer_names(dwg)
        
    for layer in layer_names:
        
        # first create a new file for the layer
        new_dwg = ezdxf.new()
    
        try:
            new_dwg.layers.remove('0')
            new_dwg.layers.remove('VIEW_PORT')
            new_dwg.layers.remove('DEFPOINTS')
        except:
            pass
    
        new_dwg.layers.create(layer)
        new_modelspace = new_dwg.modelspace()        
        
        # print out all types of dxf entities
        l=[]
        modelspace = dwg.modelspace()
        for e in modelspace:
            l.append(e.dxftype())        
        print(set(l))
        
        # consolidate a list of all line entities in the layer
        center_point, min_bounding_box, max_bounding_box = compute_bounding_box(dwg, layer)
        
        # skip if no lines to copy
        if(len(center_point) != 0):        
            print('Center point: %s' % center_point)        
            
            # next copy all layer entities to new file, subtract
            for e in modelspace:
                if(layer == e.get_dxf_attrib('layer')):
                    
                    if(e.dxftype() == 'LINE'):
                        # center line in new coord
                        start = np.array(e.dxf.start) - center_point
                        end = np.array(e.dxf.end) - center_point
                        
                        # create line
                        new_modelspace.add_line(tuple(start), tuple(end)) 
                    elif(e.dxftype() == 'CIRCLE'):
                        # center line in new coord
                        center = np.array(e.dxf.center) - center_point
                        radius = e.dxf.radius
                        
                        # create line
                        new_modelspace.add_circle(center, radius) 
                    elif(e.dxftype() == 'ARC'):
                        # center line in new coord
                        center = np.array(e.dxf.center) - center_point
                        radius = e.dxf.radius
                        start_ang = e.dxf.start_angle
                        end_ang = e.dxf.end_angle
                        
                        # create line
                        new_modelspace.add_arc(center, radius, start_ang, end_ang)
                    elif(e.dxftype() == 'POLYLINE'):
                        # center line in new coord
                        points = [tuple(np.array(point) - center_point) for point in e.points()]                    
                        
                        # create line
                        new_modelspace.add_polyline3d(points)
                        
                    
            # close new dwg file and move on to next layer
            new_dwg.saveas(layer + '.dxf')                    
#        new_dwg.close()
            
#%% 

def tile_dxf(dwg):
    """
    Take in a dxf drawing handle. Tile each layer that is the same material.
    Naming convention of layers is NUMBER_MATERIAL
    so 1_KA  --> layer 1, kapton. 
       6_ADH --> laye 6, adhesive.
       
    Script tiles according to an assumed geometry of 25x25 mm tile spacing, and
    over a footprint of 3 x n wide tiling.

    """    
    
    tile_space = (25, 25) # mm
    marker_circle_size = .4 # mm
    marker_circle_location = np.array([-11.5, -11.5, 0])    
    
    
    layer_names = get_dxf_layer_names(dwg)
    
    # get layer number and types
    layer_num_and_type = [layer_name.split('_') for layer_name in layer_names]            

    # create list of unique layer types    
    layer_types = [layer_type[1] if len(layer_type) > 1 else 'NULL' for layer_type in layer_num_and_type]
    unique_layers = list(set(layer_types))

    number_unique = [layer_types.count(unq) for unq in unique_layers]
    
    layer_number = [int(string[0]) if(len(string) > 1) else -1 for string in layer_num_and_type]
    
    for tile_layer_type in unique_layers:
        if(tile_layer_type != 'NULL'):        
            # first create a new file for the layer
            new_dwg = ezdxf.new()
        
            try:
                new_dwg.layers.remove('0')
                new_dwg.layers.remove('VIEW_PORT')
                new_dwg.layers.remove('DEFPOINTS')
            except:
                pass
        
            new_dwg.layers.create(tile_layer_type)
            new_modelspace = new_dwg.modelspace()        
            
            print('Current tile layer is %s' % tile_layer_type)
            layer_count = 0
            for kk, current_layer_type in enumerate(layer_types):
                print('Current layer is %s' % current_layer_type)
                # if current layer is same type is tiling layer
                
                if(tile_layer_type == current_layer_type):   
                    print('and there was a match')
                    center_point, min_bounding_box, max_bounding_box = compute_bounding_box(dwg, layer_names[kk])
                    
                    new_origin = np.array([np.mod(layer_count,3)*tile_space[0], np.floor(layer_count/3)*tile_space[1], 0])
                    print(new_origin)
                    print(center_point)
                    
                    
                    copy_all_entities_from_layer(dwg, new_dwg, layer_names[kk], center_point - new_origin)
                    
                    # add circles to the layer                    
                    for numlayers in range(layer_number[kk]):
                        circle_origin = marker_circle_location + np.array([numlayers*marker_circle_size*2*1.7, 0, 0])
                        print(circle_origin)
                        new_modelspace.add_circle(circle_origin + new_origin, marker_circle_size)
                    
                    layer_count = layer_count + 1
            new_dwg.saveas(tile_layer_type + '.dxf')
            
        
        
        
        
        
        
        
        
        
        
        
        
    