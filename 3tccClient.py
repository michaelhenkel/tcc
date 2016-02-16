#!/usr/bin/python
import types
import copy
import yaml
import socket
import fcntl
import struct
import json
import socket
import sys
import argparse
import collections
import subprocess
import ruamel.yaml
import httplib, urllib2
import inspect
from netaddr import *
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq
from pprint import pprint

def parse_extra (parser, namespace):
  namespaces = []
  extra = namespace.extra
  while extra:
    n = parser.parse_args(extra)
    extra = n.extra
    namespaces.append(n)
  return namespaces

argparser=argparse.ArgumentParser()
subparsers = argparser.add_subparsers(help='sub-command help', dest='subparser_name')

create_parser = subparsers.add_parser('create', help = "create help")
create_parser.add_argument('type')
create_parser.add_argument('-n','--name')
create_parser.add_argument('-t','--terminal')
create_parser.add_argument('-sn','--subnet')
create_parser.add_argument('-ip','--ipaddress')
create_parser.add_argument('-vip','--vxlanip')
create_parser.add_argument('-pp','--protocolprocessor')
create_parser.add_argument('-svc','--service')
create_parser.add_argument('-cust','--customer')
create_parser.add_argument('-rt','--routetarget')
create_parser.add_argument('-host','--host')
create_parser.add_argument('-f','--yamlfile')
create_parser.add_argument('-vr','--virtualrouter')
create_parser.add_argument('-et','--endpointtype')

add_parser = subparsers.add_parser('add', help = "del help")
add_parser.add_argument('type')
add_parser.add_argument('-n','--name')
add_parser.add_argument('-t','--terminal')

del_parser = subparsers.add_parser('del', help = "del help")
del_parser.add_argument('type')
del_parser.add_argument('-n','--name')
del_parser.add_argument('-t','--terminal')

move_parser = subparsers.add_parser('move', help = "del help")
move_parser.add_argument('type')
move_parser.add_argument('-n','--name')
move_parser.add_argument('-pp','--protocolprocessor')

show_parser = subparsers.add_parser('show', help = "show help")
show_parser.add_argument('type')
show_parser.add_argument('-n','--name')

argparser.add_argument('extra', nargs = "*", help = 'Other commands')
args = argparser.parse_args()

class Tcc(object):
    def __init__(self, tccConfigObject):
        self.tccConfigObject = tccConfigObject
        if not self.tccConfigObject:
            self.tccConfigObject = CommentedMap([(None, None)])
        self.object_dict = {}
        for item in object_lookup.keys():
            self.generateObjects(item)
    def generateObjects(self, element):
        if element in self.tccConfigObject and isinstance(self.tccConfigObject[element],list):
            self.object_dict[element] = []
            for item in self.tccConfigObject[element]:
                class_object = object_lookup[element](item)
                del class_object.mandatoryAttributes
                self.object_dict[element].append(class_object)
    def list(self, element):
        if element in self.tccConfigObject:
            return self.object_dict[element]
        else:
            return 'no %s' % element
    def get(self, element, name):
        if not element in self.object_dict:
            return False
        if len(self.object_dict[element]) > 0:
            for item in self.object_dict[element]:
                if item.name == name:
                    return item
            return False
        else:
            return False
    def getByAttr(self, element, attribute, value):
        if element in self.object_dict:
            if len(self.object_dict[element]) > 0:
                for item in self.object_dict[element]:
                    if getattr(item, attribute) == value:
                        return item
                return False
            else:
                return False
        else:
            return False

class Elements(object):
    def __init__(self):
        self.elementType = self.__class__.__name__
        self.elementCategory = element_lookup[self.elementType.lower()]
    def show(self):
        return self.__dict__
    def check(self, args):
        check_lookup = {}
        for attribute in self.mandatoryAttributes:
            if not getattr(args, attribute):
                print attribute + ' is missing'
                return False
            if self.mandatoryAttributes[attribute] == 'ref':
                refElementCategory = element_lookup[attribute]
                if not tcc.get(refElementCategory,getattr(args, attribute)):
                    print 'reference object %s of category %s does not exist' % (getattr(args, attribute), refElementCategory)
                    return False
            check_lookup[attribute] = getattr(args, attribute)
        for k,v in check_lookup.items():
            if self.mandatoryAttributes[k] == 'unique':
                if tcc.getByAttr(self.elementCategory, k, v) and args.subparser_name != 'add':
                    element = tcc.getByAttr(self.elementCategory, k, v).name
                    print self.elementType + ' ' + element + ' already uses ' + k + ' ' + v
                    return False
        return self
    def delete(self, args, tccConfigObject):
        self.name = args.name
        element = tcc.get(self.elementCategory, args.name)
        print element.show()
        if hasattr(element, 'back_refs'):
            if len(element.back_refs) > 0:
                print 'cannot delete because back refs exist: %s' % element.back_refs
                return False
        delFunction = getattr(self, self.delMethod)
        result = delFunction()
        elemLen = 0
        for attribute in self.mandatoryAttributes:
            if self.mandatoryAttributes[attribute] == 'ref':
                refElementCategory = element_lookup[attribute]
                if isinstance(getattr(element, attribute),ruamel.yaml.comments.CommentedSeq):
                    for item in getattr(element, attribute):
                        for el in item:
                            if el == getattr(args, attribute):
                                refElement = tcc.get(refElementCategory,el)
                                itemCounter = getattr(element, attribute).index(item)
                                getattr(element, attribute).pop(itemCounter)
                    elemLen = len(getattr(element, attribute))
                    ref_back_refs = refElement.back_refs
                    refIndex = ref_back_refs.index(args.name)
                    ref_back_refs.pop(refIndex)
                    for elementObject in tccConfigObject[refElementCategory]:
                        if elementObject['name'] == refElement.name:
                            elementObject['back_refs'] = ref_back_refs
        if elemLen == 0:
            for attribute in self.mandatoryAttributes:
                if self.mandatoryAttributes[attribute] == 'ref':
                    refElementCategory = element_lookup[attribute]
                    if not isinstance(getattr(element, attribute),ruamel.yaml.comments.CommentedSeq):
                        refElement = tcc.get(refElementCategory,getattr(element, attribute))
                        ref_back_refs = refElement.back_refs
                        refIndex = ref_back_refs.index(args.name)
                        ref_back_refs.pop(refIndex)
                        for elementObject in tccConfigObject[refElementCategory]:
                            if elementObject['name'] == refElement.name:
                                elementObject['back_refs'] = ref_back_refs
        elementCounter = 0
        for element in tccConfigObject[self.elementCategory]:
            if element['name'] == args.name:
                if elemLen == 0:
                    tccConfigObject[self.elementCategory].pop(elementCounter)
                else:
                    tccConfigObject[self.elementCategory][elementCounter].update(element)
            elementCounter = elementCounter + 1
        if len(tccConfigObject[self.elementCategory]) == 0:
            tccConfigObject[self.elementCategory] = None
        self.updateYaml(tccConfigObject)
    def updateYaml(self, tccConfigObject):
        ruamel.yaml.dump(tccConfigObject, open(tccYaml, 'w'),Dumper=ruamel.yaml.RoundTripDumper)
        #print ruamel.yaml.dump(tccConfigObject,Dumper=ruamel.yaml.RoundTripDumper)
    def findFreeId(self, start, elem1, elem2, key1, key2):
        idList = []
        for element in tccConfigObject[elem2]:
            if element['name'] == key2:
                back_refs = element['back_refs']
        if len(back_refs) == 0:
            return start
        for back_refElement in back_refs:
            for element in tccConfigObject[elem1]:
                print tccConfigObject[elem1]
                if element['name'] == back_refElement:
                    print element['name']
                    idList.append(element['Id'])
        idList = sorted(idList)
        itemCounter = start
        print idList
        for item in idList:
            if itemCounter < item:
                print 'bla' + str(item)
                print 'bla2 ' + str(itemCounter)
                return itemCounter
            itemCounter = itemCounter + 1
        return itemCounter
    def findFreeSvcId(self, start, elem1, elem2, key1, key2):
        idList = []
        for element in tccConfigObject[elem2]:
            if element['name'] == key2:
                back_refs = element['back_refs']
        if len(back_refs) == 0:
            return start
        for back_refElement in back_refs:
            for element in tccConfigObject[elem1]:
                if element['name'] == back_refElement:
                    for term in element['terminal']:
                        print term
                        for te in term:
                            if te == key2:
                                print term[te]
                                idList.append(term[te])
                    #idList.append(element['Id'])
        idList = sorted(idList)
        itemCounter = start
        print idList
        for item in idList:
            if itemCounter < item:
                print 'bla' + str(item)
                print 'bla2 ' + str(itemCounter)
                return itemCounter
            itemCounter = itemCounter + 1
        return itemCounter
    def move(self, args, tccConfigObject):
        self.name = args.name
        moveFunction = getattr(self, self.moveMethod)
        result = moveFunction(tccConfigObject)
        #print ruamel.yaml.dump(result,Dumper=ruamel.yaml.RoundTripDumper)
        self.updateYaml(result)
        return self
    def add(self, args, tccConfigObject):
        service = tcc.get('Services',args.name)
        newTerminal = tcc.get('Terminals', args.terminal)
        protocolprocessor = tcc.get('ProtocolProcessors', newTerminal.protocolprocessor)
        args.customer = service.customer
        args.routetarget = service.routetarget
        args.subnet = service.subnet
        self.subnet = service.subnet
        self.terminal = args.terminal
        self.name = args.name
        result = self.check(args)
        addFunction = getattr(self, self.addMethod)
        result = addFunction()
        terminalDict = { self.terminal:self.Id }
        for attribute in self.mandatoryAttributes:
            setattr(self,attribute,getattr(args,attribute))
            if self.mandatoryAttributes[attribute] == 'ref':
                refElementCategory = element_lookup[attribute]
                refElement = tcc.get(refElementCategory,getattr(args, attribute))
                back_refs = refElement.back_refs
                back_ref_found = False
                for back_ref in back_refs:
                    if back_ref == args.name:
                        back_ref_found = True
                if not back_ref_found:
                    back_refs.append(args.name)
                    for element in tccConfigObject[refElementCategory]:
                        if element['name'] == refElement.name:
                            element['back_refs'] = back_refs
        for element in tccConfigObject[self.elementCategory]:
            if element['name'] == self.name:
                if not isinstance(element['terminal'], list):
                    element['terminal'] = []
                element['terminal'].append(terminalDict)
        print tccConfigObject[self.elementCategory]
        self.updateYaml(tccConfigObject)            
    def create(self, args, tccConfigObject):
        result = self.check(args)
        if not result:
            sys.exit()
        for attribute in self.mandatoryAttributes:
            setattr(self,attribute,getattr(args,attribute))
            if self.mandatoryAttributes[attribute] == 'ref':
                refElementCategory = element_lookup[attribute]
                refElement = tcc.get(refElementCategory,getattr(args, attribute))
                back_refs = refElement.back_refs
                back_refs.append(args.name)
                for element in tccConfigObject[refElementCategory]:
                    if element['name'] == refElement.name:
                        element['back_refs'] = back_refs
        if not tccConfigObject:
            tccConfigObject = CommentedMap([(self.elementCategory, None)])
        elif self.elementCategory not in tccConfigObject:
            tccConfigObject.update(CommentedMap([(self.elementCategory, None)]))
        if not tccConfigObject[self.elementCategory]:
            tccConfigObject[self.elementCategory] = []
        attributes = copy.deepcopy(self.mandatoryAttributes)
        for element in self.mandatoryAttributes:
            attributes[element] = getattr(self, element)
        if hasattr(self,'back_refs'):
            attributes['back_refs'] = self.back_refs
        del self.mandatoryAttributes

        self.mgmtNetmask = tccConfigObject['Network']['mgmt']['netmask']
        self.mgmtGateway = tccConfigObject['Network']['mgmt']['gateway']
        self.mgmtDns = tccConfigObject['Network']['mgmt']['dns']
        self.vxlanNetmask = tccConfigObject['Network']['vxlan']['netmask']
        createFunction = getattr(self, self.createMethod)
        result = createFunction()
        if 'Error' in result:
            print result['Error']
            return False
        if args.type == 'service':
            terminalDict = { attributes['terminal']:self.Id }
            attributes['terminal'] = []
            attributes['terminal'].append(terminalDict)
        else:
            if hasattr(self,'Id'):
                attributes['Id'] = self.Id
        tccConfigObject[self.elementCategory].append(attributes)
        self.updateYaml(tccConfigObject)
        return self

class Customer(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' )])
        self.back_refs = []
        self.createMethod = 'createCustomer'
        self.delMethod = 'delCustomer'
        if obj:
            if 'back_refs' in obj:
                self.back_refs = obj['back_refs']
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(Customer, self).__init__()
    def createCustomer(self):
        result = sendData(self.show(),host,port,'createCustomer')
        return result
    def delCustomer(self):
        result = sendData(self.show(),host,port,'deleteCustomer')
        return result

class VirtualRouter(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' ),
                                                 ( 'ipaddress', 'unique'),
                                                 ( 'host', None)])
        self.back_refs = []
        self.createMethod = 'createVirtualRouter'
        self.delMethod = 'delVirtualRouter'
        if obj:
            if 'back_refs' in obj:
                self.back_refs = obj['back_refs']
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(VirtualRouter, self).__init__()
    def createVirtualRouter(self):
        print self.host
        result = sendData(self.show(),self.host,port,'createVirtualRouter')
        return result
    def delVirtualRouter(self):
        virtualRouter = tcc.get('VirtualRouters',self.name)
        result = sendData(self.show(),virtualRouter.host,port,'deleteVirtualRouter')
        return result

class ProtocolProcessor(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' ),
                                                 ( 'ipaddress', 'unique'),
                                                 ( 'host', None),
                                                 ( 'vxlanip', 'unique'),
                                                 ( 'virtualrouter', 'ref')])
        self.back_refs = []
        self.createMethod = 'createProtocolProcessor'
        self.delMethod = 'delProtocolProcessor'
        if obj:
            if 'back_refs' in obj:
                self.back_refs = obj['back_refs']
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(ProtocolProcessor, self).__init__()
    def createProtocolProcessor(self):
        result = sendData(self.show(),self.host,port,'createProtocolProcessor')
        return result
    def delProtocolProcessor(self):
        protocolProcessor = tcc.get('ProtocolProcessors',self.name)
        result = sendData(self.show(),protocolProcessor.host,port,'deleteProtocolProcessor')
        return result

class Terminal(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' ),
                                                 ( 'ipaddress', 'unique'),
                                                 ( 'host', None),
                                                 ( 'vxlanip', 'unique'),
                                                 ( 'protocolprocessor', 'ref')])
        self.back_refs = []
        self.createMethod = 'createTerminal'
        self.delMethod = 'delTerminal'
        self.moveMethod = 'moveTerminal'
        self.Id = ''
        if obj:
            if 'back_refs' in obj:
                self.back_refs = obj['back_refs']
            self.Id = obj['Id']
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(Terminal, self).__init__()
    def createTerminal(self):
        protocolProcessor = tcc.get('ProtocolProcessors',self.protocolprocessor)
        protocolProcessorName = protocolProcessor.name
        protocolProcessorIp = protocolProcessor.ipaddress
        protocolProcessorHost = protocolProcessor.host
        self.protocolprocessorVxlanIp = protocolProcessor.vxlanip
        self.Id = self.findFreeId(1, 'Terminals', 'ProtocolProcessors', self.name, protocolProcessorName)
        result = sendData(self.show(),protocolProcessorIp,port,'createTerminal')
        result = sendData(self.show(),self.host,port,'createTerminal')
        return result
    def delTerminal(self):
        terminal = tcc.get('Terminals',self.name)
        protocolProcessor = tcc.get('ProtocolProcessors',terminal.protocolprocessor)
        protocolProcessorName = protocolProcessor.name
        protocolProcessorIp = protocolProcessor.ipaddress
        protocolProcessorHost = protocolProcessor.host
        self.protocolprocessorVxlanIp = protocolProcessor.vxlanip
        result = sendData(self.show(),protocolProcessorIp,port,'deleteTerminal')
        result = sendData(self.show(),terminal.host,port,'deleteTerminal')
        return result
    def moveTerminal(self, tccConfigObject):
        terminal = tcc.get('Terminals',self.name)
        currentProtocolprocessor = tcc.get('ProtocolProcessors',terminal.protocolprocessor)
        newProtocolprocessor = tcc.get('ProtocolProcessors',args.protocolprocessor)
        currentVirtualrouter = tcc.get('VirtualRouters',currentProtocolprocessor.virtualrouter)
        newVirtualrouter = tcc.get('VirtualRouters',newProtocolprocessor.virtualrouter)
        currentSvcIdList = terminal.back_refs
        self.Id = self.findFreeId(1, 'Terminals', 'ProtocolProcessors', self.name, newProtocolprocessor.name)
        self.move = True
        self.vxlanip = terminal.vxlanip
        self.oldpp = currentProtocolprocessor.name
        self.newpp = newProtocolprocessor.name
        self.newppvxlanip = newProtocolprocessor.vxlanip
        self.oldvr = currentVirtualrouter.name
        try:
            result = sendData(self.show(),newProtocolprocessor.ipaddress,port,'createTerminal')
        except:
            print 'create terminal failed' 
        try:
            result = sendData(self.show(),terminal.ipaddress,port,'moveTerminal')
        except:
            print 'moving terminal failed'
        for term in tccConfigObject['Terminals']:
            if term['name'] == terminal.name:
                term['protocolprocessor'] = newProtocolprocessor.name
                term['Id'] = self.Id
        for ppObj in tccConfigObject['ProtocolProcessors']:
            if ppObj['name'] == currentProtocolprocessor.name:
                terminalIndex = ppObj['back_refs'].index(terminal.name)
                ppObj['back_refs'].pop(terminalIndex)
            if ppObj['name'] == newProtocolprocessor.name:
                ppObj['back_refs'].append(terminal.name)
        if len(terminal.back_refs) > 0:
            for svc in terminal.back_refs:
                service = tcc.get('Services',svc)
                dhcpIp = IPNetwork(service.subnet)
                service.move = True
                service.dhcpip = str(dhcpIp.broadcast - 1)
                service.Id = self.Id * 10 - 10 + terminal.back_refs.index(service.name) + 1
                service.virtualrouter = newVirtualrouter.name
                service.oldvr = currentVirtualrouter.name
                for svcObj in tccConfigObject['Services']:
                    if svcObj['name'] == service.name:
                        for term in svcObj['terminal']:
                           for te in term:
                               if te == terminal.name:
                                   service.oldId = term[te]
                                   term[te] = service.Id
                                   print term[te]
                try:
                    result = sendData(service.show(),newProtocolprocessor.ipaddress,port,'createService')
                except:
                    print 'creating service failed'
                try:
                    result = sendData(service.show(),terminal.ipaddress,port,'changeService')
                except:
                    print 'changing service failed'
                service.virtualrouter = currentVirtualrouter.name
                try:
                    service.Id = service.oldId
                    result = sendData(service.show(),currentProtocolprocessor.ipaddress,port,'deleteService')
                except:
                    print 'deleting service failed'
        try:
            result = sendData(self.show(),currentProtocolprocessor.ipaddress,port,'deleteTerminal')
        except:
            print 'deleting terminal failed'
        return tccConfigObject
                

class Service(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' ),
                                                 ( 'terminal', 'ref'),
                                                 ( 'customer', 'ref'),
                                                 ( 'routetarget', None),
                                                 ( 'subnet', None)])
        self.back_refs = []
        self.createMethod = 'createService'
        self.delMethod = 'delService'
        self.addMethod = 'addService'
        if obj:
            print obj
            if 'back_refs' in obj:
                self.back_refs = obj['back_refs']
            #self.Id = obj['Id']
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(Service, self).__init__()
    def createService(self):
        dhcpip = IPNetwork(self.subnet)
        self.dhcpip = str(dhcpip.broadcast - 1)
        terminal = tcc.get('Terminals',self.terminal)
        protocolprocessor = tcc.get('ProtocolProcessors',terminal.protocolprocessor)
        virtualRouter = tcc.get('VirtualRouters',protocolprocessor.virtualrouter)
        start = int(terminal.Id) * 10 - 10 + 1
        #svcId = self.findFreeId(start, 'Services', 'Terminals', self.name, terminal.name)
        svcId = self.findFreeSvcId(start, 'Services', 'Terminals', self.name, terminal.name)
        self.Id = svcId
        self.virtualrouter = virtualRouter.name
        result = sendData(self.show(),protocolprocessor.ipaddress,port,'createService')
        result = sendData(self.show(),terminal.ipaddress,port,'createService')
        return result
    def addService(self):
        dhcpip = IPNetwork(self.subnet)
        self.dhcpip = str(dhcpip.broadcast - 1)
        terminal = tcc.get('Terminals',self.terminal)
        protocolprocessor = tcc.get('ProtocolProcessors',terminal.protocolprocessor)
        virtualRouter = tcc.get('VirtualRouters',protocolprocessor.virtualrouter)
        service = tcc.get('Services', self.name)
        self.routetarget = service.routetarget
        self.customer = service.customer
        self.add = True 
        start = int(terminal.Id) * 10 - 10 + 1
        svcId = self.findFreeSvcId(start, 'Services', 'Terminals', self.name, terminal.name)
        #svcId = self.findFreeId(start, 'Services', 'Terminals', self.name, terminal.name)
        self.Id = svcId
        self.virtualrouter = virtualRouter.name
        result = sendData(self.show(),protocolprocessor.ipaddress,port,'createService')
        result = sendData(self.show(),terminal.ipaddress,port,'createService')
        return result
    def delService(self):
        service = tcc.get('Services',self.name)
        terminal = tcc.get('Terminals',args.terminal)
        protocolprocessor = tcc.get('ProtocolProcessors',terminal.protocolprocessor)
        virtualrouter = tcc.get('VirtualRouters',protocolprocessor.virtualrouter)
        self.terminal = terminal.name
        self.customer = service.customer
        print service.show()['terminal']
        for term in service.show()['terminal']:
            for te in term:
                if te == args.terminal:
                    print term[te]
                    self.Id = term[te]
        self.virtualrouter = virtualrouter.name
        numSvc = len(service.show()['terminal'])
        print numSvc
        if numSvc == 1:
            self.delvn = True
        result = sendData(self.show(),terminal.ipaddress,port,'deleteService')
        result = sendData(self.show(),protocolprocessor.ipaddress,port,'deleteService')
        #result = {'status':'bla'}
        return result

class Endpoint(Elements):
    def __init__(self, obj = None):
        self.mandatoryAttributes = CommentedMap([( 'name' , 'unique' ),
                                                 ( 'endpointtype' , None ),
                                                 ( 'terminal' , None ),
                                                 ( 'service', 'ref')])
        self.createMethod = 'createEndpoint'
        self.delMethod = 'delEndpoint'
        if obj:
            for attribute in self.mandatoryAttributes:
                setattr(self,attribute,obj[attribute])
        super(Endpoint, self).__init__()
    def createEndpoint(self):
        service = tcc.get('Services',self.service)
        terminal = tcc.get('Terminals',args.terminal)
        result = sendData(self.show(),terminal.ipaddress,port,'createEndpoint')
        return result
    def delEndpoint(self):
        endpoint = tcc.get('Endpoints',self.name)
        service = tcc.get('Services',endpoint.service)
        terminal = tcc.get('Terminals',args.terminal)
        self.service = service.name
        self.endpointtype = endpoint.endpointtype
        result = sendData(self.show(),terminal.ipaddress,port,'deleteEndpoint')
        return result

def sendData(data, host, port, action):
    print 'bla'
    connection = 'http://' + host + ':' + port + '/' + action
    req = urllib2.Request(connection)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data))
    return json.loads(response.read())
    return {'status':'ok'}

tccYaml = 'tcc.yaml'
f = open(tccYaml,'a+')
tccConfig = f.read()
tccConfigObject = ruamel.yaml.load(tccConfig, ruamel.yaml.RoundTripLoader)

host = '192.168.1.1'
port = '6666'

object_lookup = {}
object_lookup['Customers'] = Customer
object_lookup['VirtualRouters'] = VirtualRouter
object_lookup['ProtocolProcessors'] = ProtocolProcessor
object_lookup['Terminals'] = Terminal
object_lookup['Services'] = Service
object_lookup['Endpoints'] = Endpoint


element_lookup = {}
element_lookup['terminal'] = 'Terminals'
element_lookup['virtualrouter'] = 'VirtualRouters'
element_lookup['customer'] = 'Customers'
element_lookup['service'] = 'Services'
element_lookup['endpoint'] = 'Endpoints'
element_lookup['protocolprocessor'] = 'ProtocolProcessors'


if args.subparser_name == 'show':
    element = element_lookup[args.type]
    if tccConfigObject:
        if element in tccConfigObject and isinstance(tccConfigObject[element], list):
            tcc = Tcc(tccConfigObject)
            if args.name:
                elementObject = tcc.get(element,args.name)
                if elementObject:
                    print elementObject.show()
            else:
                for item in tcc.list(element):
                     print item.show()
        else:
            print 'no %s ' % element
    else:
        print 'no %s ' % element

if args.subparser_name == 'add':
    tcc = Tcc(tccConfigObject)
    element = element_lookup[args.type]
    class_object = object_lookup[element]()
    newElement = class_object.add(args, tccConfigObject)

if args.subparser_name == 'create':
    tcc = Tcc(tccConfigObject)
    element = element_lookup[args.type]
    class_object = object_lookup[element]()
    newElement = class_object.create(args, tccConfigObject)
    if newElement:
        print newElement.show()

if args.subparser_name == 'del':
    tcc = Tcc(tccConfigObject)
    element = element_lookup[args.type]
    class_object = object_lookup[element]()
    newElement = class_object.delete(args, tccConfigObject)

if args.subparser_name == 'move':
    tcc = Tcc(tccConfigObject)
    element = element_lookup[args.type]
    class_object = object_lookup[element]()
    class_object.move(args, tccConfigObject)
