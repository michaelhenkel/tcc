./3tccClient.py create service -n svc1 -sn 1.0.0.0/24 -t t1 -cust cust1 -rt 1:1 -m l2 -cv 1
./3tccClient.py add service -n svc1 -t t2
./3tccClient.py create service -n svc2 -sn 2.0.0.0/24 -t t2 -cust cust2 -rt 1:2 -m l2 -cv 2
./3tccClient.py add service -n svc2 -t t1

./3tccClient.py create endpoint -n ep10 -svc svc1 -t t1 -et ns
./3tccClient.py create endpoint -n ep11 -svc svc1 -t t2 -et ns
./3tccClient.py create endpoint -n ep20 -svc svc2 -t t1 -et ns
./3tccClient.py create endpoint -n ep21 -svc svc2 -t t2 -et ns

./3tccClient.py move terminal -n t1 -pp pp2
