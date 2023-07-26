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
from microdot_asyncio import Microdot, Response

#Allow time to interrupt main.py
sleep(5)

def update_main_script():
    response = urequests.get(github_url)
    new_code = response.text
    response.close()

    # Check if the new code is different from the existing code
    if new_code != open('main.py').read():
        print('Github code is different, updating...')
        # Save the new main.py file
        with open('main.py', 'w') as f:
            f.write(new_code)

        # Reset the Pico to apply the updated main.py
        machine.reset()

def appLog(stringOfData):
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
    return temp

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

def createTempHtmlOptionsList(valveTemp):
    iter = 68.0
    fullHtmlStr = ""
    while iter < 100.1:
        strMinute = f'{iter:.1f}'
        if iter == valveTemp:
            newStr = f'<option selected="selected" value="{strMinute}">{strMinute}</option>'
        else:
            newStr = f'<option value="{strMinute}">{strMinute}</option>'
        fullHtmlStr = fullHtmlStr + newStr
        iter += .5
    return fullHtmlStr

def createMinHTMLoptionsList(defaultValue, MinOrHour):
    iter = 0
    if MinOrHour.lower() == 'hour':
        iterEnd = 23
    else:
        iterEnd = 59
    fullHtmlStr = ""
    while iter < iterEnd:
        strIter = f'{iter:02d}'
        if iter == defaultValue:
            newStr = f'<option selected="selected" value="{strIter}">{strIter}</option>'
        else:
            newStr = f'<option value="{strIter}">{strIter}</option>'
        fullHtmlStr = fullHtmlStr + newStr
        iter += 1
    return fullHtmlStr
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

with open('valveSettings.txt','r') as fr:
    lines = fr.readlines()

variables_dict = {}

# Step 4: Iterate through the lines and extract variable names and values
for line in lines:
    # Step 5: Split the line at the '=' character to get the variable name and value
    variable_name, value = line.strip().split(' = ')
    
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
valveTemp = variables_dict.get('valveTemp')
startHour = variables_dict.get('startHour')
startMin = variables_dict.get('startMin')
endHour = variables_dict.get('endHour')
endMin = variables_dict.get('endMin')
mistersOnMinutes = variables_dict.get('mistersOnMinutes')
interval = variables_dict.get('interval')

valveHtmlTempOptions = createTempHtmlOptionsList(valveTemp)
startHourHTMLOptions = createMinHTMLoptionsList(startHour, 'hour')
startMinHTMLOptions = createMinHTMLoptionsList(startMin, 'minute')
endHourHTMLOptions = createMinHTMLoptionsList(endHour, 'hour')
endMinHTMLOptions = createMinHTMLoptionsList(endMin, 'minute')

# def printVars():
#     global valveTemp
#     print(f"valveTemp is {valveTemp} before I change it")
#     valveTemp = 97.8
# 
# printVars()
# print(f"printVars() has attempted to change valveTemp, it is now {valveTemp}")
# input('Did it change?')

# Step 9: Print the variables to verify
# print(valveTemp)           # Output: 99.8
# print(anotherVariable)     # Output: 42
# print(someOtherVariable)   # Output: Hello, World!
#If you need the output as your script runs, add appLog('String of data') throughout the script.
#When you change verbose to True, appLog will send the data to a log.txt for you to evaluate after
#execution and it will print to the console as well
verbose = False
# URL of the raw main.py file on GitHub
github_url = 'https://raw.githubusercontent.com/NFLEagles500/htmlSprinkler/main/main.py'

if dev == 'picow':
    connect()
    # Perform initial update on startup
    #update_main_script()
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
        appLog(error)

app = Microdot()

Response.default_content_type = 'text/html'

@app.route('/')
async def index(request):
    picoTemp = tempSensor()
    if led.value() == 0:
        valveStat = 'Closed'
    else:
        valveStat = 'Open'
    return render_template('home.html', picoTemp, valveStat)

@app.route('/update')
async def update(request):
    return render_template('settings.html', valveHtmlTempOptions, startHourHTMLOptions, startMinHTMLOptions, endHourHTMLOptions, endMinHTMLOptions)

try:
    print('Starting webserver')
    app.run(port=80)
except:
    app.shutdown()
    machine.reset()
#Start coding.  Blink added for example
while True:
    led.toggle()
    sleep(2)

