#If you are using a Pico W, be sure to create the envSecrets.py with hostname, ssid,
#wifipsw, timeApiUrl. timeApiUrl is:
# 'https://timeapi.io/api/TimeZone/zone?timeZone={INSERT TIME ZONE HERE}'
import urequests
from microdot_utemplate import render_template
from machine import Pin, ADC
from utime import sleep, sleep_ms, time, localtime
import network
import envSecrets
import ntptime
import usys
import uos
import uasyncio
import _thread
from microdot_asyncio import Microdot, Response, redirect

verbose = False

def update_main_script():
    response = urequests.get(github_url)
    new_code = response.text
    response.close()

    # Check if the new code is different from the existing code
    if new_code != open('main.py').read():
        appLog('Github code is different, updating...')
        # Save the new main.py file
        with open('main.py', 'w') as f:
            f.write(new_code)

        # Reset the Pico to apply the updated main.py
        machine.reset()

def appLog(stringOfData):
    global verbose
    #print(f'applog verbose value is {verbose}')
    if verbose:
        with open('log.txt','a') as file:
            if type(stringOfData) == str:
                file.write(f"{utcToLocal('datetime')} {stringOfData}\n")
                print(f"{utcToLocal('datetime')} {stringOfData}")
            else:
                file.write(f"{utcToLocal('datetime')} --- Traceback begin ---\n")
                usys.print_exception(stringOfData,file)
                file.write(f"{utcToLocal('datetime')} --- Traceback end ---\n")

def utcToLocal(type):
    #get the offset from timeapi.io, using your timezone
    global localUtcOffset
    localTime = localtime(time() + localUtcOffset)
    if type == 'time':
        return f'{localTime[3]:02d}:{localTime[4]:02d}:{localTime[5]:02d}'
    elif type == 'date':
        return f'{localTime[0]}/{localTime[1]}/{localTime[2]:02d}'
    else:
        return f'{localTime[0]}/{localTime[1]}/{localTime[2]:02d} {localTime[3]:02d}:{localTime[4]:02d}:{localTime[5]:02d}'

def tempSensor():
    sensor_temp = ADC(4)
    conversion_factor = 3.3 / (65535)
    reading = sensor_temp.read_u16() * conversion_factor 
    temperature = 27 - (reading - 0.706)/0.001721
    temp = temperature * 9 / 5 + 32
    return float(f'{temp:.1f}')

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.config(hostname=envSecrets.hostname)
    sleep(1)
    wlan.active(True)
    wlan.connect(envSecrets.ssid, envSecrets.wifipsw)
    iter = 1
    while wlan.ifconfig()[0] == '0.0.0.0':
        print(f'Not Connected...{iter}')
        iter += 1
        sleep(1)
        if iter == 10:
            wlan.connect(envSecrets.ssid, envSecrets.wifipsw)
            iter = 1
    ip = wlan.ifconfig()[0]
    print(f'{network.hostname()} is connected on {ip}')

def createTempHtmlOptionsList(toggleTemp):
    iter = 68.0
    fullHtmlStr = ""
    while iter < 100.1:
        strMinute = f'{iter:.1f}'
        if iter == toggleTemp:
            newStr = f'<option selected="selected" value="{strMinute}">{strMinute}</option>'
        else:
            newStr = f'<option value="{strMinute}">{strMinute}</option>'
        fullHtmlStr = fullHtmlStr + newStr
        iter += .5
    return fullHtmlStr

def createEnvStatusOptionsList(defaultValue):
    fullHtmlStr = ""
    options = ['Enable','Disable']
    for item in options:
        if item == defaultValue:
            newStr = f'<option selected="selected" value="{item}">{item}</option>'
        else:
            newStr = f'<option value="{item}">{item}</option>'
        fullHtmlStr = fullHtmlStr + newStr
    return fullHtmlStr


def createMinHTMLoptionsList(defaultValue, MinOrHour):
    iter = 0
    if MinOrHour.lower() == 'hour':
        iterEnd = 23
    else:
        iterEnd = 59
    fullHtmlStr = ""
    while iter <= iterEnd:
        strIter = f'{iter:02d}'
        if iter == defaultValue:
            newStr = f'<option selected="selected" value="{strIter}">{strIter}</option>'
        else:
            newStr = f'<option value="{strIter}">{strIter}</option>'
        fullHtmlStr = fullHtmlStr + newStr
        iter += 1
    return fullHtmlStr

def createIntervalHTMLOptions(defaultInterval):
    intervalList = [10, 20, 30, 45, 60, 120]
    fullHtmlStr = ""
    for item in intervalList:
        if item == defaultInterval:
            newStr = f'<option selected="selected" value="{item}">{item} minutes</option>'
        else:
            newStr = f'<option value="{item}">{item} minutes</option>'
        fullHtmlStr = fullHtmlStr + newStr
    return fullHtmlStr

def writeToValveSettingsDotText(postBody):
    global intervalTimer
    global mistersOnTimer
    mistersOnTimer = 0
    intervalTimer = 0
    skipItems = ['submitForm=Submit', '']
    valveSetStr = ''
    for item in postBody:
        if item not in skipItems:
            newStr=f"{item}\n"
            valveSetStr = valveSetStr + newStr
    with open('valveSettings.txt','w') as fw:
        fw.write(valveSetStr)

def readNewValveSettingsDotText():
    global toggleTemp
    global startHour
    global startMin
    global endHour
    global endMin
    global mistersOnMinutes
    global intervalDefault
    global valveHtmlTempOptions
    global startHourHTMLOptions
    global startMinHTMLOptions
    global endHourHTMLOptions
    global endMinHTMLOptions
    global intervalHTMLOptions
    global disableEnableLabel
    global disableEnableHTMLOptions
    with open('valveSettings.txt','r') as fr:
        lines = fr.readlines()

    variables_dict = {}

    # Step 4: Iterate through the lines and extract variable names and values
    for line in lines:
        # Step 5: Split the line at the '=' character to get the variable name and value
        variable_name, value = line.strip().split('=')
        
        # Step 6: Convert the value to the appropriate data type (int, float, str, etc.)
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                value = value.strip('"')

        # Step 7: Add the variable and its value to the dictionary
        variables_dict[variable_name] = value
    # Step 8: Now you can access the variables using the dictionary
    toggleTemp = variables_dict.get('toggleTemp')
    startHour = variables_dict.get('startHour')
    startMin = variables_dict.get('startMin')
    endHour = variables_dict.get('endHour')
    endMin = variables_dict.get('endMin')
    mistersOnMinutes = variables_dict.get('mistersOnMinutes')
    intervalDefault = variables_dict.get('interval')
    disableEnableLabel = variables_dict.get('disableEnableLabel').replace("'","")
    valveHtmlTempOptions = createTempHtmlOptionsList(toggleTemp)
    startHourHTMLOptions = createMinHTMLoptionsList(startHour, 'hour')
    startMinHTMLOptions = createMinHTMLoptionsList(startMin, 'minute')
    endHourHTMLOptions = createMinHTMLoptionsList(endHour, 'hour')
    endMinHTMLOptions = createMinHTMLoptionsList(endMin, 'minute')
    intervalHTMLOptions = createIntervalHTMLOptions(intervalDefault)
    disableEnableHTMLOptions = createEnvStatusOptionsList(disableEnableLabel)
    if disableEnableLabel == 'Disable':
        valveControl('Close')

def valveControl(action):
    if action == 'Open':
        valvePin.value(1)
    elif action == 'Close':
        valvePin.value(0)
    #else:
    #    print('returning status')
    #return current status
    if valvePin.value() == 0:
        return 'Closed'
    else:
        return 'Opened'
        
async def mistersLoop():
    #print(f'Core1 says toggleTemp is {toggleTemp}')
    #Use this to loop evaluation of valve
    global verbose
    global intervalDefault
    global mistersOnTimer
    global intervalTimer
    global misterStatus
    global manualConLabel
    global disableEnableLabel
    global toggleTemp
    mistersOnTimer = 0
    intervalTimer = 0
    misterStatus = False
    while True:
        
        if disableEnableLabel == 'Enable':
            if manualConLabel == 'Turn_ON':
                #this means the manual control does not have the
                #misters running
                getTime = utcToLocal('time').split(':')
                #if int(startHour) <= int(getTime[0]) <= int(endHour):
                #    print('The hour is within range')
                if int(startHour) == int(getTime[0]) and int(startMin) <= int(getTime[1]):
                    appLog('Current time equals Start hour and after start minutes, running')
                    timeRange = True
                elif int(endHour) == int(getTime[0]) and int(endMin) >= int(getTime[1]):
                    appLog('Current time equals End hour and before end minutes, running')
                    timeRange = True
                elif int(startHour) < int(getTime[0]) < int(endHour):
                    appLog('Current time is within range, running')
                    timeRange = True
                else:
                    appLog(f'time is out of range, Current time: {getTime[0]}:{getTime[1]}, Start time: {startHour}:{startMin}, End time: {endHour}:{endMin}')
                    timeRange = False
                    if valveControl('Status') == 'Opened':
                        valveControl('Close')

                if timeRange:
                    if intervalTimer == 0:
                        if tempSensor() >= float(toggleTemp):
                            appLog('Current temp is at or above setting, running misters')
                            if mistersOnTimer == 0:
                                valveControl('Open')
                                misterStatus = True
                                mistersOnTimer = time() + mistersOnMinutes*60
                                intervalTimer = time() + intervalDefault*60
                        else:
                            appLog(f'Temp is too low, Current temp: {tempSensor()}, Configured temp: {toggleTemp}')
                            if valveControl('Status') == 'Opened':
                                valveControl('Close')
                    else:
                        #use this else to evaluate if interval timer is done
                        if time() >= intervalTimer:
                            #setting intervalTimer AND mistersOnTimer to 0
                            appLog('Current time has surpassed the interval, setting values to 0 to re-evaluate current temperature to restart')
                            intervalTimer = 0
                            mistersOnTimer = 0
                        else:
                            if mistersOnTimer == 0:
                                appLog(f'Misters already off, counting down interval with {intervalTimer - time()} seconds left before re-evaluation')
                            else:
                                if time() >= mistersOnTimer:
                                    appLog('Misters duration done, turning off for rest of interval')
                                    misterStatus = False
                                    valveControl('Close')
                                    mistersOnTimer = 0
                                else:
                                    appLog(f'Misters are currently running for {mistersOnTimer - time()} more seconds')
                                
            else:
                #this else pertains to the manual control button
                appLog('Misters are on with manual override')
                mistersOnTimer = 0
                intervalTimer = 0
        else:
            appLog(f'The misters are currently disabled')
            if valveControl('Status') == 'Opened':
                valveControl('Close')
        await uasyncio.sleep(5)

def core2():
    uasyncio.create_task(mistersLoop())


#Variables
#Setting defaults depending on which pico
devCheck = uos.uname()
if 'Pico W' in devCheck.machine:
    dev = 'picow'
    led = Pin('LED', Pin.OUT)
else:
    dev = 'pico'
    led = Pin(25, Pin.OUT)
led.value(0)
global manualConLabel
manualConLabel = 'Turn_ON'
valvePin = Pin(26, Pin.OUT)
valvePin.value(0)

#Allow time to interrupt main.py and enable LED to show main.py is running
led.value(1)
sleep(5)
led.value(0)

verbose = False
# URL of the raw main.py file on GitHub
github_url = 'https://raw.githubusercontent.com/NFLEagles500/htmlSprinkler/main/main.py'

if dev == 'picow':
    connect()
    # Perform initial update on startup
    update_main_script()
    try:
        while True:
            try:
                ntptime.settime()
                print('ntptime success')
                break
            except:
                print('ntptime fail, trying again')
                sleep(1)
                pass
        while True:
            try:
                responseFromTimeapi = urequests.get(envSecrets.timeApiUrl)
                print('responseFromTimeapi worked')
                break
            except Exception as error:
                print(f'{error}, trying again')
                sleep(1)
                pass
        localUtcOffset = responseFromTimeapi.json()['currentUtcOffset']['seconds']
        responseFromTimeapi.close()
    except Exception as error:
        print(error)

app = Microdot()

Response.default_content_type = 'text/html'

@app.route('/')
async def index(request):
    global manualConLabel
    global disableEnableLabel
    picoTemp = tempSensor()
    if disableEnableLabel == 'Disable':
        envStatus = 'Disabled, change in "Modify Temperature Settings"'
    else:
        envStatus = 'Enabled, change in "Modify Temperature Settings"'
    if valvePin.value() == 0:
        valveStat = 'Closed'
        #manualConLabel = 'Turn_ON'
    else:
        valveStat = 'Open'
        #manualConLabel = 'Turn_OFF'
    readNewValveSettingsDotText()
    return render_template('home.html', picoTemp, valveStat, toggleTemp, startHour, startMin, endHour, endMin, manualConLabel, envStatus)

@app.route('/',methods=["POST"])
async def toggValve(request):
    global disableEnableLabel
    global manualConLabel
    value = request.body.decode().replace('\r\n','').split('=')
    if disableEnableLabel == 'Enable':
        if value[1] == 'Turn_ON':
            valveControl('Open')
            manualConLabel = 'Turn_OFF'
        else:
            valveControl('Close')
            manualConLabel = 'Turn_ON'
    return redirect("/")

@app.route('/update')
async def update(request):
    return render_template('settings.html', valveHtmlTempOptions, startHourHTMLOptions, startMinHTMLOptions, endHourHTMLOptions, endMinHTMLOptions, intervalHTMLOptions, mistersOnMinutes, disableEnableHTMLOptions)

@app.route('/update',methods=["POST"])
async def process_updates(request):
    codes = request.body.decode().split('\r\n')
    writeToValveSettingsDotText(codes)
    return redirect("/")

readNewValveSettingsDotText()
second_thread = _thread.start_new_thread(core2, ())
led.value(1)
try:
    appLog('Starting webserver')
    app.run(port=80)
except:
    app.shutdown()
    machine.reset()
#Start coding.  Blink added for example
while True:
    led.toggle()
    sleep(2)

