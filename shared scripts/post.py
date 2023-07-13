import os
import glob
import shutil
import re
from parse_outcar import parse_outcar
import pickle
import argparse
from datetime import datetime
from pymatgen.io.vasp.outputs import Vasprun

root = os.getcwd()
jobsdir = root+"/"+"jobs"

def parse_args():
    parser=argparse.ArgumentParser(description="postprocessing program, reads in statuses, fixes errors, and outputs to post_data.pkl")
    parser.add_argument("-f", "--fix_errors", help="Fixes errored jobs", action="store_true")
    parser.add_argument("-i", "--inits_done", help="initial jobs all finished?", action="store_true")
    parser.add_argument("-j", "--jobs_folder", help="top folder for job files")
    args=parser.parse_args()
    return args

def get_statuses():
    statuses={}
    for jobdir, _, files in os.walk(jobsdir):
        #find folders
        if jobdir.endswith("init") or jobdir.endswith("_so") or jobdir.endswith("_ip") or jobdir.endswith("relax") or "scf" in jobdir or jobdir.endswith("_op"):
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

def change_incar(job_folder,pattern,change):
    if os.path.exists(job_folder+'/INCAR'):
        with open(job_folder+'/INCAR', 'r+') as incar:
            text=incar.read()
            text=re.sub(pattern,change,text)
            incar.seek(0)
            incar.write(text)
            incar.truncate()
        print(f"Changed line {pattern} to {change} in {job_folder}/INCAR")
        return True
    else:
        print("INCAR file not found in "+job_folder)
        return False

def EDDDAV_fixer(job_folder):
    '''fixes EDDDAV errors'''
    if check_contcar(job_folder):
        print('copy CONTCAR to POSCAR')
        shutil.copy(job_folder+'/CONTCAR', job_folder+'/POSCAR')
        print("CONTCAR to POSCAR in "+job_folder)
    else:
        print('CONTCAR not present in '+job_folder)
    return change_incar(job_folder,"ALGO = \w*","ALGO = All")

def ZBRENT_fixer(job_folder):
    '''Copy CONTCAR to POSCAR if exists'''
    if check_contcar(job_folder):
        print('copy CONTCAR to POSCAR')
        shutil.copy(job_folder+'/CONTCAR', job_folder+'/POSCAR')
        print("Fixed! Copied CONTCAR to POSCAR in "+job_folder)
    else:
        print('CONTCAR not present in '+job_folder)
        print('restart from POSCAR instead.')
    return change_incar(job_folder,"IBRION = \w*","IBRION = 1")

def TIME_OUT_fixer(job_folder):
    '''Copy CONTCAR to POSCAR if exists'''
    if check_contcar(job_folder):
        print('copy CONTCAR to POSCAR')
        shutil.copy(job_folder+'/CONTCAR', job_folder+'/POSCAR')
        print("Fixed! Copied CONTCAR to POSCAR in "+job_folder)
        return True
    else:
        print('CONTCAR not present in '+job_folder)
        print('restart from POSCAR instead.')
        return True

def run_fixer(root, statuses):
    with open(root+"/restart_ready.txt",mode='w') as restart_f, open(root+"/failed.txt",mode='w') as failed_f, open(root+"/finished.txt",mode='w') as finished_f:
        for jobdir in statuses:
            print(jobdir)
            stat=statuses[jobdir]
            if stat=="FINISHED":
                print(jobdir)
                print(jobdir,file=finished_f)
            elif stat=="ZBRENT":
                print("ZBRENT error in ",jobdir)
                print("fixing...")
                if ZBRENT_fixer(jobdir):
                    print(jobdir,file=restart_f)
                else:
                    print(jobdir,file=failed_f)
            elif stat=="EDDDAV":
                print("EDDDAV error in ",jobdir)
                print("fixing")
                if EDDDAV_fixer(jobdir):
                    print(jobdir,file=restart_f)
                else:
                    print(jobdir,file=failed_f)
            elif stat=="TIME_OUT":
                print("Time out on ",jobdir)
                print("fixing...")
                if TIME_OUT_fixer(jobdir):
                    print(jobdir,file=restart_f)
                else:
                    print(jobdir,file=failed_f)
            elif stat=="NOT_RUN":
                print("Not run yet: ",jobdir)
                print(jobdir,file=restart_f)
            else:
                print("I don't know what to do with ",jobdir)
                print(jobdir,file=failed_f)

from pymatgen.core import Structure
from pymatgen.io.vasp.inputs import Poscar

def load_poscar(file):
    print(file)
    struct=Poscar.from_file(file).structure
    return struct

if __name__ == '__main__':

    inputs=parse_args()
    jobsdir=inputs.jobs_folder
    print(root+f"post_data-{datetime.now().strftime('%m-%d-%Y')}.pkl")
    statuses=get_statuses()
    print(statuses)
    print(len(statuses))

    inits_done=inputs.inits_done
    fix_errors=inputs.fix_errors

    if fix_errors:
        print("i should fix errors, but this is turned off right now because it needs to be updated to account for scf jobs")
        #run_fixer(root,statuses)
    else:
        print("i won't fix errors")

    #load atomic atomic info
    import yaml

    with open("atomic_info.yaml") as f:
        atomic_info = yaml.safe_load(f)

    data=[]

    for jobdir in statuses:
        job_dat={}
        job_dat["work_dir"]=jobdir
        job_dat["name"]=jobdir.split('/')[-1]
        job_dat["workflow"]=jobdir.split('/')[-2]
        job_dat["state"]=statuses[jobdir]
        if job_dat["state"]=="FINISHED":
            job_dat["state"]="JOB_FINISHED"
            os.chdir(jobdir)
            job_dat["data"]=parse_outcar()
            try:
                job_dat["data"]["bandgap"]=get_bandgap()
            except Exception as e:
                print(f"error reading bandgap for {jobdir}")
                job_dat["data"]["bandgap"]=None
            #load POSCAR
            poscar_struct=load_poscar("POSCAR")
            #load CONTCAR
            contcar_struct=None
            if check_contcar(""):
                contcar_struct=load_poscar("CONTCAR")

            jobdat["data"]["POSCAR"]=poscar_struct
            jobdat["data"]["CONTCAR"]=contcar_struct

            elem_energy=sum([atomic_info[site.specie.name]["energy_per_atom"] for site in struct.sites])
            job_dat["data"]["formation_energy"]=job_dat["data"]["energy"]-elem_energy
            os.chdir(root)
        data.append(job_dat)
        print(f"loaded data from {jobdir}")

    pickle.dump(data,open(root+f"/post_data-{datetime.now().strftime('%m-%d-%Y')}.pkl",'wb'))
