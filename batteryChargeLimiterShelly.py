# Dependencies
import psutil
import subprocess
import time
from win11toast import toast
from pathlib import Path

# Functions
def errorMessage(lvl, msg): #format cli notifications, goal is to keep any notification minimal in case of perfect operation
    if lvl <= vocationality:
        print(["FATAL ERROR:", "ERROR:","Warning:","    "][lvl], msg) # lvl:0/1/2/3 for fatal/error/warning/note
    return 0

def uptime(): #convert time to readable
    return '%d:%02d:%02d h' % ((time.time()-startTime) / 3600, ((time.time()-startTime) %3600 ) / 60, (time.time()-startTime) % 60)

def cmd(myCmd): #cmd shortcut
    return subprocess.run(myCmd.split(), capture_output=True, timeout=30, shell=True)

def readSensor(): #read battery percentage and adjust charging status accordingly, updates percy & oldPercy, returns bool (is charging?)
    global percy, oldPercy, shellyIsOn
    oldPercy = percy #save old battery percentage
    percy = psutil.sensors_battery().percent #read new battery percentage
    if shellyIsOn: #catch edge case of just turned on but no change in batt percentage yet
        return percy >= oldPercy #off-state based on evidence (or batt draw too large, unlikely)
    return percy > oldPercy # on-state based on evidence

def resetTimer():
    global startTime, startPercy, percy
    startTime = time.time()
    startPercy = percy
    return 0

def makeShellyTurn(offOn):
    for n in range(1,4): #three retries (n=1,2,3)
        if not cmd("netsh wlan connect name=" + shellyName).returncode:
            if n>1: 
                errorMessage(3,"Could not establish connection (netsh). Retrying for "+str(n*n+2)+" seconds...")
            time.sleep(n*n+2) #wait some time to let wifi connection establish
            if not cmd("curl http://" + shellyUser + ":" + shellyPass + "@192.168.33.1/relay/0?turn=" + offOn).returncode:
                cmd("netsh wlan disconnect") #reset connection & let win auto-reconnect take over
                return 0
            errorMessage(2,"Shelly did not accept command or not connected.") #not worth distinguishing as Shelly (energy save mode?) seems flaky
            cmd("netsh wlan disconnect") #in case of late connect still reset connection
    errorMessage(1,"Could not reach Shelly in network.")
    return 1

def wrapShellyTurn(offOn):
    global startTime
    increasePanicCounter() #collect action warning
    for n in range (1,4): #three retries (n=1,2,3)
        if not makeShellyTurn(offOn) or readSensor()==(offOn=="on"): #success via communication or evidence
            resetTimer()
            return 0
        errorMessage(3,"Could not makeShellyTurn("+str(offOn)+"). Retrying in "+str(n*n)+" seconds...")
        time.sleep(n*n) #if shelly needs time to wake up?
    errorMessage(1,"Could not turn power %s." % offOn)
    return 1

def increasePanicCounter():
    global panicCounter
    panicCounter += 1
    if panicCounter == 3: #actions did not work 3 times in a row
        errorMessage(2,"Actions have no effect. Trying soft reset.")
        toast("Warning: Can not reach Shelly.") #notify user, e.g. if cable not connected to laptop
    return 0

def printPercy():
    print("%7s" % time.strftime("%H:%M h"), "█"*percy + "░"*(100-percy), "%3d%%" % percy)
    return 0

def readSettings(): #parse yaml (yes there are parsers out there but I wanted to build one myself)
    global battMax, battMin, tick, vocationality, shellyName, shellyUser, shellyPass
    try:
        with Path().absolute().joinpath("batteryChargeLimiterShelly.config.yaml").open() as set: #...from file
            set = set.read().split("\n")
            for n in range(0,len(set)):
                newVar = set[n].split("#",1)[0].split(":",1) #remove comments.split by name and value
                if len(newVar)>1: #ignore lines without ":"
                    match newVar[0].strip():
                        case "battMax":
                            try:
                                newVal = float(newVar[1])
                                if newVal>=0 and newVal<=100:
                                    battMax = newVal
                                else:
                                    errorMessage(2,"Invalid value for battery percentage (battMax:" + newVal + ").")
                            except:
                                errorMessage(2,"Invalid type for \"battMax\".")
                        case "battMin":
                            try:
                                newVal = float(newVar[1])
                                if newVal>=0 and newVal<=100:
                                    battMin = newVal
                                else:
                                    errorMessage(2,"Invalid value for battery percentage (battMin:" + newVal + ").")
                            except:
                                errorMessage(2,"Invalid type for \"battMin\".")
                        case "tick":
                            try:
                                newVal = float(newVar[1])
                                if newVal>0:
                                    tick = newVal
                                else:
                                    errorMessage(2,"Invalid value for tick period (tick:" + newVal + ").")                        
                            except:
                                errorMessage(2,"Invalid type for \"tick\".")
                        case "vocationality":
                            try:
                                newVal = int(newVar[1])
                                if newVal in range(0,4):
                                    vocationality = newVal
                                else:
                                    errorMessage(2,"Invalid value for vocationality (vocationality:" + newVal + ").")                        
                            except:
                                errorMessage(2,"Invalid type for \"vocationality\".")
                        case "shellyName":
                            shellyName = newVar[1].strip()
                        case "shellyUser":
                            shellyUser = newVar[1].strip()
                        case "shellyPass":
                            shellyPass = newVar[1].strip()
                        case _:
                            errorMessage(3,"Unknown variable encountered in config.yaml (" + newVar[0].strip() + ").")
        if not (shellyName and shellyUser and shellyPass): #check for minimum set of settings
            errorMessage(1,"Invalid configuration file (name, user, or password of Shelly is missing).")
            return 1
    except:
        errorMessage(1,"No configuration file found (batteryChargeLimiterShelly.config.yaml).")
        return 1
    return 0


# MAIN
# Initialization 1/2 - settings
battMax = 80 #/percent  
battMin = 20 # /percent
tick = 60 # /seconds
vocationality = 1 #/level; 0:silent, 1:errors only, 2:errors & warnings, 3:all notifications
shellyName = ""
shellyUser = ""
shellyPass = ""
if readSettings():
    errorMessage(0,"Could not read configuration (batteryChargeLimiterShelly.config.yaml).")
    input("Press Enter to quit...")
    quit()
print("Settings for", shellyName, ":\n - Start charging below", battMin, "%\n - Stop charging above", battMax, "%\n - Tickperiod is", tick, "seconds\n - notifications about", ["fatal errors","errors only","also warnings","any"][vocationality], "\n")

# Initialization 2/2 - internal
powerConnected = 1
shellyIsOn = 0 #assumption
startTime = time.time()
panicCounter = 0
percy = psutil.sensors_battery().percent
startPercy = percy
readSensor()
errorMessage(3,"Running...")

# Get battery charge & act if neccessary
while powerConnected: #infinite loop    

    # Check for battery status change per tick
    while percy == psutil.sensors_battery().percent:
        if time.time()%(10*tick) < tick: #display battery bar every tenth tick
            printPercy()
        print(time.strftime("%H:%M h"), ["Idle", "Charging"][shellyIsOn], "since", uptime(), "at", "{:.2f}".format((percy-startPercy)/(time.time()-startTime+1)*3600), "%/h and currently at", percy, "%.    ", end="\r") #human readable status message (the "+1" is a hack to avoid div0)
        time.sleep(tick) # tick
        print("...", " "*99, end="\r") #clear status message

    # Check if action neccessary (based on battery percentage & charging status)
    newShellyIsOn = readSensor()
    if shellyIsOn != newShellyIsOn: #external change detected
        errorMessage(2, "External variance in charging status detected (" + ["is not plugged in?","freshly plugged in?"][newShellyIsOn] + ").")
        resetTimer()
    shellyIsOn = newShellyIsOn
    if percy > battMax and shellyIsOn:         
        shellyIsOn = wrapShellyTurn("off")
    elif percy < battMin and not shellyIsOn:
        shellyIsOn = 1 - wrapShellyTurn("on")
    else:
        panicCounter = 0 #reset