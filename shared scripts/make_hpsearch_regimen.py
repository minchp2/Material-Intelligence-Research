import argparse
import json
import random

with open("/projects/MI2Dmaterials/minchp/ALIGNN/alignn/config-default.json",'r') as f:
    default_config=json.load(f)

def parse_args():
    parser=argparse.ArgumentParser(description="makes a list of hyperparameter jobs to fit a hp grid")
    parser.add_argument("-n", "--n_samples", help="number of random samples to search")
    parser.add_argument("-t", "--workflow_tag", help="tag for workflow")
    parser.add_argument("-r","--random",action='store_true',help="run random search? if no, defaults to grid search")
    parser.add_argument("-o","--out_folder",help="out directory to store config files and job folders")
    parser.add_argument("-g","--grid",help="hyperparameter grid file")
    parser.add_argument("-d","--data_folder",help="location of training data")
    parser.add_argument("-c","-default_config",help="default config file")

    args=parser.parse_args()
    return args

if __name__ == '__main__':

    args=parse_args()
    if "default_config" in args:
        with open(args.default_config,'r') as f:
            default_config=json.load(f)
    tag=args.workflow_tag
    out_folder=args.out_folder
    data_folder=args.data_folder
    if args.random:
        N=int(args.n_samples)
    grid_file=args.grid
    assert grid_file.endswith(".json")
    with open(grid_file,'r') as f:
        hp_grid=json.load(f)
    print(hp_grid)
    hp_job_list=list()
    if args.random:
        hp_sets=[{k: random.choice(hp_grid[k]) for k in hp_grid} for i in range(N)]
    else:
        hp_sets=[]
    for i,hp_list in enumerate(hp_sets):
        job_dict={'id':f"{tag}_{i:03d}",'state':"NOT_RUN"}
        new_config=default_config.copy()
        for param in hp_list:
            if param in new_config["model"]:
                new_config["model"][param]=hp_list[param]
            elif param in new_config:
                new_config[param]=hp_list[param]
            else:
                print(f"could not find param {param}")
        j_obj=json.dumps(new_config, indent=4)
        with open(f"{out_folder}/config_atomwise_hp_search_{tag}_{i:03d}.json","w") as f:
             f.write(j_obj)
        job_dict.update(hp_list)
        job_dict["config"]=f"{out_folder}/config_atomwise_hp_search_{tag}_{i:03d}.json"
        job_dict["out_folder"]=f"{out_folder}/{tag}_{i:03d}"
        job_dict["data_folder"]=data_folder
        hp_job_list.append(job_dict)

    with open(f"{tag}_hp_regimen.json","w") as f:
        json.dump(hp_job_list,f)