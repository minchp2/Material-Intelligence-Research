import yaml
import os

with open(os.path.join(os.path.dirname(__file__),"atomic_info.yaml")) as f:
    atomic_info = yaml.safe_load(f)

def calc_formation_energy(elem_list,energy):
    """calculates the formation energy relative to the lowest energy elemental state of each atom in elem_list as found in materials project"""
    elem_energy=sum([atomic_info[elem]["energy_per_atom"] for elem in elem_list])
    return energy-elem_energy