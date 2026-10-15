"""Branch-transfer include recovered from the user's earlier SAS source.

All supplied transformations are commented out; no active rules remain.
The preserved source is original_jcl/NPLNTB.sas.
"""
def apply(row):
    return row.copy()

if __name__ == '__main__':
    print('NPLNTB: no active branch-transfer rules in the supplied source.')
