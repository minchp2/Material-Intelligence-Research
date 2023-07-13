import os
import glob
import shutil
import re
from parse_outcar import parse_outcar
import pickle
import argparse
from datetime import datetime
import numpy as np
from pymatgen.io.vasp.outputs import Vasprun

root = os.getcwd()
jobsdir = root+"/"+"jobs"
vasp_out_file="vasp.out"

def parse_args():
    parser=argparse.ArgumentParser(description="postprocessing program, reads in statuses, fixes errors, and outputs to post_data file")
    parser.add_argument("-p", "--output_pkl", help="output is .pkl if flag is present, otherwise output is csv", action="store_true")
    parser.add_argument("-j", "--jobs_folder", help="top folder for job files")
    parser.add_argument("-o", "--vasp_out_file", help="name of vasp output file, default=vasp.out",default="vasp.out")
    args=parser.parse_args()
    return args

def get_statuses():
    statuses={}
    vasp_files=["POSCAR","INCAR","KPOINTS","POTCAR"]
    for jobdir, _, files in os.walk(jobsdir):
        #find folders

        if all(f in files for f in vasp_files):
            #look at outfile to see statuses of jobs
            outs=glob.glob(jobdir+"/vasp.out")
            if len(outs)>0:
                with open(glob.glob(jobdir+"/vasp.out")[-1]) as outfile, open(glob.glob(jobdir+"/*.err")[-1]) as err_file:
                    for line in outfile:
                        if "Starting up job" in line:
                            #i+=1
                            pass
                        elif "ZBRENT: fatal error in bracketing" in line:
                            statuses[jobdir]="ZBRENT"
                        elif "reached required accuracy" in line or ("scf" in jobdir and "1 F=" in line):
                            statuses[jobdir]="FINISHED"
                            print(jobdir)
                        elif "ZBRENT: fatal error" in line:
                            statuses[jobdir]="ZBRENT"
                        elif "TIME LIMIT" in line:
                            statuses[jobdir]="TIME_OUT"
                        elif "Error EDDDAV: Call to ZHEGV failed" in line:
                            statuses[jobdir]="EDDDAV"
                    for line in err_file:
                        if "Starting up job" in line:
                            #i+=1
                            pass
                        elif "ZBRENT: fatal error in bracketing" in line:
                            statuses[jobdir]="ZBRENT"
                        elif "reached required accuracy" in line:
                            statuses[jobdir]="FINISHED"
                            print(jobdir)
                        elif "ZBRENT: fatal error" in line:
                            statuses[jobdir]="ZBRENT"
                        elif "TIME LIMIT" in line:
                            statuses[jobdir]="TIME_OUT"
                            print(jobdir,"timed out")
                        if jobdir in statuses:
                            break
                    if jobdir not in statuses:
                        statuses[jobdir]="FAILED"
                        print(jobdir,"was mysterious to me")

    return statuses

def get_bandgap():
    vaspout = Vasprun("vasprun.xml")
    bandstr = vaspout.get_band_structure()
    return bandstr.get_band_gap()

def check_contcar(job_folder):
    if os.path.exists(job_folder+'/CONTCAR'):
        with open(job_folder+'/CONTCAR') as fp:
            for line in fp:
                if line.strip(): return True
    return False

from pymatgen.core import Structure
from pymatgen.io.vasp.inputs import Poscar,Incar,Potcar

def load_poscar(file):
    struct=Poscar.from_file(file).structure
    return struct

def load_incar(jobdir):
    ic=Incar.from_file(os.path.join(jobdir,"INCAR"))
    return ic

def get_potcar_symbols(jobdir):
    pc=Potcar.from_file(os.path.join(jobdir,"POTCAR"))
    return pc.symbols

def rotate_vec(saxis,vec):
    #rotates a vector in the saxis basis to cartesian coordinates
    sx,sy,sz=saxis
    mx,my,mz=vec #vec components in saxis basis
    a=np.arctan2(sy,sx) #angle between saxis and x axis
    b=np.arctan2(np.sqrt(sx**2+sy**2),sz) #angle between saxis and z axis
    return [np.cos(b)*np.cos(a)*mx+np.cos(b)*np.sin(a)*my-np.sin(b)*mz,
           -np.sin(a)*mz+np.cos(a)*my,
           np.sin(b)*np.cos(a)*mx+np.sin(b)*np.sin(a)*my+np.cos(b)*mz]#not sure if this is correct, might be off by 180 degrees

if __name__ == '__main__':

    inputs=parse_args()
    jobsdir=inputs.jobs_folder
    vasp_out_file=inputs.vasp_out_file
    if inputs.output_pkl:
        out_type="pickle"
    else:
        out_type="csv"

    statuses=get_statuses()
    print(statuses)
    print(len(statuses))

    #load atomic atomic info
    import yaml

    with open(os.path.join(os.path.dirname(__file__),"atomic_info.yaml")) as f:
        atomic_info = yaml.safe_load(f)

    data=[]

    for jobdir in statuses:
        job_dat={}
        job_dat["work_dir"]=jobdir
        job_dat["name"]=jobdir.split('/')[-1]
        job_dat["workflow"]=jobdir.split('/')[-2]
        job_dat["state"]=statuses[jobdir]
        job_dat["incar"]=load_incar(jobdir)
        job_dat["potcar_pseudos"]=get_potcar_symbols(jobdir)
        job_dat["data"]=dict()

        if job_dat["state"]=="FINISHED":
            job_dat["state"]="JOB_FINISHED"
            os.chdir(jobdir)
            dat=parse_outcar()
            try:
                bg=get_bandgap()
                job_dat["data"]["bandgap"]=bg['energy']
                job_dat["data"]["bg_direct"]=bg['direct']
                job_dat["data"]["bg_transition"]=bg['transition']
            except Exception as e:
                print(f"error reading bandgap for {jobdir}")
            #load POSCAR
            poscar_struct=load_poscar("POSCAR")
            #load CONTCAR
            contcar_struct=load_poscar("CONTCAR")

            job_dat["data"]["POSCAR"]=poscar_struct
            job_dat["data"]["CONTCAR"]=contcar_struct

            elem_energy=sum([atomic_info[site.specie.name]["energy_per_atom"] for site in poscar_struct.sites])

            NIONS=dat['NIONS']
            saxis=np.array(job_dat["incar"]["SAXIS"].split()).astype(float)
            if job_dat["incar"]["LNONCOLLINEAR"]:
                mag_table=dat['magnetization'][-3:] #get table of ion magnetizations
                ion_mags_x=[ion_mag[-1] for ion_mag in mag_table[0][2]]
                ion_mags_y=[ion_mag[-1] for ion_mag in mag_table[1][2]]
                ion_mags_z=[ion_mag[-1] for ion_mag in mag_table[2][2]]
                mus=[rotate_vec(saxis,[mux,muy,muz]) for mux,muy,muz in zip(ion_mags_x,ion_mags_y,ion_mags_z)]
                mags=[np.sqrt(mux**2+muy**2+muz**2) for mux,muy,muz in zip(ion_mags_x,ion_mags_y,ion_mags_z)]
                x_tot=sum(ion_mags_x)
                y_tot=sum(ion_mags_y)
                z_tot=sum(ion_mags_z)
                total_mag=np.sqrt(x_tot**2+y_tot**2+z_tot**2)
                total_mu=rotate_vec(saxis,[x_tot,y_tot,z_tot])
            else:
                mag_table=dat['magnetization'][-1][2] #get table of ion magnetizations
                tots=[ion_mag[-1] for ion_mag in mag_table] #total magnetization of each ion
                mus=[muz*saxis for muz in tots]
                mags=[abs(muz) for muz in tots]
                total_mag=sum(tots)
                total_mu=list(sum(tots)*saxis) #total magnetization vector of material
            job_dat["data"]["mag_table"]=mag_table
            job_dat["NIONS"]=NIONS
            es=dat['energy']
            if type(es)==list:
                energy=es[-1]
                pos=np.array(dat['position_force'][-1])[:,0:3]
                lattice_vecs=np.array(dat['lattice_vecs'][-1])[:,0:3]
            else:
                energy=es
                pos=np.array(dat['position_force'])[:,0:3]
                lattice_vecs=np.array(dat['lattice_vecs'][-1])[:,0:3]
            job_dat["data"]["energy"]=energy
            job_dat["data"]["pos"]=pos
            job_dat["data"]["lattice_vecs"]=lattice_vecs
            job_dat["data"]["formation_energy"]=energy-elem_energy
            job_dat["data"]["mag_table"]=mag_table
            job_dat["data"]["mus"]=mus
            job_dat["data"]["mags"]=mags
            job_dat["data"]["total_mu"]=total_mu
            job_dat["data"]["total_mag"]=total_mag

            os.chdir(root)

        data.append(job_dat)
        print(f"loaded data from {jobdir}")

    if out_type=="pickle":
        pickle.dump(data,open(root+f"/post_data-{datetime.now().strftime('%m-%d-%Y')}.pkl",'wb'))
    else:
        flat_data=[dict({k:j[k] for k in ["work_dir","name","workflow","state","incar","potcar_pseudos"]},**j['data']) for j in data]
        import pandas as pd
        pd.DataFrame(flat_data).to_csv(root+f"/post_data-{datetime.now().strftime('%m-%d-%Y')}.csv")
