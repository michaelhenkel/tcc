#!/usr/bin/python
import stat
import shutil
import urllib2
import argparse
import subprocess
import json
import os.path
import os
import socket
import fcntl
import struct
from pyroute2 import NSPopen
from pyroute2 import netns
from pyroute2 import NetNS
from pyroute2 import IPDB
from pprint import pprint
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

class SendHTTPData:
   def __init__(self, data, method, HOST, PORT, action):
       self.connection = 'http://' + HOST + ':' + PORT + '/' + action
       self.data = data

   def send(self):
       req = urllib2.Request(self.connection)
       req.add_header('Content-Type', 'application/json')
       response = urllib2.urlopen(req, json.dumps(self.data))
       return json.loads(response.read())

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if format == 'html':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write("body")
        elif format == 'json':
            self.request.sendall(json.dumps({'path':self.path}))
        else:
            self.request.sendall("%s\t%s" %('path', self.path))
        return

    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(self.data_string)
        if self.path == '/createService':
            print data
            result = createService(data['name'],data['terminal'], data['Id'])
            self.request.sendall(result)
        if self.path == '/changeService':
            print data
            result = changeService(data['name'],data['terminal'], data['Id'])
            self.request.sendall(result)
        if self.path == '/deleteService':
            print data
            result = deleteService(data['name'],data['terminal'])
            self.request.sendall(result)
        if self.path == '/createEndpoint':
            print data
            result = createEndpoint(data['name'],data['service'],data['endpointtype'])
            self.request.sendall(result)
        if self.path == '/deleteEndpoint':
            print data
            result = deleteEndpoint(data['name'],data['service'],data['endpointtype'])
            self.request.sendall(result)
        if self.path == '/moveTerminal':
            print data
            result = moveTerminal(data)
            self.request.sendall(result)

def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        print('Directory not copied. Error: %s' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        print('Directory not copied. Error: %s' % e)

def createService(name, terminalName, svcId):
    subprocess.call(["ovs-vsctl", "add-br", "vs-" + name])
    if_svc_name = name
    if_terminal_name = name + '_' + terminalName
    ip_host = IPDB()
    ip_host.create(ifname=if_svc_name, kind='veth', peer=if_terminal_name).commit()
    with ip_host.interfaces[if_svc_name] as veth:
        veth.up()
    with ip_host.interfaces[if_terminal_name] as veth:
        veth.up()
    ip_host.release()
    subprocess.call(["ovs-vsctl", "add-port", "vs-" + name, if_svc_name])
    subprocess.call(["ovs-vsctl", "add-port", "br0", if_terminal_name])
    subprocess.call(["ovs-vsctl", "set", "port", if_terminal_name, "tag=" + str(svcId)])
    return json.dumps({ 'status' : 'created service'})

def moveTerminal(data):
    subprocess.call(['ovs-vsctl', 'del-port', 'br0', data['oldpp']])
    subprocess.call(['ovs-vsctl', 'add-port', 'br0', data['newpp'], '--', 'set', 'interface', data['newpp'], 'type=vxlan', 'options:remote_ip='+data['newppvxlanip']])
    return json.dumps({ 'status' : 'terminal nmoved'})

def changeService(name, terminalName, svcId):
    if_terminal_name = name + '_' + terminalName
    subprocess.call(["ovs-vsctl", "set", "port", if_terminal_name, "tag=" + str(svcId)])
    return json.dumps({ 'status' : 'changed service'})

def deleteService(name, terminalName):
    if_svc_name = name
    if_terminal_name = name + '_' + terminalName
    ip_host = IPDB()
    with ip_host.interfaces[if_terminal_name] as veth:
        veth.remove()
    ip_host.release()
    subprocess.call(["ovs-vsctl", "del-port", "vs-" + name, if_svc_name])
    subprocess.call(["ovs-vsctl", "del-port", "br0", if_terminal_name])
    subprocess.call(["ovs-vsctl", "del-br", "vs-" + name])
    return json.dumps({ 'status' : 'deleted service'})

def createEndpoint(name, svcName, endpointtype):
    if endpointtype == 'ns':
        ip_host = IPDB()
        ip_host.create(ifname=name, kind='veth', peer=name + '_' + svcName).commit()
        ip_ns = IPDB(nl=NetNS(name))
        with ip_host.interfaces[name] as veth:
            veth.net_ns_fd = name
            veth.up()
        with ip_host.interfaces[name + '_' + svcName] as veth:
            veth.up()
        subprocess.call(["ovs-vsctl", "add-port", "vs-" + svcName, name + '_' + svcName])
        ip_host.release()
        ip_ns.release()
        nsp = NSPopen(name, ['dhclient', '-lf', '/tmp/' + name + '.lease', name], stdout=subprocess.PIPE)
        nsp.wait()
        nsp.release()
    if endpointtype == 'lxc':
        subprocess.call(['/usr/bin/lxc-clone','template',name])
        lxcUpOvsScript = '#!/bin/bash\n'
        lxcUpOvsScript += 'BRIDGE="vs-'+ svcName + '"\n'
        lxcUpOvsScript += 'ovs-vsctl --if-exists del-port $BRIDGE $5\n'
        lxcUpOvsScript += 'ovs-vsctl add-port $BRIDGE $5\n'
        f = open('/var/lib/lxc/' + name + '/ovsup.sh','w+')
        f.write(lxcUpOvsScript)
        f.close()
        lxcDownOvsScript = '#!/bin/bash\n'
        lxcDownOvsScript += 'BRIDGE="vs-'+ svcName + '"\n'
        lxcDownOvsScript += 'ovs-vsctl --if-exists del-port $BRIDGE $5\n'
        f = open('/var/lib/lxc/' + name + '/ovsdown.sh','w+')
        f.write(lxcDownOvsScript)
        f.close()
        os.chmod('/var/lib/lxc/' + name + '/ovsup.sh',stat.S_IRWXU)
        os.chmod('/var/lib/lxc/' + name + '/ovsdown.sh',stat.S_IRWXU)
        lxcConfig = 'lxc.include = /usr/share/lxc/config/ubuntu.common.conf\n'
        lxcConfig += 'lxc.arch = x86_64\n' 
        lxcConfig += 'lxc.rootfs = /var/lib/lxc/' + name + '/rootfs\n'
        lxcConfig += 'lxc.utsname = ' + name + '\n'
        lxcConfig += 'lxc.network.type = veth\n'
        lxcConfig += 'lxc.network.veth.pair = ' + name + '\n'
        lxcConfig += 'lxc.network.script.up = /var/lib/lxc/' + name + '/ovsup.sh\n'
        lxcConfig += 'lxc.network.script.down = /var/lib/lxc/' + name + '/ovsdown.sh\n'
        lxcConfig += 'lxc.network.flags = up\n'
        f = open('/var/lib/lxc/' + name + '/config','w+')
        f.write(lxcConfig)
        f.close()
        subprocess.call(['/usr/bin/lxc-start','-d','-n',name])
        pass
    return json.dumps({ 'status' : 'created endpoint'})

def deleteEndpoint(name, svcName, endpointtype):
    if endpointtype == 'ns':
        nsp = NSPopen(name, ['dhclient', '-r', name], stdout=subprocess.PIPE)
        nsp.wait()
        nsp.release()
        netns.remove(name)
        ip_host = IPDB()
        if name + '_' + svcName in ip_host.interfaces:
            with ip_host.interfaces[name + '_' + svcName] as veth:
                veth.remove()
        subprocess.call(["ovs-vsctl", "del-port", "vs-" + svcName, name + '_' + svcName])
    if endpointtype == 'lxc':
        subprocess.call(['/usr/bin/lxc-stop','-n',name])
        subprocess.call(['/usr/bin/lxc-destroy','-n',name])
        pass
    return json.dumps({ 'status' : 'deleted endpoint'})

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def setTunnel():
    f = open('/etc/hostname','r')
    hostname = f.read()
    f.close
    hostname = hostname.rstrip()
    data = json.dumps({'Name':hostname})
    result = SendHTTPData(data=data, method='POST',HOST='192.168.1.1',PORT='6666',action='pullTerminalConfig').send()
    subprocess.call(['ovs-vsctl', 'add-port', 'br0', result['pp'], '--', 'set', 'interface', result['pp'], 'type=vxlan', 'options:remote_ip='+result['ip']])

HOST = get_ip_address('eth0')
PORT = 6666

if __name__ == "__main__":
    setTunnel()
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, Handler)
    print "Serving at: http://%s:%s" % (HOST, PORT)
    httpd.serve_forever()
