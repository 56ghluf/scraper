echo ===== "$(date '+%Y-%m-%d %H:%M:%S')" $0 =====

cd $1
$2 run update_orders.py

printf "\n"
