source /home/alexander/Documents/ecosim/ecosimpy/ecosim/venv/bin/activate
konsole -e "python /home/alexander/Documents/ecosim/ecosimpy/ecosim/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py --config-file ../Modules/house/preferences.ini --debug --simulator-type fmu" &
konsole -e "python /home/alexander/Documents/ecosim/ecosimpy/ecosim/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py --config-file ../Modules/occupancy/preferences.ini --debug --simulator-type fmu" &
konsole -e "python /home/alexander/Documents/ecosim/ecosimpy/ecosim/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py --config-file ../Modules/weather/preferences.ini --debug --simulator-type fmu" &
