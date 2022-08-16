import datetime
import os
from pathlib import Path
import platform
import socket
import subprocess
import logging
import threading
import time

MAX_LOG_SIZE_MIB = 1

host = socket.gethostname()

try:
    os.mkdir('logs')
except FileExistsError:
    pass

logFileName = Path(__file__).parent.resolve() / 'logs' / (host + '_log.txt')

if logFileName.is_file():
    statInfo = logFileName.stat()
    if statInfo.st_size > MAX_LOG_SIZE_MIB*1024*1024:
        mtime = statInfo.st_mtime
        archivedLogFileName = logFileName.with_stem(logFileName.stem + f"_{int(mtime)}")
        logFileName.rename(archivedLogFileName)

logFileName = Path(__file__).parent.resolve() / 'logs' / (host + '_log.txt')

def flush_(fh):
    while 1:
        time.sleep(20)
        print('Flushing', time.time())
        fh.flush()

log = logging.getLogger('file')
log.setLevel(level=logging.INFO)

formatter = logging.Formatter('%(message)s')

fh = logging.FileHandler(logFileName)
fh.setLevel(level=logging.INFO)
fh.setFormatter(formatter)

log.addHandler(fh)

flusher = threading.Thread(target=flush_, args=(fh, ))
flusher.daemon = True
flusher.start()

print('Launching')
exe = {'Windows': 'hid_listen.exe', 'Darwin': './hid_listen.app'}[platform.system()]
proc = subprocess.Popen([exe], stdout=subprocess.PIPE)

try:
    while True:
        line = proc.stdout.readline()
        if line is None:
            break
        line = line.decode()
        if line.startswith('C:'):
            log.info("%s %s" % (time.time(), line.rstrip()))
except KeyboardInterrupt:
    proc.terminate()
