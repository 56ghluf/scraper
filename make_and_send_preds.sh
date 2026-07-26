cd $1
./build/bin/get_current_openinsider_data
$2 run make_latest_preds.py
