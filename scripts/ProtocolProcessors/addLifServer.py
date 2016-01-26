import socket
import os, os.path
import time
 
if os.path.exists( "/tmp/addlif.socket" ):
  os.remove( "/tmp/addlif.socket" )
 
print "Opening socket..."
server = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
server.bind("/tmp/addlif.socket")
 
print "Listening..."
while True:
  try:
    datagram = server.recv( 1024 )
    if not datagram:
      break
    else:
      print "-" * 20
      print datagram
      a = datagram.split(' ')
      print a
      if "DONE" == datagram:
        break
  except KeyboardInterrupt, k:
    print 'shutting down'
    server.close()
    os.remove( "/tmp/addlif.socket" )
    print "Done"
print "-" * 20
print "Shutting down..."
server.close()
os.remove( "/tmp/addlif.socket" )
print "Done"
