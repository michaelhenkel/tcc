sleep 3
systemctl restart networking.service
python /ppServer.py &
python /addLif.py &
