import subprocess
import os

cwd = os.getcwd()

p2 = subprocess.Popen("python3 " +cwd+"/node_server.py -p " +str(8001) +" -n "+ "pp2" + " -t " + "c", shell=True, start_new_session = True, stdin =None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


while True:
  line = p2.stderr.readline()
  if not line:
    break
  print("Line:", line.rstrip())
