#!/usr/bin/python
import sys
from jnpr.junos import Device
from jnpr.junos.utils.config import Config

mmpList = [{'mmp1':'192.168.1.11'},{'mmp2':'192.168.1.12'}]
serviceList = ['svc1','svc2','svc3']
sasList = [{'sas1':'192.168.1.130','sas2':'192.168.1.131'}]
creds = {'user':'root','password':'contrail123'}
if len(sys.argv) < 3:
    print 'missing args'
    sys.exit()
mmp = str(sys.argv[2])
sas = str(sys.argv[1])

nonpreferredDeviceList = []
for mmpItem in mmpList:
    if mmpItem.keys()[0] == mmp:
        preferredDevice = mmpItem.values()[0]
    else:
        nonpreferredDeviceList.append(mmpItem.values()[0])
preferredSvcList = []
for svcItem in range(3, len(sys.argv)):
    preferredSvcList.append(sys.argv[svcItem])
print 'sas: %s, mmp: %s, svc: %s' % (sas, mmp, preferredSvcList)
print preferredDevice
print nonpreferredDeviceList
print creds['user']
dev = Device(host=preferredDevice, user=creds['user'], password=creds['password'])
dev.open()
for sasItem in sasList:
    if sasItem.keys()[0] == sas:
        sasPeer = sasItem.values()[0]
for prefSvc in preferredSvcList:
    print 'device %s' % preferredDevice
    varPolicy = "set policy-options policy-statement " + sas + "_" + prefSvc +"_to_var term " + prefSvc + " then metric 10"
    sasPolicy = "set policy-options policy-statement " + sas + "_" + prefSvc +"_to_sas term " + prefSvc + " then local-preference 110"
    print varPolicy
    print sasPolicy
    cfg = Config(dev)
    cfg.lock()
    cfg.load(varPolicy, format="set", merge=True)
    cfg.load(sasPolicy, format="set", merge=True)
cfg.commit()
cfg.unlock()
dev.close()


    

for nonprefDev in nonpreferredDeviceList:
    print 'device %s' % nonprefDev
    dev = Device(host=nonprefDev, user=creds['user'], password=creds['password'])
    dev.open()
    cfg = Config(dev)
    cfg.lock()
    for prefSvc in preferredSvcList:
        varPolicy = "set policy-options policy-statement " + sas + "_" + prefSvc +"_to_var term " + prefSvc + " then metric 20"
        sasPolicy = "set policy-options policy-statement " + sas + "_" + prefSvc +"_to_sas term " + prefSvc + " then local-preference 100"
        print varPolicy
        print sasPolicy
        cfg.load(varPolicy, format="set", merge=True)
        cfg.load(sasPolicy, format="set", merge=True)
    cfg.commit()
    cfg.unlock()
    dev.close()
