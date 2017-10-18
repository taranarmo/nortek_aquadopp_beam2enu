#!/bin/python

import numpy as np
import pandas as pd
import sys

def parse_aquadopp_hdr(filename,read_transformation_matrix=False):  
    with open(filename+'.hdr','r',encoding='windows-1251') as f:
        if read_transformation_matrix:
            T = []
        beam_cells = []
        vert_cells = []
        read_cells = False
        lines = f.readlines()
        for i,line in enumerate(lines):
            if read_cells and line is '\n':
                read_cells = False
                continue
            elif line.startswith('-----'):
                continue
            elif line is '\n':
                continue
            elif line.startswith('Coordinate system'):
                beam2enu = True if line.split()[-1] == 'BEAM' else False
            elif line.startswith('Orientation'):
                if line.split()[-1] == 'DOWNLOOKING':
                    downlooking = True
                else:
                    downlooking = False
                continue
            elif line.startswith('Transformation matrix'):
                if read_transformation_matrix:
                    T = lines[i:i+3]
                continue
            elif line.startswith('       Beam    Vertical\n'):
                read_cells = True
                continue
            if read_cells:
                cell = line.split()
                beam_cells.append(float(cell[1]))
                vert_cells.append(float(cell[2]))
    return_list = [beam_cells, vert_cells, downlooking]
    if read_transformation_matrix:
        return_list.append(T)
    return_list.append(beam2enu)
    return return_list

def parse_T(T):
    if isinstance(T,list):
        T = [s.strip('Transformation matrix').strip() for s in T]
    else:
        T = T.strip().split('\n')
    T = '{};\n{};\n{}'.format(*T)
    return np.matrix(T)

def get_result_matrix(hh,pp,rr,T):
    H = np.matrix([[np.cos(hh),np.sin(hh),0],[-np.sin(hh),np.cos(hh),0],[0,0,1]])
    P = np.matrix([[np.cos(pp),-np.sin(pp)*np.sin(rr),-np.cos(rr)*np.sin(pp)],
                  [0,np.cos(rr),-np.sin(rr)],
                  [np.sin(pp),np.sin(rr)*np.cos(pp),np.cos(pp)*np.cos(rr)]])
    return np.array(H*P*T)

def parse_sen(filename,build_index=False):
    with open(filename+'.sen','r',encoding='windows-1251') as file:
        d = []
        index = []
        for line in file:
            line = line.split()
            if build_index:
                index.append('{2}-{0}-{1} {3}:{4}:{5}'.format(*line))
            d.append({'Heading':line[12],'Pitch':line[13],'Roll':line[14]})
#    index = pd.to_datetime(index)
    if not build_index:
        index = np.loadtxt(filename+'_index_file',dtype=np.datetime64,delimiter='\t')
    rotation = pd.DataFrame(d,index=index,dtype='float')
    rotation.loc[:,'Heading'] = rotation.loc[:,'Heading']-90
    rotation = np.radians(rotation)
    return rotation

def get_nortek_velocity_df(filename,columns,index):
    cells = beam_cells if beam2enu else vert_cells
    multi_cols = pd.MultiIndex.from_product([['v1','v2','v3'],cells],names=['Component','Cell'])
    vel = pd.DataFrame(columns=multi_cols)
    for comp in ['v1','v2','v3']:
        df = pd.read_table(filename+'.'+comp,delim_whitespace=True,header=None)
        df['TS'] = index
        df.columns = columns
        df.set_index(['TS','burst','ping'],inplace=True)
        vel.loc[:,comp] = df.values
    vel.index = df.index
    return vel

to_separate_files = True
idx = pd.IndexSlice
comps = ['v1','v2','v3']
filename = ''
if not filename:
    filename = sys.argv[1]
T = ''''''
if T:
    beam_cells, vert_cells, downlooking, beam2enu = parse_aquadopp_hdr(filename)
else:
    beam_cells, vert_cells, downlooking, T, beam2enu = parse_aquadopp_hdr(filename,read_transformation_matrix=True)
T = parse_T(T)
if downlooking:
    T[1] = -T[1]
    T[2] = -T[2]
source_cells = beam_cells if beam2enu else vert_cells
result_cells = vert_cells if beam2enu else beam_cells
columns = ['burst', 'ping', *source_cells, 'TS']
rotation = parse_sen(filename)
source_vel = get_nortek_velocity_df(filename,columns,rotation.index)
columns = pd.MultiIndex.from_product([['v1', 'v2', 'v3'], result_cells],names=['Component', 'Cell'])
result_vel = pd.DataFrame(index=source_vel.index,columns=columns)
Rs = []
for ts in rotation.index:
    Rs.append(get_result_matrix(*rotation.loc[ts].values,T))
if not beam2enu:
    Rs = np.linalg.inv(Rs)
for sc,rc in zip(source_cells,result_cells):
    cell_vel = []
    for source,R in zip(source_vel.loc[:,idx[:,sc]].values,Rs):
        cell_vel.append(np.dot(R,source))
    result_vel.loc[:,idx[:,rc]] = np.array(cell_vel)
result_filename = '/tmp/'+filename+'_enu' if beam2enu else filename+'_beam'
if to_separate_files:
    fmt = [':d',':d']+['%.5f' for i in range(len(beam_cells))]
    for comp in comps:
        output_df = result_vel.loc[:,idx[comp,:]]
        out_filename = '{}.{}.csv'.format(result_filename,comp)
        output_df.to_csv(out_filename,encoding='ascii',float_format='%.5f')
else:
    result_vel.to_csv(result_filename+'.csv',encoding='ascii',float_format='%.5f')

