import os
import pathlib
import socket
import subprocess
import time

path = pathlib.Path(__file__).parent.resolve()
host = socket.gethostname()

try:
    os.mkdir('logs')
except FileExistsError:
    pass

print('Launching')
proc = subprocess.Popen(['hid_listen.exe'], stdout=subprocess.PIPE)

with open(os.path.join(path, 'logs', host + '_log.txt'), 'at', buffering=1024*10) as f:
    try:
        while True:
            line = proc.stdout.readline()
            if line is None:
                break
            line = line.decode()
            if line.startswith('C:'):
                print(time.time(), line.rstrip(), file=f)
    except KeyboardInterrupt:
        proc.terminate()
