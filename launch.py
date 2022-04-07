import os
import pathlib
import socket
import subprocess
import logging
import threading
import time

path = pathlib.Path(__file__).parent.resolve()
host = socket.gethostname()

try:
    os.mkdir('logs')
except FileExistsError:
    pass

def flush_(fh):
    while 1:
        time.sleep(20)
        print('Flushing', time.time())
        fh.flush()

log = logging.getLogger('file')
log.setLevel(level=logging.INFO)

formatter = logging.Formatter('%(message)s')

fh = logging.FileHandler(os.path.join(path, 'logs', host + '_log.txt'))
fh.setLevel(level=logging.INFO)
fh.setFormatter(formatter)

log.addHandler(fh)

flusher = threading.Thread(target=flush_, args=(fh, ))
flusher.daemon = True
flusher.start()

print('Launching')
proc = subprocess.Popen(['hid_listen.exe'], stdout=subprocess.PIPE)

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
