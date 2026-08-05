echo ===== $0 ["$(date '+%Y-%m-%d %H:%M:%S')"] =====

cd "$1"
"$2" run update_orders.py

printf "\n"
