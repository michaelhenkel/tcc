#!/usr/bin/python
import socket
import os, os.path
import time
import uuid
import sys
from vnc_api import vnc_api
api_server='192.168.1.130'
api_port='8082'
admin_user = 'admin'
admin_password = 'contrail123'
admin_tenant = 'admin'
vnc_client = vnc_api.VncApi(
            username = admin_user,
            password = admin_password,
            tenant_name = admin_tenant,
            api_server_host=api_server,
            auth_host = api_server,
            api_server_port=api_port)

if os.path.exists( "/tmp/addlif.socket" ):
    os.remove( "/tmp/addlif.socket" )

server = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
server.bind("/tmp/addlif.socket")

def createVirtualMachineInterface(tenant, vnName, mac=None, bd=None):
    project = vnc_client.project_read(fq_name_str = 'default-domain:' + tenant)
    vn = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    #vmIntMac = { 'mac_address' : [ mac ] }
    vmIntUUID = str(uuid.uuid4())
    #vmIntObj = vnc_api.VirtualMachineInterface(name = vmIntUUID, parent_obj = project, virtual_machine_interface_mac_addresses = vmIntMac)
    vmIntObj = vnc_api.VirtualMachineInterface(name = vmIntUUID, parent_obj = project)
    vmIntObj.set_virtual_network(vn)
    if bd:
        bridge_domain = vnc_client.bridge_domain_read(id=bd[0]['uuid'])
        bmem=vnc_api.BridgeDomainMembershipType(vlan_tag=0)
        vmIntObj.add_bridge_domain(bridge_domain,bmem)
        vmIntObj.set_virtual_machine_interface_disable_policy(True)
    print vn.get_uuid()
    try:
        vmIntObjResult = vnc_client.virtual_machine_interface_create(vmIntObj)
    except:
        print 'cannot create vmi'
    vmIntObj = vnc_client.virtual_machine_interface_read(id = vmIntObjResult)
    return vmIntObj

def createInstanceIp(ip, vmInterface, vn):
    instIpUUID = str(uuid.uuid4())
    ipInst = vnc_api.InstanceIp(name = instIpUUID, instance_ip_address = ip)
    ipInst.set_virtual_machine_interface(vmInterface)
    ipInst.set_virtual_network(vn)
    try:
        vnc_client.instance_ip_create(ipInst)
    except:
        print 'cannot create instance ip'

def getVirtualNetwork(tenant, vnName):
    vn = vnc_client.virtual_network_read(fq_name_str = 'default-domain:' + tenant + ':' + vnName)
    return vn

def getPhysicalInterface(virtualRouter, interfaceName='ens4'):
    phIntList = vnc_client.physical_interfaces_list()['physical-interfaces']
    for phInt in phIntList:
        if phInt['fq_name'][1] == virtualRouter and phInt['fq_name'][2] == interfaceName:
            phIntObjUUID = phInt['uuid']
    phIntObj = vnc_client.physical_interface_read(id = phIntObjUUID)
    return phIntObj

def getLogicalInterface(physicalInterface, interface):
    lifList =  physicalInterface.get_logical_interfaces()
    if lifList:
        for lif in lifList:
            print lif
            if lif['to'][3] == interface:
                lifObj = vnc_client.logical_interface_read(id = lif['uuid'])
                return lifObj

def getVirtualMachineInterface(mac):
    vmIntList = vnc_client.virtual_machine_interfaces_list()['virtual-machine-interfaces']
    for vmInt in vmIntList:
        print vmInt
        vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
        intMac = vmIntObj.get_virtual_machine_interface_mac_addresses().get_mac_address()[0]
        if intMac == mac:
            return vmIntObj

def getAllowedAddressPair(mac, ip):
    vmIntList = vnc_client.virtual_machine_interfaces_list()['virtual-machine-interfaces']
    for vmInt in vmIntList:
        vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
        if vmIntObj.get_virtual_machine_interface_allowed_address_pairs():
            allowedAddressPairs = vmIntObj.get_virtual_machine_interface_allowed_address_pairs()
            if allowedAddressPairs.get_allowed_address_pair():
                allowedAddressPair = allowedAddressPairs.get_allowed_address_pair()
                for ap in allowedAddressPair:
                    if ap.get_mac() == mac and ap.get_ip().ip_prefix == ip:
                        return [vmIntObj, allowedAddressPairs, ap]

def actionLif(data):
    args = data.split(' ')
    oper = args[0]
    mac = args[1]
    ip = args[2]
    terminal = args[3]
    if oper == 'add':
        already_exists = False
        lif_has_vmi = False
        allowed_address_pair_exists = False
        allowed_address_pairs_exists = False
        vmi_created = False
        svc_lif = args[4]
        print svc_lif
        vnName = svc_lif.split('__')[0]
        vr = svc_lif.split('__')[1]
        tenant = svc_lif.split('__')[2]
        svcId = svc_lif.split('__')[3]
        vn = getVirtualNetwork(tenant, vnName)
        bd = vn.get_bridge_domains()
        physicalInterface = getPhysicalInterface(vr)
        logicalInterface = getLogicalInterface(physicalInterface, vnName + '_' + svcId)
        if logicalInterface.get_virtual_machine_interface_refs():
            for vmInt in logicalInterface.get_virtual_machine_interface_refs():
                vmIntObj = vnc_client.virtual_machine_interface_read(id = vmInt['uuid'])
                if vmIntObj.get_virtual_machine_interface_allowed_address_pairs():
                    allowed_address_pairs_exists = True
                    allowedAddressPairs = vmIntObj.get_virtual_machine_interface_allowed_address_pairs()
                    if allowedAddressPairs.get_allowed_address_pair():
                        allowedAddressPair = allowedAddressPairs.get_allowed_address_pair()
                        for ap in allowedAddressPair:
                            if ap.get_mac() == mac and ap.get_ip().ip_prefix == ip:
                                allowed_address_pair_exists = True
        if not allowed_address_pair_exists:
            if not allowed_address_pairs_exists:
                allowedAddressPairs = vnc_api.AllowedAddressPairs()
            ip = {'ip_prefix':ip,'ip_prefix_len':32}
            addrPair = vnc_api.AllowedAddressPair(ip=ip, mac=mac, address_mode='active-standby')
            allowedAddressPairs.add_allowed_address_pair(addrPair)
            vmIntObj.set_virtual_machine_interface_allowed_address_pairs(allowedAddressPairs)
            vnc_client.virtual_machine_interface_update(vmIntObj)
                 
    if oper == 'del':
        allowedApList = getAllowedAddressPair(mac, ip) 
        if allowedApList:
            vmIntObj = allowedApList[0]
            allowedAddressPairs = allowedApList[1]
            ap = allowedApList[2]
            allowedAddressPairs.delete_allowed_address_pair(ap)
            vmIntObj.set_virtual_machine_interface_allowed_address_pairs(allowedAddressPairs)
            vnc_client.virtual_machine_interface_update(vmIntObj)

while True:
    try:
        datagram = server.recv( 1024 )
        if not datagram:
            break
        else:
            print "-" * 20
            print datagram
            actionLif(datagram)
    except KeyboardInterrupt, k:
        print 'shutting down'
        server.close()
        os.remove( "/tmp/addlif.socket" )
        print "Done"
