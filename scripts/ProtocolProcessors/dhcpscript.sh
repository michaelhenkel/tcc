#!/bin/bash
echo $1 > /tmp/bla
echo $2 >> /tmp/bla
echo $3 >> /tmp/bla
echo $4 >> /tmp/bla
echo $DNSMASQ_TAGS >> /tmp/bla
#/usr/bin/python /mnt/addLif.py $1 $2 $3 $4 $DNSMASQ_TAGS >> /tmp/bla
python /addLifClient.py $1 $2 $3 $4 $DNSMASQ_TAGS $1
