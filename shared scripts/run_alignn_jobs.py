import argparse
import json
import subprocess

def run_job(job_file,cur_i,job_dict):
    id=job_dict["id"]
    print(f"running job {id}")
    root_dir=job_dict["data_folder"]
    config_file=job_dict["config"]
    #   "train_folder_ff.py --root_dir "CONTCAR-model" --config "CONTCAR-model/hp-search/config_atomwise_graphwise_weight=0.25.json" --output_dir="CONTCAR-model/hp-search/graphwise_weight=0.25" --target_key total_mag --atomwise_key mus"
    return_code=subprocess.run(['train_folder_ff.py', '--root_dir', root_dir, '--config', config_file, f'--output_dir={job_dict["out_folder"]}', '--target_key', 'total_mag', '--atomwise_key', 'mus']).returncode
    if return_code==0:
        print(f"job {id} finished")
        state="FINISHED"
    else:
        print(f"job failed with return code",return_code)
        state="FAILED"
    with open(job_file,"r") as f:
        job_list=json.load(f)
    job_list[cur_i]["state"]=state
    with open(job_file,'w') as f:
        json.dump(job_list,f,indent=4)
    return return_code

def next_available(job_list):
    for i,j in enumerate(job_list):
        if j["state"]=="NOT_RUN":
            return i
    return "done"
        
def reset_running(job_file):
    with open(job_file,"r") as f:
        job_list=json.load(f)
    for j in job_list:
        if j["state"]=="RUNNING":
            j["state"]="NOT_RUN"
    with open(job_file,'w') as f:
        json.dump(job_list,f,indent=4)

def parse_args():
    parser=argparse.ArgumentParser(description="script for running jobs defined in joblist json file")
    parser.add_argument("-j", "--job_list", help="json file for joblist")
    parser.add_argument("-r","--reset_running",action='store_true',help="resets jobs labeled RUNNING to")
    args=parser.parse_args()
    return args

if __name__=="__main__":
    args=parse_args()
    job_file=args.job_list
    if args.reset_running:
        reset_running(job_file)
    else:
        with open(job_file,"r") as f:
            job_list=json.load(f)
        job_tot=len(job_list)
        job_unfinished=len([j for j in job_list if j["state"]=="NOT_RUN"])
        print(f"{job_unfinished} to run out of {job_tot}")
        for i in range(job_unfinished):
            with open(job_file,"r") as f:
                job_list=json.load(f)
            cur_i=next_available(job_list)
            if cur_i=="done":
                print("All jobs finished")
                break
            cur_job=job_list[cur_i]
            cur_job["state"]="RUNNING"
            job_list[cur_i]=cur_job
            with open(job_file,'w') as f:
                json.dump(job_list,f,indent=4)
            run_job(job_file,cur_i,cur_job)
