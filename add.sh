./3tccClient.py create customer -n cust1
./3tccClient.py create customer -n cust2
./3tccClient.py create customer -n cust3
./3tccClient.py create virtualrouter -host 192.168.1.2 -n vr1 -ip 192.168.1.70
./3tccClient.py create virtualrouter -host 192.168.1.3 -n vr2 -ip 192.168.1.71
./3tccClient.py create virtualrouter -host 192.168.1.4 -n vr3 -ip 192.168.1.72
./3tccClient.py create protocolprocessor -host 192.168.1.2 -n pp1 -ip 192.168.1.80 -vip 10.0.0.1 -vr vr1
./3tccClient.py create protocolprocessor -host 192.168.1.3 -n pp2 -ip 192.168.1.81 -vip 10.0.0.2 -vr vr2
./3tccClient.py create protocolprocessor -host 192.168.1.4 -n pp3 -ip 192.168.1.82 -vip 10.0.0.3 -vr vr3
./3tccClient.py create terminal -host 192.168.1.1 -n t1 -ip 192.168.1.90 -vip 10.0.0.10 -pp pp1
./3tccClient.py create terminal -host 192.168.1.1 -n t2 -ip 192.168.1.91 -vip 10.0.0.11 -pp pp2
./3tccClient.py create terminal -host 192.168.1.1 -n t3 -ip 192.168.1.92 -vip 10.0.0.12 -pp pp3
./3tccClient.py create service -n svc1 -sn 1.0.0.0/24 -t t1 -cust cust1 -rt 1:1
./3tccClient.py add service -n svc1 -t t2
./3tccClient.py create service -n svc2 -sn 2.0.0.0/24 -t t2 -cust cust2 -rt 1:2
./3tccClient.py add service -n svc2 -t t3
./3tccClient.py create service -n svc3 -sn 3.0.0.0/24 -t t3 -cust cust3 -rt 1:3
./3tccClient.py add service -n svc3 -t t1

#./3tccClient.py create service -n svc4 -sn 4.0.0.0/24 -t t2 -cust cust2 -rt 1:4
#./3tccClient.py create service -n svc5 -sn 5.0.0.0/24 -t t3 -cust cust1 -rt 1:5
#./3tccClient.py create service -n svc6 -sn 6.0.0.0/24 -t t3 -cust cust2 -rt 1:6
./3tccClient.py create endpoint -n ep10 -svc svc1 -t t1 -et lxc
./3tccClient.py create endpoint -n ep11 -svc svc1 -t t2 -et lxc
./3tccClient.py create endpoint -n ep20 -svc svc2 -t t2 -et lxc
./3tccClient.py create endpoint -n ep21 -svc svc2 -t t3 -et lxc
./3tccClient.py create endpoint -n ep30 -svc svc3 -t t3 -et lxc
./3tccClient.py create endpoint -n ep31 -svc svc3 -t t1 -et lxc
#./3tccClient.py create endpoint -n ep40 -svc svc4 -et lxc
#./3tccClient.py create endpoint -n ep41 -svc svc4 -et lxc
#./3tccClient.py create endpoint -n ep50 -svc svc5 -et lxc
#./3tccClient.py create endpoint -n ep51 -svc svc5 -et lxc
#./3tccClient.py create endpoint -n ep60 -svc svc6 -et lxc
#./3tccClient.py create endpoint -n ep61 -svc svc6 -et lxc
