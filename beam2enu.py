#!/bin/python

import numpy as np
import pandas as pd
import fnmatch
import os
import sys

def parse_aquadopp_hdr(filename, read_transformation_matrix=False):
    with open(filename+".hdr", "r", encoding="windows-1251") as f:
        if read_transformation_matrix:
            T = [] # if the transformation matrix is not set, then read
        beam_cells = []
        vert_cells = []
        read_cells = False
        lines = f.readlines() # read the whole file and then iterate over lines
        for i, line in enumerate(lines):
            if read_cells and line is "\n": # if currently reading cells and encounter empty line
                read_cells = False # then stop reading cells
                continue
            elif line.startswith("-----"):
                continue
            elif line is "\n":
                continue
            elif line.startswith("Coordinate system"): # decide what coordinate system was used
                beam2enu = True if line.split()[-1] == "BEAM" else False
            elif line.startswith("Orientation"): 
                if line.split()[-1] == "DOWNLOOKING":
                    downlooking = True
                else:
                    downlooking = False
                continue
            elif line.startswith("Transformation matrix"):
                if read_transformation_matrix:
                    T = lines[i:i+3]
                continue
            elif line.startswith("       Beam    Vertical\n"):
                read_cells = True
                continue
            if read_cells:
                cell = line.split()
                beam_cells.append(float(cell[1]))
                vert_cells.append(float(cell[2]))
    return_list = [
            beam_cells,
            vert_cells,
            downlooking,
            ]
    if read_transformation_matrix:
        return_list.append(T)
    return_list.append(beam2enu)
    return return_list

def parse_T(T):
    if isinstance(T, list):
        T = [s.strip("Transformation matrix").strip() for s in T]
    else:
        T = T.strip().split("\n")
    T = "{};\n{};\n{}".format(*T)
    return np.matrix(T)

def get_result_matrix(hh, pp, rr, T):
    H = np.matrix([
        [np.cos(hh), np.sin(hh), 0],
        [-np.sin(hh), np.cos(hh), 0],
        [0, 0, 1],
        ])
    P = np.matrix([
        [np.cos(pp), -np.sin(pp)*np.sin(rr), -np.cos(rr)*np.sin(pp)],
        [0, np.cos(rr), -np.sin(rr)],
        [np.sin(pp), np.sin(rr)*np.cos(pp), np.cos(pp)*np.cos(rr)],
        ])
    return np.array(H*P*T)

def parse_sen(filename, build_index=False):
    with open(filename+".sen", "r", encoding="windows-1251") as file:
        d = []
        index = []
        for line in file:
            line = line.split()
            if build_index:
                index.append("{2}-{0}-{1} {3}:{4}:{5}".format(*line))
            d.append({
                "Heading":line[12],
                "Pitch":line[13],
                "Roll":line[14],
                })
#    index = pd.to_datetime(index)
    if not build_index:
        index = np.loadtxt(
                filename+"_index_file",
                dtype=np.datetime64,
                delimiter="\t",
                )
    rotation = pd.DataFrame(
            d,
            index=index,
            dtype="float32",
            )
    rotation.loc[:, "Heading"] = rotation.loc[:, "Heading"]-90
    rotation = np.radians(rotation)
    return rotation

def get_nortek_velocity_df(filename, columns, index,
                           beam2enu, vert_cells, beam_cells):
    cells = beam_cells if beam2enu else vert_cells
    multi_cols = pd.MultiIndex.from_product(
            [["v1", "v2", "v3"], cells],
            names=["Component", "Cell"],
            )
    vel = pd.DataFrame(
            columns=multi_cols,
            dtype="float32",
            )
    for comp in ["v1", "v2", "v3"]:
        df = pd.read_csv(
                f"{filename}.{comp}",
                delim_whitespace=True,
                header=None,
                sep='\t',
                )
        df["TS"] = index
        df.columns = columns
        df.set_index(["TS", "burst", "ping"], inplace=True)
        vel.loc[:, comp] = df.values
    vel.index = df.index
    return vel

def save_file(df, to_separate_files, result_filename, beam2enu, cells):
    idx = pd.IndexSlice
    if to_separate_files:
        fmt = [":d", ":d"]+["%.5f" for i in range(len(cells))]
        for comp in ["v1", "v2", "v3"]:
            output_df = df.loc[:, idx[comp, :]]
            output_df.columns = output_df.columns.levels[-1]
            out_filename = "{}.{}.csv".format(result_filename, comp)
            output_df.to_csv(
                    out_filename,
                    encoding="ascii",
                    float_format="%.5f",
                    )
    else:
        df.to_csv(
                f"{result_filename}.csv",
                encoding="ascii",
                float_format="%.5f",
                )

def parse_sen(filename):
    names = [
        "Month",
        "Day",
        "Year",
        "Hour",
        "Minute",
        "Second",
        "Burst counter",
        "Ensemble counter",
        "Error code",
        "Status code",
        "Battery voltage",
        "Soundspeed",
        "Heading",
        "Pitch",
        "Roll",
        "Pressure",
        "Temperature",
        "Analog input 1",
        "Analog input 2",
        ]
    sen = pd.read_table(f"{filename}.sen", names=names, delim_whitespace=True)
    index_cols = ["Year", "Month", "Day", "Hour", "Minute", "Second"]
    index_formatter = lambda x: "{0:02.0f}-{1:02.0f}-{2:02.0f} {3:02.0f}:{4:02.0f}:{5:02.4f}".format(*x)
    index = sen.loc[:, index_cols].apply(index_formatter,
                                         axis=1)
    index = index.astype(np.datetime64)
    index = index.values
    rotation = sen.loc[:, ["Heading", "Pitch", "Roll"]]
    rotation.loc[:, "Heading"] = rotation.loc[:, "Heading"]-90
    rotation = np.radians(rotation)
    rotation = rotation.astype("float32")
    rotation.index = index
    return rotation, index

def convert_data_coordinates(filename,
                             save_in_original_coords = True,
                             to_separate_files = True,
                             T = ""):
    idx = pd.IndexSlice
    comps = ["v1", "v2", "v3"]
    if T:
        [beam_cells,
         vert_cells,
         downlooking,
         beam2enu] = parse_aquadopp_hdr(filename)
    else:
        [beam_cells,
         vert_cells,
         downlooking,
         T,
         beam2enu] = parse_aquadopp_hdr(filename,
                                        read_transformation_matrix=True)
    T = parse_T(T)
    if downlooking:
        T[1] = -T[1]
        T[2] = -T[2]
    source_cells = beam_cells if beam2enu else vert_cells
    result_cells = vert_cells if beam2enu else beam_cells
    columns = ["burst", "ping", *source_cells, "TS"]
    print("reading {}.sen file".format(filename))
    rotation, index = parse_sen(filename)
    print("reading velocity data")
    source_vel = get_nortek_velocity_df(filename=filename,
                                        columns=columns,
                                        index=index,
                                        beam2enu=beam2enu,
                                        vert_cells=vert_cells,
                                        beam_cells=beam_cells)
    columns = pd.MultiIndex.from_product([["v1", "v2", "v3"], result_cells],
                                        names=["Component", "Cell"])
    result_vel = pd.DataFrame(index=source_vel.index,
                              columns=columns,
                              dtype="float32")
    print("building result matrix")
    Rs = []
    for ts in rotation.index:
        Rs.append(get_result_matrix(*rotation.loc[ts].values, T))
    if not beam2enu:
        Rs = np.linalg.inv(Rs)
    for sc, rc in zip(source_cells, result_cells):
        result_vel.loc[:, idx[:, rc]] = np.einsum("ijk, ik->ij",
                                                Rs,
                                                source_vel.loc[:, idx[:, sc]].values)
    print("saving")
    result_filename = filename+"_enu" if beam2enu else filename+"_beam"
    result_filename_source = filename+"_beam" if beam2enu else filename+"_enu"
    if save_in_original_coords:
        print("saving in original coordinates")
        save_file(source_vel,
                  to_separate_files=to_separate_files,
                  result_filename=result_filename_source,
                  beam2enu=beam2enu,
                  cells=source_cells)
    print("saving in new coordinates")
    save_file(result_vel, 
              to_separate_files=to_separate_files,
              result_filename=result_filename,
              beam2enu=beam2enu,
              cells=result_cells)

def guess_filename(working_dir=None):
    if not working_dir:
        working_dir = '.'
    hdr_file = fnmatch.filter(names=os.listdir(working_dir), pat="*.hdr")
    hdr_file = hdr_file[0]
    filename = hdr_file.split('.')[0]
    print(f"Found file {filename}")
    return filename


def main(filename=None):
    if not filename:
        filename = guess_filename()
    if f"{filename}_beam.v1.csv" not in os.listdir():
        convert_data_coordinates(filename)

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except:
        print("Script runs without argument")
        print("Assumed one deployment per directory")
        main()
