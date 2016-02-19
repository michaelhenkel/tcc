sleep 3
systemctl restart networking.service
tmux new-session -d -s terminalserver
tmux send -t terminalserver python SPACE /terminalServer.py ENTER
#python /terminalServer.py &
