#!/usr/bin/python
import sys
import struct
import fcntl
import socket
import traceback
import ruamel.yaml
import argparse
import subprocess
import json
import os.path
import os
import StringIO
import guestfs
import shutil
import libvirt
import time
import uuid
import netifaces
import random
from keystoneclient.v2_0 import client
from netaddr import *
from vnc_api import vnc_api
from pyroute2 import netns
from pyroute2 import NetNS
from pyroute2 import IPDB
from pprint import pprint
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

api_server='192.168.1.130'
api_port='8082'
admin_user = 'admin'
admin_password = 'contrail123'
admin_tenant = 'admin'
imageDirectory = '/var/lib/libvirt/images'
scriptDirectory = 'scripts'
definitionDirectory = '/var/lib/libvirt/definitions'
imageTemplateFileNamePP ='protocol_processor.qcow2'
imageTemplateFileNameTE ='terminal.qcow2'
imageTemplateFileNameVR ='virtual_router.qcow2'
nfsServer = '192.168.1.1'

def randomMAC():
    mac = [ 0x52, 0x54, 0x00,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

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
        print data
        if self.path == '/createVirtualRouter':
            result = VirtualRouter(data).create()
            self.request.sendall(result)
        if self.path == '/deleteVirtualRouter':
            result = VirtualRouter(data).delete()
            self.request.sendall(result)

        if self.path == '/createProtocolProcessor':
            result = ProtocolProcessor(data).create()
            self.request.sendall(result)
        if self.path == '/deleteProtocolProcessor':
            result = ProtocolProcessor(data).delete()
            self.request.sendall(result)

        if self.path == '/createTerminal':
            result = Terminal(data).create()
            self.request.sendall(result)
        if self.path == '/deleteTerminal':
            result = Terminal(data).delete()
            self.request.sendall(result)

        if self.path == '/createCustomer':
            result = Customer(data).create()
            self.request.sendall(result)
        if self.path == '/deleteCustomer':
            result = Customer(data).delete()
            self.request.sendall(result)

        if self.path == '/pullTerminalConfig':
            result = pullTerminalConfig(data)
            self.request.sendall(result)

def pullTerminalConfig(terminalData):
    f = open('tcc.yaml','r')
    tccConfig = f.read()
    tccConfigObject = ruamel.yaml.load(tccConfig, ruamel.yaml.RoundTripLoader)
    f.close()
    terminalData = json.loads(terminalData)
    print terminalData
    for terminal in tccConfigObject['Terminals']:
        termObject = json.loads(json.dumps(terminal))
        print termObject
        if termObject['name'] == terminalData['Name']:
            pp = termObject['protocolprocessor']
    for ppObj in tccConfigObject['ProtocolProcessors']:
        ppObject = json.loads(json.dumps(ppObj))
        if ppObject['name'] == pp:
            ppIp = ppObject['vxlanip']
    return json.dumps({'pp':pp,'ip':ppIp})

class Customer(object):
    def __init__(self, data):
        self.vnc_client = vnc_api.VncApi(
            username = admin_user,
            password = admin_password,
            tenant_name = admin_tenant,
            api_server_host=api_server,
            api_server_port=api_port,
            auth_host=api_server)
        self.ks_client = client.Client(username=admin_user, password=admin_password,
                                       tenant_name=admin_tenant, auth_url='http://' + api_server + ':5000/v2.0')
        print data
        self.name = data['name']
    def create(self):
        try:
            tenant = self.ks_client.tenants.create(tenant_name=self.name, enabled=True)
        except Exception as e:
            print e
            return json.dumps({'Error':str(e)})
        users = self.ks_client.users.list()
        my_user = [x for x in users if x.name==admin_user][0]
        roles = self.ks_client.roles.list()
        role = [x for x in roles if x.name=='admin'][0]
        self.ks_client.roles.add_user_role(my_user, role, tenant)
        tenantId = uuid.UUID('{'+ tenant.id + '}')
        self.vnc_client.project_read(id = str(tenantId))
        return json.dumps({'status':'customer created'})
    def delete(self):
        projectObj = self.vnc_client.project_read(fq_name_str = 'default-domain:'+self.name)
        self.vnc_client.project_delete(id = projectObj.uuid)
        tenants = self.ks_client.tenants.list()
        tenant = [x for x in tenants if x.name==self.name][0]
        self.ks_client.tenants.delete(tenant)
        return json.dumps({'status':'customer deleted'})

def createImage(name, vmType, fileList, interfaceList, vsList=None):
    print vmType
    if vmType == 'VirtualRouters':
        imageTemplateFileName = imageTemplateFileNameVR
        ram='4000'
        vcpus='2'
    if vmType == 'ProtocolProcessors':
        imageTemplateFileName = imageTemplateFileNamePP
        ram='384'
        vcpus='1'
    if vmType == 'Terminals':
        imageTemplateFileName = imageTemplateFileNameTE
        ram='384'
        vcpus='1'
    imageFile = imageDirectory + '/' + vmType + '/' + name + '.img'
    definitionTemplateFile = definitionDirectory + '/' + vmType + '/template.xml'
    definitionFile = definitionDirectory + '/' + vmType + '/' + name + '.xml'
    if os.path.isfile(imageFile):
        os.remove(imageFile)
    eth0_mac = randomMAC()
    interfaceMacList = {}
    for interface in interfaceList:
        print "interface name: %s" % interface
        if interface['name'] == 'vhost0':
            print 'setting mac'
            interface['mac'] = eth0_mac
        interfaceFileDict = createInterfaceConfiguration(name, interface)
        fileList.append(interfaceFileDict)
    hostnameFileDict = createHostname(name)
    scriptFileDict = { 'src' : scriptDirectory + '/' + vmType + '/script.sh', 'dst' : '/script.sh' }
    imageTemplatePath = '/var/lib/libvirt/images/' + vmType + '/' + imageTemplateFileName
    fileList.append(hostnameFileDict)
    fileList.append(scriptFileDict)
    shutil.copy2(imageTemplatePath, imageFile)
    '''
    g = guestfs.GuestFS ()
    g.add_drive(imageFile)
    g.launch()
    g.mount("/dev/sda1", "/")
    for file in fileList:
        g.upload(file['src'], file['dst'])
    g.sync()
    g.umount_all()
    '''
    for file in fileList:
        subprocess.call(['/usr/bin/virt-customize','--upload',file['src']+':'+file['dst'],'-a',imageFile])
    virtInstall = ['/usr/bin/virt-install',
        '--name=%s' % name,
        '--disk=%s' % imageFile,
        '--vcpus=%s' % vcpus,
        '--ram=%s' % ram,
        '--network=network=br0,model=virtio,target=eth0_%s,mac=%s' % (name, eth0_mac),
        '--virt-type=kvm',
        '--import',
        '--graphics=vnc',
        '--serial=pty',
        '--noautoconsole',
        '--console=pty,target_type=virtio']
    if vsList:
        for vs in vsList:
            virtInstall.append('--network=network=%s,model=virtio,target=%s' % (vs['switchName'], vs['interfaceName']))
    print virtInstall
    subprocess.call(virtInstall)
    subprocess.call(['ifconfig','eth0_'+name,'mtu','9000'])
    if vsList:
        for vs in vsList:
            while vs['interfaceName'] not in netifaces.interfaces():
                print 'interface not there, yet' % vs['interfaceName']
            subprocess.call(['ifconfig',vs['interfaceName'],'mtu','9000'])

def destroyImage(name, vmType):
    definitionFile = definitionDirectory + '/' + vmType + '/' + name + '.xml'
    imageFile = imageDirectory + '/' + vmType + '/' + name + '.img'
    conn = libvirt.open('qemu:///system')
    dom0 = conn.lookupByName(name)
    dom0.destroy()
    dom0.undefine()
    os.remove(definitionFile)
    os.remove(imageFile)

def createInterfaceConfiguration(vmName, interface):
    interfaceString = 'auto ' + interface['name'] + '\n'
    if  interface['Type'] == 'ovs':
        interfaceString += 'allow-ovs ' + interface['name'] + '\n'
        interfaceString += 'iface ' + interface['name'] + ' inet manual' + '\n'
        interfaceString += '    ovs_type OVSBridge' + '\n'
        portList = ' '.join(interface['Ports'])
        interfaceString += '    ovs_ports ' + portList + '\n'
    else:
        if 'Bridge' in interface:
            interfaceString += 'allow-' + interface['Bridge'] + ' ' + interface['name'] + '\n'
            if interface['Type'] == 'l2':
                interfaceString += 'iface ' + interface['name'] + ' inet manual' + '\n'
                interfaceString += '    ovs_bridge ' + interface['Bridge'] + '\n'
                interfaceString += '    ovs_type OVSPort' + '\n'
        else:
            if 'ipaddress' in interface:
                interfaceString += 'iface ' + interface['name'] + ' inet static' + '\n'
                if interface['Type'] == 'vhost':
                    print 'interface: %s', interface
                    interfaceString += '    pre-up /opt/contrail/bin/if-vhost0\n'
                    interfaceString += '    post-up ip link set vhost0 address ' + interface['mac'] + '\n'
                interfaceString += '    address ' + interface['ipaddress'] + '\n'
                interfaceString += '    netmask ' + interface['netmask'] + '\n'
                if 'dns' in interface:
                    interfaceString += '    dns-nameservers ' + interface['dns'] + '\n'
                if 'gateway' in interface:
                    interfaceString += '    gateway ' + interface['gateway'] + '\n'
            else:
                interfaceString += 'iface ' + interface['name'] + ' inet manual' + '\n'
                if interface['Type'] == 'vhost':
                    interfaceString += 'pre-up ifconfig ' + interface['name'] + ' up\n'
                    interfaceString += 'pre-down ifconfig ' + interface['name'] + ' down\n'
    if 'Mtu' in interface:
        interfaceString += '    mtu ' + interface['Mtu'] + '\n'
    interfaceFile = open('/tmp/' + vmName + '_' + interface['name'],'w')
    interfaceFile.write(interfaceString)
    interfaceFile.close()
    return { 'src' : '/tmp/' + vmName + '_' + interface['name'], 'dst' : '/etc/network/interfaces.d/' + interface['name'] + '.cfg'}

def createHostname(vmName):
    hostNameFile = open('/tmp/' + vmName + '_hostname','w')
    hostNameFile.write(vmName + '\n')
    hostNameFile.close()
    return { 'src' : '/tmp/' + vmName + '_hostname', 'dst' : '/etc/hostname' }
    
class Terminal(object):
    def __init__(self, terminalObject):
        self.terminalObject = terminalObject
        self.name = self.terminalObject['name']
        print 'create terminal'
    def create(self):
        fileList = []
        terminalServerFileDict = { 'src' : scriptDirectory + '/Terminals/terminalServer.py', 'dst' : '/terminalServer.py' }
        fileList.append(terminalServerFileDict)
        interfaceList = []
        vsList = []
        intEth0 = { 'name':'ens3','ipaddress':self.terminalObject['ipaddress'],'dns':self.terminalObject['mgmtDns'],'netmask':self.terminalObject['mgmtNetmask'],'gateway':self.terminalObject['mgmtGateway'], 'Type':'l3'}
        intEth1 = { 'name':'ens4','ipaddress':self.terminalObject['vxlanip'],'netmask':self.terminalObject['vxlanNetmask'],'Type':'l3','Mtu':'9000'}
        intBr0 = { 'name':'br0','Type':'ovs','Ports': ['ens4']}
        interfaceList.append(intEth0)
        interfaceList.append(intEth1)
        interfaceList.append(intBr0)
        vs_eth1 = { 'interfaceName': 'eth1_' + self.terminalObject['name'] , 'switchName' : "br0" }
        vsList.append(vs_eth1)
        createImage(self.terminalObject['name'], 'Terminals', fileList, interfaceList, vsList=vsList)
        return json.dumps({'status':'created Terminal'})
    def delete(self):
        destroyImage(self.terminalObject['name'], 'Terminals')
        return json.dumps({'status':'deleted Terminal'})
    def show(self):
        return json.dumps({'status':'deleted Terminal'})

class VirtualRouter(object):
    def __init__(self, vrObject):
        self.vnc_client = vnc_api.VncApi(
            username = admin_user,
            password = admin_password,
            tenant_name = admin_tenant,
            api_server_host=api_server,
            api_server_port=api_port,
            auth_host=api_server)
        self.vrObject = vrObject
        print self.vrObject

    def getPhysicalInterface(self,virtualRouter, interfaceName):
        phIntList = self.vnc_client.physical_interfaces_list()['physical-interfaces']
        for phInt in phIntList:
            if phInt['fq_name'][1] == virtualRouter and phInt['fq_name'][2] == interfaceName:
                phIntObjUUID = phInt['uuid']
        phIntObj = self.vnc_client.physical_interface_read(id = phIntObjUUID)
        return phIntObj

    def getVirtualRouter(self,vrName):
        virtualRouter = self.vnc_client.virtual_router_read(fq_name = ['default-global-system-config',vrName])
        return virtualRouter

    def getPhysicalRouter(self,vrName):
        physicalRouter = self.vnc_client.physical_router_read(fq_name = ['default-global-system-config',vrName])
        return physicalRouter
    def create(self):
        fileList = []
        vsList = []
        interfaceList = []
        vs_eth1 = { 'interfaceName': 'eth1_' + self.vrObject['name'] , 'switchName' : "vs-" + self.vrObject['protocolprocessor'] }
        vsList.append(vs_eth1)
        cidrIp = IPNetwork(self.vrObject['ipaddress'] + '/' + self.vrObject['mgmtNetmask'])
        cidrIp = str(cidrIp)
        vrouterAgentString = """[CONTROL-NODE]
[CONTROL-NODE]
server=""" + api_server + """
[DEFAULT]
gateway_mode = server
log_file=/var/log/contrail/contrail-vrouter-agent.log
log_level=SYS_NOTICE
log_local=1
[DNS]
[FLOWS]
[METADATA]
[NETWORKS]
control_network_ip=""" + self.vrObject['ipaddress'] + """
[VIRTUAL-HOST-INTERFACE]
name=vhost0
ip=""" + cidrIp + """
gateway=""" + self.vrObject['mgmtGateway'] + """
physical_interface=ens3
compute_node_address = """ + self.vrObject['ipaddress'] + """
[GATEWAY-0]
[GATEWAY-1]
[SERVICE-INSTANCE]
netns_command=/usr/bin/opencontrail-vrouter-netns
docker_command=/usr/bin/opencontrail-vrouter-docker"""
        f = open('/tmp/' + self.vrObject['name'] + '_vrouter_agent', 'w+')
        f.write(vrouterAgentString)
        f.close()
        vrouterAgentDictFile = { 'src' : '/tmp/' + self.vrObject['name'] + '_vrouter_agent', 'dst' : '/etc/contrail/contrail-vrouter-agent.conf' }
        fileList.append(vrouterAgentDictFile)
        vrScriptDict = { 'src' : scriptDirectory + '/VirtualRouters/addPhysicalInterface.py', 'dst' : '/addPhysicalInterface.py' }
        fileList.append(vrScriptDict)
        intEth0 = { 'name':'ens3','Type':'vhost','Mtu':'9000','mac': randomMAC()}
        intEth1 = { 'name':'ens4', 'Type':'l2' ,'Mtu':'9000'}
        intVhost0 = { 'name':'vhost0','ipaddress':self.vrObject['ipaddress'],'dns':self.vrObject['mgmtDns'],'netmask':self.vrObject['mgmtNetmask'],'gateway':self.vrObject['mgmtGateway'],'Type':'vhost', 'Mtu':'9000'}
        interfaceList.append(intEth0)
        interfaceList.append(intEth1)
        interfaceList.append(intVhost0)
        createImage(self.vrObject['name'], 'VirtualRouters', fileList, interfaceList, vsList=vsList)
        return json.dumps({'status':'created Virtual Router'})
    def delete(self):
        '''
        try:
            phInt = self.getPhysicalInterface(self.vrObject['name'],'ens4')
        except:
            print 'cannot get physical interface'
        try:
            lifList =  phInt.get_logical_interfaces()
            if lifList:
                for lif in lifList:
                    try:
                        self.vnc_client.logical_interface_delete(id = lif['uuid'])
                    except:
                        print 'cannot delete lif'
        except:
            print 'cannot get lif'
        try:
            self.vnc_client.physical_interface_delete(id=phInt.get_uuid())
        except:
            print 'cannot delete physical interface'
        try:
            phRouter = self.getPhysicalRouter(self.vrObject['name'])
        except:
            print 'cannot get physical router'
        try:
            self.vnc_client.physical_router_delete(id=phRouter.get_uuid())
        except:
            print 'cannot delete physical router'
        try:
            virtualRouter = self.getVirtualRouter(self.vrObject['name'])
        except:
            print 'cannot get virtual router'
        try:
            self.vnc_client.virtual_router_delete(id=virtualRouter.get_uuid())
        except:
            print 'cannot delete virtual router'
        destroyImage(self.vrObject['name'], 'VirtualRouters')
        subprocess.call(["ovs-vsctl", "del-br", "vs-" + self.vrObject['name']])
        '''
        return json.dumps({'status':'deleted Virtual Router'})
    def show(self):
        return json.dumps({'status':'deleted Virtual Router'})

class ProtocolProcessor(object):
    def __init__(self, ppObject):
        self.ppObject = ppObject
    def create(self):
        fileList = []
        vsList = []
        interfaceList = []
        intEth0 = { 'name':'ens3','ipaddress':self.ppObject['ipaddress'],'dns':self.ppObject['mgmtDns'],'netmask':self.ppObject['mgmtNetmask'],'gatweway':self.ppObject['mgmtGateway'], 'Type':'l3'}
        intEth1 = { 'name':'ens4','ipaddress':self.ppObject['vxlanip'],'netmask':self.ppObject['vxlanNetmask'], 'Type':'l3','Mtu':'9000'}
        intEth2 = { 'name':'ens5', 'Bridge':'br0', 'Type':'l2','Mtu':'9000'}
        intBr0 = { 'name':'br0','Type':'ovs','Ports': ['ens5']}
        interfaceList.append(intEth0)
        interfaceList.append(intEth1)
        interfaceList.append(intEth2)
        interfaceList.append(intBr0)
        ppServerFileDict = { 'src' : scriptDirectory + '/ProtocolProcessors/ppServer.py', 'dst' : '/ppServer.py' }
        fileList.append(ppServerFileDict)
        ppServerFileDict2 = { 'src' : scriptDirectory + '/ProtocolProcessors/addLif.py', 'dst' : '/addLif.py' }
        fileList.append(ppServerFileDict2)
        ppServerFileDict3 = { 'src' : scriptDirectory + '/ProtocolProcessors/addLifClient.py', 'dst' : '/addLifClient.py' }
        fileList.append(ppServerFileDict3)
        ppServerFileDict4 = { 'src' : scriptDirectory + '/ProtocolProcessors/dhcpscript.sh', 'dst' : '/dhcpscript.sh' }
        fileList.append(ppServerFileDict4)
        vs_eth1 = { 'interfaceName': 'eth1_' + self.ppObject['name'] , 'switchName' : "br0" }
        vs_eth2 = { 'interfaceName': 'eth2_' + self.ppObject['name'] , 'switchName' : "vs-" + self.ppObject['name'] }
        vsList.append(vs_eth1)
        vsList.append(vs_eth2)
        fstabString = 'LABEL=cloudimg-rootfs	/	 ext4	defaults	0 0\n'
        fstabString += nfsServer + ':/home/lease /mnt nfs rw 0 0\n'
        f = open('/tmp/'+self.ppObject['name']+'_fstab', 'w')
        f.write(fstabString)
        f.close()
        fstabDict = { 'src':'/tmp/'+self.ppObject['name']+'_fstab','dst':'/etc/fstab' }
        fileList.append(fstabDict)
        subprocess.call(["ovs-vsctl", "del-br", "vs-" + self.ppObject['name']])
        subprocess.call(["ovs-vsctl", "add-br", "vs-" + self.ppObject['name']])
        virshNetXml = '<network>\n'
        virshNetXml += '<name>vs-%s</name>\n' % self.ppObject['name']
        virshNetXml += '<forward mode=\'bridge\'/>\n'
        virshNetXml += '<bridge name=\'vs-%s\'/>\n' % self.ppObject['name']
        virshNetXml += '<virtualport type=\'openvswitch\'/>\n'
        virshNetXml += '</network>'
        conn = libvirt.open('qemu:///system')
        network = conn.networkDefineXML(virshNetXml)
        network.create()
        network.isActive()
        network.setAutostart(True)
        createImage(self.ppObject['name'], 'ProtocolProcessors', fileList, interfaceList, vsList=vsList)
        return json.dumps({'status':'created Protocol Processor'})
    def delete(self):
        destroyImage(self.ppObject['name'], 'ProtocolProcessors')
        subprocess.call(["/usr/bin/virsh","net-destroy","vs-%s" % self.ppObject['name']])
        subprocess.call(["/usr/bin/virsh","net-undefine","vs-%s" % self.ppObject['name']])
        return json.dumps({'status':'deleted Protocol Processor'})
    def show(self):
        return json.dumps({'status':'deleted Terminal'})

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print 'interface missing'
        sys.exit()
    HOST = get_ip_address(sys.argv[1])
    PORT = 6666
    server_address = ('192.168.1.1', PORT)
    httpd = HTTPServer(server_address, Handler)
    print "Serving at: http://%s:%s" % ('192.168.1.1', PORT)
    httpd.serve_forever()
