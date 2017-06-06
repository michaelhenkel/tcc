#create services
## L2
./3tccClient.py create service -n svc1 -sn 1.0.0.0/24 -t t1 -cust cust1 -rt 1:1 -m l2 -cv 1
./3tccClient.py create service -n svc2 -sn 2.0.0.0/24 -t t2 -cust cust2 -rt 1:2 -m l2 -cv 2
./3tccClient.py create service -n svc3 -sn 3.0.0.0/24 -t t3 -cust cust3 -rt 1:3 -m l2 -cv 3

## L3
./3tccClient.py create service -n svc4 -sn 4.0.0.0/24 -t t1 -cust cust1 -rt 1:4 -m l3 -cv 0
./3tccClient.py create service -n svc5 -sn 5.0.0.0/24 -t t2 -cust cust2 -rt 1:5 -m l3 -cv 0
./3tccClient.py create service -n svc6 -sn 6.0.0.0/24 -t t3 -cust cust3 -rt 1:6 -m l3 -cv 0

#extend services
## l@
./3tccClient.py add service -n svc1 -t t3
./3tccClient.py add service -n svc2 -t t1
./3tccClient.py add service -n svc3 -t t2

## L3
./3tccClient.py add service -n svc4 -t t3
./3tccClient.py add service -n svc5 -t t1
./3tccClient.py add service -n svc6 -t t2

# create endpoints
./3tccClient.py create endpoint -n ep10 -svc svc1 -t t1 -et ns
./3tccClient.py create endpoint -n ep20 -svc svc2 -t t2 -et ns
./3tccClient.py create endpoint -n ep30 -svc svc3 -t t3 -et ns

./3tccClient.py create endpoint -n ep40 -svc svc4 -t t1 -et ns
./3tccClient.py create endpoint -n ep50 -svc svc5 -t t2 -et ns
./3tccClient.py create endpoint -n ep60 -svc svc6 -t t3 -et ns

./3tccClient.py create endpoint -n ep11 -svc svc1 -t t3 -et ns
./3tccClient.py create endpoint -n ep21 -svc svc2 -t t1 -et ns
./3tccClient.py create endpoint -n ep31 -svc svc3 -t t2 -et ns

./3tccClient.py create endpoint -n ep41 -svc svc4 -t t3 -et ns
./3tccClient.py create endpoint -n ep51 -svc svc5 -t t1 -et ns
./3tccClient.py create endpoint -n ep61 -svc svc6 -t t2 -et ns

./3tccClient.py move terminal -n t1 -pp pp2
./3tccClient.py move terminal -n t1 -pp pp3
./3tccClient.py move terminal -n t2 -pp pp3
./3tccClient.py move terminal -n t1 -pp pp1
./3tccClient.py move terminal -n t2 -pp pp2
