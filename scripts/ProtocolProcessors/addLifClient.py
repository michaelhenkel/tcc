import sys
import socket
import os, os.path

if sys.argv[1] == 'del':
    data = sys.argv[1] + ' ' + sys.argv[2] + ' ' + sys.argv[3]
else:
    data = sys.argv[1] + ' ' + sys.argv[2] + ' ' + sys.argv[3] + ' ' + sys.argv[4] + ' ' + sys.argv[5]
 
print "Connecting..."
if os.path.exists( "/tmp/addlif.socket" ):
    client = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
    client.connect( "/tmp/addlif.socket" )
    client.send(data)
    client.close()
else:
    print "Couldn't Connect!"
print "Done"
