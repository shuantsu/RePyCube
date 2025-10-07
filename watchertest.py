import os

def watcher(filename):
    def _w(r=[0,0]):
        mtime = os.stat(filename).st_mtime
        changed = False
        if r[1] != mtime:
            changed = True
            r[1] = mtime
            r[0] += 1
        return changed and r[0] > 1
    return _w