README FOR batteryChargeLimiterShelly

#TLDR
-change atteryChargeLimiterShelly.config.yaml & put next to exe
-win+r -> type "shell:startup" -> add shortcut to .exe 
-optionally make app to start minimized in rightclick->details

# WIFI CONNECTION FLOW for shellyplug-s-A1B2C3 with user & pass
# netsh wlan connect name=shellyplug-s-A1B2C3
# netsh wlan show interfaces
# curl http://user:pass@192.168.33.1/relay/0?turn=on
# netsh wlan disconnect

# EXPORTING AS EXECUTABLE
# cd /d D:\Documents\Git Yard\batteryChargeLimiterShelly
# pyinstaller -F batteryChargeLimiterShelly.py

--
Archived version history pre git:
#v1.2: clean up, added vocationality for message density, changed setting configuration to external file
#v1.1: added charge rate info, fixed edge case detection behavior of external charging state change
#v1.0: fixed connection error introduced in change in interface handling in win11_23H2 update, now omits check of SSID in favor of unelevation, can detect manual changes of charging status
#v0.9: included charging status check into connection retry mechanic
#v0.8: swapped action & wait for battery change blocks in main loop (avoids wrong uncertainty state interpretation at initialization)
#v0.7: switched to active sensor interpretation (shellyIsOn now based on evidence rather command)
#v0.6: switched netsh access from "os" to "subprocess"
#v0.5: redesigned timeout handling when trying to connect to Shelly
#v0.4: updated battery status graphics
#v0.3: updated UI to graphicly represent battery level
#v0.2: restructured code into functions and settings
#v0.1: designed basic functionality
#v0.0: idea of toggling power outlet based on laptop battery percentage