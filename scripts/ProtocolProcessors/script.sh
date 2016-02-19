sleep 3
systemctl restart networking.service
tmux new-session -d -s ppserver
tmux new-session -d -s addlif
tmux send -t ppserver python SPACE /ppServer.py ENTER
tmux send -t addlif python SPACE /addLif.py ENTER
#python /ppServer.py &
#python /addLif.py &
