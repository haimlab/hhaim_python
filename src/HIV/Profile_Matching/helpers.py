from constants import AMINOACIDS
from file_parse import logConvert


# compute profile from all given envelopes
# i -> column index of Amino Acids to be counted
def envelopes_to_profile(envs, i, log=True):
    count = {aa: 0 for aa in AMINOACIDS}
    for e in envs:
        count[e[i]] += 1
    s = sum([count[aa] for aa in count])
    for aa in count:
        count[aa] = logConvert(count[aa] / s) if log else count[aa] / s
    return count