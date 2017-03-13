#!/usr/bin/python
import argparse
import time
import subprocess
import json
import os.path
import os
import socket
import fcntl
import struct
import uuid
import signal
import sys
from vnc_api import vnc_api
from pyroute2 import netns
from pyroute2 import NetNS
from pyroute2 import IPDB
from pyroute2 import NSPopen
from pprint import pprint
from netaddr import *
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

api_server='192.168.1.130'
api_port='8082'
admin_user = 'admin'
admin_password = 'contrail123'
admin_tenant = 'admin'
serviceInterface = 'ens4'
vnc_client = vnc_api.VncApi(
            username = admin_user,
            password = admin_password,
            tenant_name = admin_tenant,
            api_server_host=api_server,
            api_server_port=api_port,
            auth_host=api_server)

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
            result = createService(data)
            self.request.sendall(result)
        if self.path == '/deleteService':
            print data
            result = deleteService(data)
            self.request.sendall(result)
        if self.path == '/createTerminal':
            print data
            result = createTerminal(data)
            self.request.sendall(result)
        if self.path == '/deleteTerminal':
            print data
            result = deleteTerminal(data)
            self.request.sendall(result)
        if self.path == '/moveTerminal':
            print data
            result = moveTerminal(data)
            self.request.sendall(result)

def createVirtualNetwork(tenant, vnName, v4subnet, rt, mode, isid):
    project = vnc_client.project_read(fq_name_str = 'default-domain:' + tenant)
    vn = vnc_api.VirtualNetwork(name = vnName,
                    parent_obj = project)
    ipam_obj = vnc_client.network_ipam_read(fq_name = ['default-domain',
                                           'default-project', 'default-network-ipam'])
    cidr = v4subnet.split('/')
    subnet = vnc_api.SubnetType(ip_prefix = cidr[0],
                ip_prefix_len = int(cidr[1]))
    v4DnsServer = str(IPNetwork(v4subnet)[+2])
    v4gateway = str(IPNetwork(v4subnet)[+1])
    ipam_subnet = vnc_api.IpamSubnetType(subnet = subnet, dns_server_address = v4DnsServer,
                default_gateway = v4gateway, enable_dhcp = False)
    vn.add_network_ipam(ref_obj = ipam_obj,
                 ref_data = vnc_api.VnSubnetsType([ipam_subnet]))
    rtObj = vnc_api.RouteTargetList()
    vn.set_route_target_list(rtObj)
    rtObj.add_route_target('target:%s' %(rt))
    vnc_client.virtual_network_create(vn)
    vnObj = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    if mode == 'l2':
        isidName = 'isid' + str(isid)
        bd=vnc_api.BridgeDomain(name=isidName,mac_learning_enabled=True,isid=isid,parent_obj=vnObj)
        vnc_client.bridge_domain_create(bd)
        vnObj.set_layer2_control_word(True)
        vnObj.set_flood_unknown_unicast(True)
        vnObj.set_mac_learning_enabled(True)
        vnObj.set_pbb_evpn_enable(True)
        vnc_client.virtual_network_update(vnObj)
    return vnObj

def getVirtualNetwork(tenant, vnName):
    vn = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    return vn

def deleteVirtualNetwork(tenant, vnName):
    vn = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    vnc_client.virtual_network_delete(id = vn.uuid)

def getPhysicalInterface(virtualRouter, interfaceName):
    phIntList = vnc_client.physical_interfaces_list()['physical-interfaces']
    print 'phint list: %s' % phIntList
    for phInt in phIntList:
        if phInt['fq_name'][1] == virtualRouter and phInt['fq_name'][2] == interfaceName:
            phIntObjUUID = phInt['uuid']
    phIntObj = vnc_client.physical_interface_read(id = phIntObjUUID)
    return phIntObj

def createInstanceIp(ip, vmInterface, vn):
    instIpUUID = str(uuid.uuid4())
    ipInst = vnc_api.InstanceIp(name = instIpUUID, instance_ip_address = ip)
    ipInst.set_virtual_machine_interface(vmInterface)
    ipInst.set_virtual_network(vn)
    vnc_client.instance_ip_create(ipInst)

def createLogicalInterface(physicalInterface, serviceInterface, serviceVid):
    lif = vnc_api.LogicalInterface(name = serviceInterface, parent_obj = physicalInterface, logical_interface_vlan_tag = int(serviceVid), logical_interface_type = 'l2')
    lifResult = vnc_client.logical_interface_create(lif)
    lif = vnc_client.logical_interface_read(id=lifResult)
    return lif

def getLogicalInterface(vrName, interface):
    lifList = vnc_client.logical_interfaces_list()['logical-interfaces'] 
    if lifList:
        for lif in lifList:
            print lif
            if lif['fq_name'][1] == vrName and lif['fq_name'][3] == interface:
                lifObj = vnc_client.logical_interface_read(id = lif['uuid'])
                return lifObj

def createVirtualMachineInterface(tenant, vnName, sVid, cvlan=None):
    project = vnc_client.project_read(fq_name_str = 'default-domain:' + tenant)
    vn = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    bd = vn.get_bridge_domains()
    instIpUUID = str(uuid.uuid4())
    ipInst = vnc_api.InstanceIp(name = instIpUUID)
    if bd:
        p_vmIntUUID = str(uuid.uuid4())
        s_vmIntUUID = str(uuid.uuid4())
        p_vmIntObj = vnc_api.VirtualMachineInterface(name = p_vmIntUUID, parent_obj = project)
        p_vmIntObj.set_virtual_network(vn)
        p_vmIntObjResult = vnc_client.virtual_machine_interface_create(p_vmIntObj)
        p_vmIntObj = vnc_client.virtual_machine_interface_read(id = p_vmIntObjResult)
        s_vmIntObj = vnc_api.VirtualMachineInterface(name = s_vmIntUUID, parent_obj = project)
        s_vmIntObj.set_virtual_network(vn)
        s_vmIntObj.set_virtual_machine_interface(p_vmIntObj)
        bridge_domain = vnc_client.bridge_domain_read(id=bd[0]['uuid'])
        bmem=vnc_api.BridgeDomainMembershipType(vlan_tag=0)
        s_vmIntObj.add_bridge_domain(bridge_domain,bmem)
        s_vmIntObj.set_virtual_machine_interface_disable_policy(True)
        if cvlan:
            s_vmIntObj.set_virtual_machine_interface_properties({'sub_interface_vlan_tag':cvlan})
        try:
            vmIntObjResult = vnc_client.virtual_machine_interface_create(s_vmIntObj)
        except:
            print 'cannot create vmi'
    else:
        vmIntUUID = str(uuid.uuid4())
        vmIntObj = vnc_api.VirtualMachineInterface(name = vmIntUUID, parent_obj = project)
        vmIntObj.set_virtual_network(vn)
        vmIntObjResult = vnc_client.virtual_machine_interface_create(vmIntObj)
        try:
            vmIntObjResult = vnc_client.virtual_machine_interface_create(vmIntObj)
        except:
            print 'cannot create vmi'
    vmIntObj = vnc_client.virtual_machine_interface_read(id = vmIntObjResult)
    #if not bd:
    ipInst.set_virtual_machine_interface(vmIntObj)
    ipInst.set_virtual_network(vn)
    vnc_client.instance_ip_create(ipInst)
    return vmIntObj

def createTerminal(terminal):
    result = subprocess.call(['ovs-vsctl', 'add-port', 'br0', terminal['name'], '--', 'set', 'interface', terminal['name'], 'type=vxlan', 'options:remote_ip='+terminal['vxlanip']])
    return json.dumps({ 'status' : 'created service'})

def deleteTerminal(terminal):
    result = subprocess.call(['ovs-vsctl', 'del-port', 'br0', terminal['name']])
    return json.dumps({ 'status' : 'created service'})

def createDhcpConfig(name, network, vr, customer, svcId):
    nw = IPNetwork(network)
    start = str(nw.network + 3)
    end = str(nw.broadcast - 1)
    gw = str(nw.network + 1)
    dns = str(nw.network + 1)
    mask = str(nw.netmask)
    dhcpConfig = 'interface=' + name + '_' + svcId + '_v\n'
    dhcpConfig += 'dhcp-range=set:' + name + '__' + vr + '__' + customer + '__' + svcId + ',' + start + ',' + end + ',' + mask + ',infinite\n'
    dhcpConfig += 'dhcp-option=tag:' + name + '__' + vr + '__' + customer + '__' + svcId +',3,' + gw + '\n'
    dhcpConfig += 'dhcp-option=tag:' + name + '__' + vr + '__' + customer + '__' + svcId + ',6,' + dns + '\n'
    dhcpConfig += 'dhcp-leasefile=/mnt/' + name + '.lease' + '\n'
    dhcpConfig += 'dhcp-script=/dhcpscript.sh\n'
    f = open('/etc/dnsmasq.d/' + name + '.conf', 'w')
    f.write(dhcpConfig)
    f.close()

#def createService(name, svcId, ip, network, customer, routetarget, vr):
def createService(data):
    print data
    name = data['name']
    svcId = data['Id']
    svcIdString = str(data['Id'])
    ip = data['dhcpip']
    network = data['subnet']
    customer = data['customer']
    routetarget = data['routetarget']
    terminal = data['terminal']
    vr = data['virtualrouter']
    mode = data['mode']
    if data['cvlan'] != '0':
        cvlan = data['cvlan']
        isid = 1000 + int(cvlan)
    else:
        cvlan = None
        isid = 0
    if 'move' in data:
        move = data['move']
        oldvr = data['oldvr']
        oldId = data['oldId']
    else:
        move = False
    if 'add' in data:
        add = data['add']
    else:
        add = False
    print name
    print '############ mode: %s #########' % mode
    if mode != 'l2':
        print '############ mode: %s #########' % mode
        if_svc_name = name + '_' + svcIdString
        if_svc_peer_name = name + '_' + svcIdString + '_v'
        ip_ns = IPDB(nl=NetNS(name + '_' + svcIdString))
        ip_host = IPDB()
        ip_host.create(ifname=if_svc_name, kind='veth', peer=if_svc_peer_name).commit()
        subprocess.call(["ovs-vsctl", "add-port", "br0", if_svc_name])
        subprocess.call(["ovs-vsctl", "set", "port", if_svc_name, "tag=" + str(svcId)])
        netmask = network.split('/')[1]
        ip = ip + '/' + netmask
        createDhcpConfig(name, network, vr, customer, svcIdString)
        with ip_host.interfaces[if_svc_name] as veth:
            veth.up()
        with ip_host.interfaces[if_svc_peer_name] as veth:
            veth.net_ns_fd = name + '_' + svcIdString
        with ip_ns.interfaces[if_svc_peer_name] as veth:
            veth.address = 'de:ad:be:ef:ba:be'
            veth.add_ip(ip)
            veth.up()
        ip_host.release()
        ip_ns.release()
        nsp = NSPopen(name + '_' + svcIdString, ['dnsmasq', '-C', '/etc/dnsmasq.d/' + name + '.conf'], stdout=subprocess.PIPE)
        nsp.wait()
        nsp.release()
    if not move or add:
        try:
            vn = createVirtualNetwork(customer, name, network, routetarget, mode, isid)
        except:
            print 'failed to create VN'
    phInt = getPhysicalInterface(vr, serviceInterface)
    lif = vnc_client.logical_interface_read(fq_name=['default-global-system-config',vr,serviceInterface,'lif_' + str(svcId)])
    if not move:
        if cvlan:
            vmInterface = createVirtualMachineInterface(customer, name, str(svcId), cvlan)
        else:
            vmInterface = createVirtualMachineInterface(customer, name, str(svcId))
    #lif = createLogicalInterface(phInt, name + '_' + svcIdString, str(svcId))
        lif.add_virtual_machine_interface(vmInterface)
        vnc_client.logical_interface_update(lif)
    if move:
        oldlif = getLogicalInterface(oldvr, 'lif_' + str(oldId))
        if oldlif.get_virtual_machine_interface_refs():
            for vmInt in oldlif.get_virtual_machine_interface_refs():
                vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
                oldlif.del_virtual_machine_interface(vmIntObj)
                lif.add_virtual_machine_interface(vmIntObj)
                vnc_client.logical_interface_update(oldlif)
                vnc_client.logical_interface_update(lif)
    return json.dumps({ 'status' : 'created service'})

def deleteService(data):
    bd = False
    name = data['name']
    customer = data['customer']
    vr = data['virtualrouter']
    svcId = data['Id']
    if 'move' in data:
        move = data['move']
    else:
        move = False
    if 'delvn' in data:
        delvn = data['delvn']
    else:
        delvn = False
    print vr
    print name + '_' + str(svcId)
    lif = getLogicalInterface(vr, 'lif_' + str(svcId))
    if lif.get_virtual_machine_interface_refs() and not move:
        for vmInt in lif.get_virtual_machine_interface_refs():
            vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
            if vmIntObj.get_instance_ip_back_refs():
                for instIp in vmIntObj.get_instance_ip_back_refs():
                    instIpObj = vnc_client.instance_ip_read(id = instIp['uuid'])
                    vnc_client.instance_ip_delete(id = instIp['uuid'])
            if vmIntObj.get_logical_interface_back_refs():
                for logicalInterface in vmIntObj.get_logical_interface_back_refs():
                    logInt = vnc_client.logical_interface_read(id = logicalInterface['uuid'])
                logInt.del_virtual_machine_interface(vmIntObj)
                vnc_client.logical_interface_update(logInt)
            if vmIntObj.get_virtual_machine_interface_refs():
                for parentVmi in vmIntObj.get_virtual_machine_interface_refs():
                    p_vmIntObj = vnc_client.virtual_machine_interface_read(id=parentVmi['uuid'])
            vnc_client.virtual_machine_interface_delete(id = vmIntObj.get_uuid())
            vnc_client.virtual_machine_interface_delete(id = p_vmIntObj.get_uuid())

    if lif.get_virtual_machine_interface_refs() and move:
        for vmInt in lif.get_virtual_machine_interface_refs():
            vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
            if vmIntObj.get_logical_interface_back_refs():
                for logicalInterface in vmIntObj.get_logical_interface_back_refs():
                    logInt = vnc_client.logical_interface_read(id = logicalInterface['uuid'])
                logInt.del_virtual_machine_interface(vmIntObj)
                vnc_client.logical_interface_update(logInt)
    
    #vnc_client.logical_interface_delete(id = lif.get_uuid())
    vn = getVirtualNetwork(customer, name)
    bd = vn.get_bridge_domains()
    if not move:
        if delvn:
            if bd:
                vnc_client.bridge_domain_delete(id=bd[0]['uuid'])
            vnc_client.virtual_network_delete(id = vn.get_uuid())
    p = subprocess.Popen(['ip','netns','pids',name + '_' + str(svcId)], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for line in out.splitlines():
        print line
        pid = int(line)
        try:
            os.kill(pid, signal.SIGKILL) 
        except:
            print 'nothing to kill'
    if not bd:
        netns.remove(name + '_' + str(svcId))
    subprocess.call(['ip','link','del','dev',name + '_' + str(svcId)])
    #time.sleep(3)
    #ip_host = IPDB()
    #if name + '_' + str(svcId) in ip_host.interfaces:
    #    with ip_host.interfaces[name + '_' + str(svcId)] as veth:
    #        veth.remove()
    subprocess.call(["ovs-vsctl", "del-port", "br0", name + '_' + str(svcId)])
    if not move:
        if delvn and not bd:
            os.remove('/mnt/' + name + '.lease')
    return json.dumps({ 'status' : 'deleted service'})

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

HOST = get_ip_address('ens3')
PORT = 6666

if __name__ == "__main__":
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, Handler)
    print "Serving at: http://%s:%s" % (HOST, PORT)
    httpd.serve_forever()
