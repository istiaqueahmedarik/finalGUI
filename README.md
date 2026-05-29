# Sender_Gui


backend of the gui
cd urc_mission_bridge
cd mission_bridge
cd mission_bridge

change the ip of orin's end main.py and change the ip ofg goto_goal_2.py ---->to dashboard's ip
run ---->ros2 run mission_bridge mission_controller
run the script goto_goal_2.py (python got_goal_2.py)(orin's end)


dashboard's end 
here in dashbaord in utility->send_udp change to orins ip 
in componenents ->mission_viewer change it orin's ip 




running the main program
cd SenderGUI
activate venv(source venv/bin/actiavte)
cd src 
python main.py




for URC MISSION TO DOWNLOAD MAP 
CHANGE THE CONFIGURATAION MISSION CONFIG.JSON