./tccClient.py add customer -n cust1
./tccClient.py add customer -n cust2
./tccClient.py add virtualrouter -host 192.168.1.66 -n vr1 -ip 192.168.1.70
./tccClient.py add virtualrouter -host 192.168.1.66 -n vr2 -ip 192.168.1.71
./tccClient.py add protocolprocessor -host 192.168.1.66 -n pp1 -ip 192.168.1.80 -vip 10.0.0.1 -vr vr1
./tccClient.py add protocolprocessor -host 192.168.1.66 -n pp2 -ip 192.168.1.81 -vip 10.0.0.2 -vr vr1
./tccClient.py add terminal -host 192.168.1.66 -n t1 -ip 192.168.1.90 -vip 10.0.0.10 -pp pp1
./tccClient.py add terminal -host 192.168.1.66 -n t2 -ip 192.168.1.91 -vip 10.0.0.11 -pp pp1
./tccClient.py add service -n svc1 -sn 1.0.0.0/24 -t t1 -cust cust1 -rt 1:1
./tccClient.py add service -n svc2 -sn 2.0.0.0/24 -t t1 -cust cust2 -rt 1:2
./tccClient.py add service -n svc3 -sn 3.0.0.0/24 -t t2 -cust cust1 -rt 1:3
./tccClient.py add service -n svc4 -sn 4.0.0.0/24 -t t2 -cust cust2 -rt 1:4
./tccClient.py add endpoint -n ep1 -svc svc1
./tccClient.py add endpoint -n ep2 -svc svc2
./tccClient.py add endpoint -n ep3 -svc svc3
./tccClient.py add endpoint -n ep4 -svc svc4
