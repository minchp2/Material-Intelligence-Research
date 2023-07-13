import os
import re
import pandas as pd
import numpy as np
import yaml
import requests

base_url = "https://www.materialsproject.org/rest/v2/materials/"
api_key =  "SmwkewpQlSGF4g18iXMJ"
element_list = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na',
 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr',
  'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
   'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd',
    'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'Hf', 'Ta', 'W', 'Re',
     'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr',
      'Ra', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl',
       'Mc', 'Lv', 'Ts', 'Og', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd',
        'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Ac', 'Th', 'Pa', 'U', 'Np',
         'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr']

def gen_atomic_fe():
    fe_data = {e: {"energy_per_atom": np.nan} for e in element_list}
    for atom in element_list:
        print(f"getting info for {atom}")
        url = f"{base_url}{atom}/vasp?API_KEY={api_key}"
        r = requests.get(url)
        if r.status_code == 200:
            candidate_materials = r.json()["response"]
            for material in candidate_materials:
                if material["formation_energy_per_atom"] == 0.0:
                    fe_data[atom] = material
        else:
            print("Request for {atom} failed.")
    with open("atomic_info.yaml", mode='w') as f:
        yaml.dump(fe_data, f)

if __name__ == '__main__':
    gen_atomic_fe()
