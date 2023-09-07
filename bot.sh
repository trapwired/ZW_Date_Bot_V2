#!/bin/bash

stop_bot () {
	ps -ef | grep "ZW_Date_Bot_V2/src/main.py"| grep -v grep | awk '{print $2}' | xargs -r kill
}

start_bot () {
	nohup /usr/bin/python3 /root/ZW_Date_Bot_V2/src/main.py &	
}

restart_bot_if_necessary() {
	process=ZW_Date_Bot_V2/src/main.py
	if ps ax | grep -v grep | grep $process > /dev/null
	then
    		exit
	else
    		start_bot
	fi

	exit
}

git_pull() {
	OUTPUT=$(git pull)
	NUM_LINES="$(echo "$OUTPUT" | wc -l)"
	
	if [ $NUM_LINES -gt 1 ];
	then
		stop_bot
		echo 'Stopping bot due to pull'
	fi
}


case "$1"
in
restart)
	stop_bot
	start_bot
	;;
stop) 
	stop_bot
	;;
start) 
	start_bot
	;;
alwaysOn)
	restart_bot_if_necessary
	;;
pull)
	git_pull
	;;
esac
