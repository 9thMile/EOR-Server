import paho.mqtt.publish as publish
from array import *
import sys
import os
import re
import string
from datetime import date, datetime, time, timedelta
from time import sleep
import serial
import MySQLdb as mdb
import threading
import httplib, urllib
import wiringpi2 as wiringpi
import eospush as eosp
import eosutils as eosu
import eossql as eoss
import SetTime as eost
import logging
import logging.handlers

#Set the version 
S_Version = "1.2-0"


EOS_String = ""
has_db = False
has_serial = False
ser = serial.Serial()
Buff = ""
Buff2 = ""
E1 = ""
cur = None
db = None
eor_log = None
LOG_FILENAME = '/var/www/logs/eor.log'


#These are the wiringpi numbers
LED = ""
LED3 = 7
LED4 = 0
LED5 = 2

class Station:
    port = "/dev/ttyAMA0"    # Expected port
    baudrate = 9600          # change to 9600 for station
    bytesize = serial.EIGHTBITS
    parity = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE
    timeout = 0.1
    xonoff = 0
    rtscts = 0
    #interCharTimeout = none
    Wind_Count = 0
    Rain_Count = 0
    Temp_Count = 0
    Time_Count = 0
    Pressure_Count = 0
    Solar_Count = 0
    Location_Count = 0
    Board_Count = 0
    Soil_Count = 0
    Depth_Count = 0
    ID = ""
    App_Token = ""
    User_Key = ""
    Error_Level = 0
    Msg_Count = 0
    Altitude = 0
    Update = 0
    LED3 = False
    LED4 = False
    LED5 = False
    FlashLED3 = False
    FlashLED4 = False
    FlashLED5 = False
    Name = "EOS_Station"
    Broker_Address = ''
    Broker_Port = ''
    Broker_USN = ''
    Broker_PWD = ''
    FanState = ''

## Define the address bytes
class ADDRESS:
    D = 0
    E = 1
    O = 2
    S = 3
    INDICATOR = 4
    B1 = 5
    B2 = 6
    B3 = 7
    B4 = 8
    B5 = 9
    B6 = 10
    B7 = 11
    B8 = 12
    B9 = 13
    B10 = 14
    B11 = 15
    B12 = 16
    B13 = 17

class eos_reader(object):
    def __init__(self):
        print "Reader Initialized" 

    def Up(self):
        global has_db
        global has_serial
        if has_db and has_serial:
            return True
        else:
            return False

    def Update(self):
        return True

def EOS(s):
    global Station
    
    if s == 1:
        if Station.Wind_Count > 0:
            return True
        else:
            return False
    elif s == 2:
        if Station.Pressure_Count > 0:
            return True
        else:
            return False
    elif s == 3:
        if Station.Temp_Count > 0:
            return True
        else:
            return False
    elif s == 4:
        if Station.Rain_Count > 0:
            return True
        else:
            return False
    elif s == 5:
        if Station.Solar_Count > 0:
            return True
        else:
            return False
    elif s == 6:
        if Station.Board_Count > 0:
            return True
        else:
            return False
    elif s == 7:
        if Station.Soil_Count > 0:
            return True
        else:
            return False
    elif s == 8:
        if Station.Depth_Count > 0:
            return True
        else:
            return False
    else:
        return False

def setTime():
    global Station
    global ser
    global eor_log
    #Set Time/date on initial start if connected to internet
    try: 
        if eosp.is_connected():
            ip = "No connection"
            ip = eosp.get_my_ip()
##            try:
##                ip = eosp.get_ip_address("eth0")
##            except:
##                try:
##                    ip = eosp.get_ip_address("wlan0")
##                except:
##                    ip = "Not found"
            eor_log.info("Connected to WAN IP = " + ip)
            Station.LED4 = True
            Station.FlashLED4 = True
            d = datetime.now()
            dd = d.strftime("%d%m%y")
            dt = d.strftime("%H%M")
            ##eor_log.info("Updating Board Time :" + dd + " " + dt)
            ser.write("SE-D " + dd + chr(13))
            ser.write(chr(13))
            sleep(1)
            ser.write("SE-T " + dt + chr(13))
            ser.write(chr(13))
            sleep(1)
        else:
            #if not then we need to try and set the time on the pi
            #from the weather board
            ip = eosp.get_my_ip()
##            try:
##                ip = eosp.get_ip_address("eth0")
##            except:
##                try:
##                    ip = eosp.get_ip_address("wlan0")
##                except:
##                    ip = ""                
            if len(ip) > 6:
                Station.FlashLED4 = False
                Station.LED4 = True
            eor_log.critical("No Internet / IP = " + ip)
            ser.write(chr(13))
            sleep(2)
            ser.flushInput()
            ser.write("SE-D" + chr(13))
            sleep(1)
            bd = ser.readline()
            bd = ser.readline()
            bd = bd[1:]
            if len(bd) == 8:
                #Need to split out the MMDDYYYY
                d,m,y,y1 = [bd[i:i+2] for i in range(0,len(bd),2)]
                y = y + y1
                ser.write(chr(13))
                sleep(1)
                ser.write("SE-T" + chr(13))
                sleep(1)
                bt = ser.readline()
                bt = ser.readline()
                bt = ser.readline()
                bt = bt[1:]
                if len(bt) == 4:
                    #Need to split out HHMM
                    h,n = [bt[i:i+2] for i in range(0,len(bt),2)]
                    s = 0
                    time_truple =  (int(y), # Year
                                    int(m), #Month
                                    int(d), #Day
                                    int(h), #Hour
                                    int(n), #Minutes
                                    s, #Seconds
                                    s, #Milliseconds
                                   )
                    t = d + "/" + m + "/" + y + " " + h + ":" + n + ":00" 
                    nt = datetime.strptime(t, "%d/%m/%Y %H:%M:%S")
                    ##eosp.settime(t)
                    eost.set_time(time_truple)
                    
                    eor_log.critical("Set PI time from board to : " + bd + " " + bt)
        #Get Station ID
        ser.flushInput()
        ser.write(chr(13))
        ser.write("SE-S" + chr(13))
        sleep(1)
        ID = ser.readline()
        ID = ser.readline()
        ID = ser.readline()
        try:
            Station.ID = int(ID)
        except:
            Station.ID = 0
        
        
        return True
    except Exception, e:
        eor_log.error("Time set issue : " + str(e))
        return False

def setFan(a):
    global ser
    ##Set Fan 0=Off 1=On
    ser.write("SE-F " + str(a) + chr(13))
    ser.write(chr(13))
    sleep(1)
    
def setAltitude():
    global ser
    global Station
    ##Do altitude
    ser.write("SE-A " + str(Station.Altitude) + chr(13))
    ser.write(chr(13))
    sleep(1)

def KeepAlive():
    global ser
    global Station
    ser.write("$OK")
    ser.write(chr(13))
    sleep(1)
    
def setLED():
    global Station
    global LED
    try:
            
        a = "00"
        if Station.FlashLED3:
            if Station.LED3:
                wiringpi.digitalWrite(LED3,0)
                Station.LED3 = False
                a += "0"
            else:
                wiringpi.digitalWrite(LED3,1)
                Station.LED3 = True
                a += "1"
        else:
            if Station.LED3:
                wiringpi.digitalWrite(LED3,1)
                a += "1"
            else:
                wiringpi.digitalWrite(LED3,0)
                a += "0"
        if Station.FlashLED4:
            if Station.LED4:
                wiringpi.digitalWrite(LED4,0)
                Station.LED4 = False
                a += "0"
            else:
                wiringpi.digitalWrite(LED4,1)
                Station.LED4 = True
                a += "1"
        else:
            if Station.LED4:
                wiringpi.digitalWrite(LED4,1)
                a += "1"
            else:
                wiringpi.digitalWrite(LED4,0)
                a += "0"
        if Station.FlashLED5:
            if Station.LED5:
                wiringpi.digitalWrite(LED5,0)
                Station.LED5 = False
                a += "0"
            else:
                wiringpi.digitalWrite(LED5,1)
                Station.LED5 = True
                a += "1"
        else:
            if Station.LED5:
                wiringpi.digitalWrite(LED5,1)
                a += "1"
            else:
                wiringpi.digitalWrite(LED5,0)
                a += "0"

        a += "000"
        LED = a
        return True
    except Exception, e:
        LED = str(e)
        return False

                
class WeatherPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global Station
    global eor_log
    try:
        ##Setup wiringpi to output on 3/4/5 = pins 7/0/2
        wiringpi.wiringPiSetup()
        wiringpi.pinMode(LED3,1)  #Recieving data 
        wiringpi.pinMode(LED4,1)  #has network/ flash if IP address is ok, but not connected to external sites
        wiringpi.pinMode(LED5,1)
        wiringpi.digitalWrite(LED3,0)
        wiringpi.digitalWrite(LED4,0)
        wiringpi.digitalWrite(LED5,0)
        self.current_value = None
        self.running = True #setting the thread running to true
        eor_log.info("Starting EOR Server")
        Station.FlashLED3 = True  # flash when reading sentence 3 (Temp) every 10 sec        
    except:
        self.running = False
 
  def run(self):
    global ser
    global ADDRESS
    global Station
    global EOS_String
    global cur
    global db
    global has_serial
    global has_db
    global Buff
    global Buff2
    global E1
    global LED
    global EOS_reader
    global eor_log
    
    while self.running:
        try:
            Buff += ser.readline()
            if len(Buff) >= 18:
                if Buff.startswith("$EOSSD"):
                    ##this will be a command from hardware to shut down in 1 min and power off
                    self.running = False
                    eor_log.critical("Shutting Down - On command from Hardware")
                    if len(Station.User_Key) > 0:
                        eosp.sendpushover(Station.App_Token, Station.User_Key, "System is shutting down on command", 1)
                    time.sleep(10)
                    os.system('sudo shutdown -P +1')
                    
                elif Buff.startswith("$EOS"):
                    E = array("B",Buff)
                    if EOS(E[ADDRESS.INDICATOR]) == True:
                        if eosu.calcchecksum(Buff[:ADDRESS.B11]) == E[ADDRESS.B11]:
                            d = datetime.now()
                            date_time = d.isoformat()
                            date_time = re.sub("T"," ",date_time)
                            date_time = re.sub("Z","",date_time)
                            E1 = str(len(Buff)) + "/"
                            x = 0
                            for e in E:
                                E1 = E1 + str(e) + "-"
                                x += 1
                                if x == 18:
                                    break
                            a = "INSERT INTO FEED VALUES(" + str(E[ADDRESS.INDICATOR]) + ",0,'" + str(E1) + "'," + str(E[ADDRESS.B1]) + "," + str(E[ADDRESS.B2]) + "," + str(E[ADDRESS.B3]) + ","
                            a += str(E[ADDRESS.B4]) + "," + str(E[ADDRESS.B5]) + "," + str(E[ADDRESS.B6]) + "," + str(E[ADDRESS.B7]) + "," + str(E[ADDRESS.B8]) + ","
                            a += str(E[ADDRESS.B9]) + "," + str(E[ADDRESS.B10]) + "," + str(E[ADDRESS.B11]) + ",'" + date_time + "')"
                            test, e, rc = eoss.sqlUpdate(db, a)
                            if test == False:
                                eor_log.info(a + "/" + e)
                            else:
                                if rc == 0:
                                    eor_log.info(a + "/" + e)
                                else:
                                    eor_log.debug(a)
                            ##check if we need to set/flash LED 3/4/5 every time temp is read (~10 seconds)                     
                            if E[ADDRESS.INDICATOR] == 3:
                                if setLED():                 
                                    a = "Update STATION SET STR_VALUE = '" + LED + "' where LABEL = 'LED_STATE'"
                                    test, e, rc = eoss.sqlUpdate(db, a)
                                    if test == False:
                                        eor_log.info(a + "/" + e)
                                    else:
                                        if rc == 0:
                                            eor_log.info(a + "/" + e)
                                        else:
                                            eor_log.debug(a)
                                ##check if EOS is processing items                                
                                cur.execute("Select count(TYPE) C from FEED where IS_DONE = 0")
                                row = cur.fetchone()
                                if row is not None:
                                    b = int(row["C"])
                                    if b > 1000:
                                        if len(Station.User_Key) > 0:
                                            eosp.sendpushover(Station.App_Token, Station.User_Key, "EOS Server appears to be down - exiting", 1)
                                        
                                        eor_log.critical("Shutting Down - No EOS Server running")
                                        wiringpi.digitalWrite(LED3,0)
                                        wiringpi.digitalWrite(LED4,0)
                                        wiringpi.digitalWrite(LED5,0)
                                        a = "Update STATION SET STR_VALUE = '00000000' where LABEL = 'LED_STATE'"
                                        test, e, rc = eoss.sqlUpdate(db, a)
                                        if test == False:
                                            eor_log.info(a + "/" + e)
                                        else:
                                            if rc == 0:
                                                eor_log.info(a + "/" + e)
                                            else:
                                                eor_log.debug(a)
                                        has_db = False
                                        self.running = False
                                ##check if an update to station is required, will be set by Webman anytime or EOS server at 12:00am
                                Station.Update = eosu.getsetting(db, "DO_UPDATE", 1)
                                if Station.Update > 0:
                                    ser.write(chr(13))
                                    ser.flushInput()
                                    sleep(1)
                                    if Station.Update ==4:
                                        # = 4 keep alive signal
                                        KeepAlive()
                                        eor_log.info("Keep Alive sent $OK - will continue to read data")                                      
                                    elif Station.Update ==1:
                                        # = 1 normal update
                                        if setTime():
                                            if getSettings():                                    
                                                ##Do altitude
                                                setAltitude()
                                                eor_log.info("Updating Board Altitude :" + str(Station.Altitude))
                                    # = 2/3 then turn fan off else turn fan on
                                    elif Station.Update == 2:
                                        a = "Update STATION SET STR_Value = 'Fan Off' where LABEL = 'HAS_FAN'"
                                        test, e, rc = eoss.sqlUpdate(db, a)
                                        if test == False:
                                            eor_log.info(a + "/" + e)
                                        else:
                                            if rc == 0:
                                                eor_log.info(a + "/" + e)
                                            else:
                                                eor_log.debug(a)
                                        setFan(0)
                                        fanState = 'Off'
                                        eor_log.info("Station fan is OFF")
                                    elif Station.Update == 3:
                                        a = "Update STATION SET STR_Value = 'Fan On' where LABEL = 'HAS_FAN'"
                                        test, e, rc = eoss.sqlUpdate(db, a)
                                        if test == False:
                                            eor_log.info(a + "/" + e)
                                        else:
                                            if rc == 0:
                                                eor_log.info(a + "/" + e)
                                            else:
                                                eor_log.debug(a)
                                        setFan(1)
                                        fanState ='On'
                                        eor_log.info("Station fan is ON")
                                    #Clear the flag                                   
                                    a = "Update STATION SET INT_VALUE = 0 where LABEL = 'DO_UPDATE'"
                                    test, e, rc = eoss.sqlUpdate(db, a)
                                    if test == False:
                                        eor_log.info(a + "/" + e)
                                    else:
                                        if rc == 0:
                                            eor_log.info(a + "/" + e)
                                        else:
                                            eor_log.debug(a)

                                    ##MMQT
                                    if eosu.getsetting(db, "BROKER_ADDRESS",0) <> "":
                                        try:
                                            Station.Name  = eosu.getsetting(db, "NAME", 0)
                                            Station.Broker_Address = eosu.getsetting(db, "BROKER_ADDRESS", 0)
                                            Station.Broker_Port = eosu.getsetting(db, "BROKER_PORT", 0)
                                            Station.Broker_USN = eosu.getsetting(db, "BROKER_USN", 0)
                                            Station.Broker_PWD = eosu.getsetting(db, "BROKER_PWD", 0)
                                            auth = {'username':Station.Broker_USN,'password':Station.Broker_PWD}
                                            publish.single(topic= Station.Name + '/Status/Fan',payload=fanState,qos=0,retain=True, hostname=Station.Broker_Address,port=Station.Broker_Port,client_id='EOS_Station',auth=auth)
                                            sleep(5)
                                        except:
                                            eor_log.error('Error sending MQTT Message')


                                    #restart station
                                    ser.write("SE-O 48" + chr(13))
                                    eor_log.info("Set station for EOS Output - will continue to read data")
                                    ser.write(chr(13))
                                    Buff = ""
                                    ser.flushInput()
                                    sleep(1)
                                    ser.write("Q")                                   

                            eor_log.debug("Valid checksum :" + str(eosu.calcchecksum(Buff[:ADDRESS.B11]))+ "/" + str(E[ADDRESS.B11]) + " in sentence :" + str(E[ADDRESS.INDICATOR]))       
                            sleep(1)
                        else:
                            eor_log.error("Invalid checksum :" + eosu.calcchecksum(Buff[:ADDRESS.B11])+ "/" + E[ADDRESS.B11] + " in :" + Buff)
                            sleep(1)
                    Buff = Buff[18:]
                else:
                    a = Buff.find("$EOS")
                    if a >0:
                        Buff = Buff[a:]
                    else:
                        Buff == ""  
        except Exception, e:
            if len(Station.User_Key) > 0:
                eosp.sendpushover(Station.App_Token, Station.User_Key, str(e), -1)
                
            #shut down if data server is also shutting done.
            eor_log.error(str(e))
            s = str(e)
            z = s.find('1053')
            if z > 0 :
                self.running = False
                eor_log.critical("Shutting Down - No SQL Server")
                      
def getSettings():
    global db
    global Station
    global eor_log
    #0 = String, 1 = Int, 2 = Float, 3 = Datetime
    try:   
            
        Station.App_Token = eosu.getsetting(db, "APP_TOKEN", 0)
        Station.User_Key = eosu.getsetting(db, "USER_KEY", 0)
        Station.Wind_Count = eosu.getsetting(db, "WIND_COUNT", 1)
        Station.Rain_Count = eosu.getsetting(db, "RAIN_COUNT", 1)
        Station.Pressure_Count = eosu.getsetting(db, "PRESSURE_COUNT", 1)
        Station.Temp_Count = eosu.getsetting(db, "TEMP_COUNT", 1)
        Station.Solar_Count = eosu.getsetting(db, "SOLAR_COUNT", 1)
        Station.Soil_Count = eosu.getsetting(db, "SOIL_COUNT", 1)
        Station.Depth_Count = eosu.getsetting(db, "DEPTH_COUNT", 1)
        Station.Location_Count = eosu.getsetting(db, "LOCATION_COUNT", 1)
        Station.Board_Count = eosu.getsetting(db, "BOARD_COUNT", 1)
        Station.Error_Level = eosu.getsetting(db, "ERROR_LEVEL", 1)
        Station.ID = eosu.getsetting(db,"STAT_ID",1)
        Station.Name  = eosu.getsetting(db, "NAME", 0)
        Station.Broker_Address = eosu.getsetting(db, "BROKER_ADDRESS", 0)
        Station.Broker_Port = eosu.getsetting(db, "BROKER_PORT", 0)
        Station.Broker_USN = eosu.getsetting(db, "BROKER_USN", 0)
        Station.Broker_PWD = eosu.getsetting(db, "BROKER_PWD", 0)
        Station.FanState = eosu.getsetting(db, "HAS_FAN",0)

        return True
    except Exception, e:
        eor_log.error("Setting Update issue : " + str(e))
        return False

def main():
    global ADDRESS
    global SQL
    global Station
    global has_db
    global has_serial
    global EOS_String
    global cur
    global db
    global eor_log
    global S_Version
    """Set up logging files """
    try:
        os.remove(LOG_FILENAME)        
        os.remove(LOG_FILENAME + ".1")
        os.remove(LOG_FILENAME + ".2")
        os.remove(LOG_FILENAME + ".3")
        os.remove(LOG_FILENAME + ".4")
        os.remove(LOG_FILENAME + ".5")
        os.remove(LOG_FILENAME + ".6")
        os.remove(LOG_FILENAME + ".7")
        os.remove(LOG_FILENAME + ".8")
        os.remove(LOG_FILENAME + ".9")
        os.remove(LOG_FILENAME + ".10")
    except:
        pass    
    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}
    if len(sys.argv) > 1:
        level_name = sys.argv[1]
        level = LEVELS.get(level_name, logging.NOTSET)
        logging.basicConfig(filename=LOG_FILENAME,level=level)
    else:
        level = logging.INFO  ##Change this to modify logging details for all messages DEBUG/INFO
        
        logging.basicConfig(filename=LOG_FILENAME,level=level) ##Change this to modify logging details for all messages DEBUG/INFO
    eor_log = logging.getLogger('eorLogger')
    if level == logging.DEBUG:
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=10)
    else:
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=20000, backupCount=10)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    eor_log.addHandler(handler)
    eor_log.info("Waiting for MYSQL... to start")
    sleep(60) #wait a couple of min for services to start in case this is a bootup (65)
    """Ready to Go """
    try:
        EOS_reader = eos_reader()        
        db = mdb.connect(host= eoss.SQL.server, port = eoss.SQL.port, user= eoss.SQL.user,passwd= eoss.SQL.password, db= eoss.SQL.database)
        ## Set up a cursor to hold data and execute statments
        cur = db.cursor(mdb.cursors.DictCursor)

        if getSettings():
            version = eosu.getsetting(db, "EOR_VERSION", 0)
            
            if version <> S_Version:
                a ="Update STATION Set STR_VALUE ='%s' where LABEL = 'EOR_VERSION'" %(S_Version)
                test, e, rc = eoss.sqlUpdate(db, a)
                if test == False:
                    eor_log.info(a + "/" + e)
                else:
                    if rc == 0:
                        eor_log.info(a + "/" + e)
                    else:
                        eor_log.info(a)
           ##MMQT
            if Station.Broker_Address <> "":
                try:
                    auth = {'username':Station.Broker_USN,'password':Station.Broker_PWD}
                    publish.single(topic= Station.Name + '/Version/Software/EOR',payload=S_Version,qos=0,retain=True, hostname=Station.Broker_Address,port=Station.Broker_Port,client_id='EOS_Station',auth=auth)
                    sleep(5)
                    publish.single(topic= Station.Name + '/Status/Fan',payload=Station.FanState,qos=0,retain=True, hostname=Station.Broker_Address,port=Station.Broker_Port,client_id='EOS_Station',auth=auth)
                    sleep(5)
                except:
                    eor_log.error('Error4 sending MQTT Message')
            cur.execute("Delete from FEED")
            db.commit()
            eor_log.info("FEED table has been truncated")
            has_db = True
            eor_log.info("Database Connected - Starting")
        else:
            has_db = False
        try:
            ser.port = Station.port
            ser.baudrate = Station.baudrate
            ser.bytsize = Station.bytesize
            ser.parity = Station.parity
            ser.stopbits = Station.stopbits
            ser.timeout = Station.timeout
            ser.xonoff = Station.xonoff
            ser.rtscts = Station.rtscts
            #ser.interCharTimeout = STATION.interCharTimeout
            ser.open() #starting the stream of info
            eor_log.info("Serial Port Found")
            ser.write(chr(13))
            ser.flushInput()
            sleep(1)
            if setTime():
                setAltitude()
            
            if type(Station.ID) is int:
                a = "UPDATE STATION SET INT_VALUE = %d WHERE LABEL = 'STAT_ID'" %(Station.ID)
                test, e, rc = eoss.sqlUpdate(db, a)
                if test == False:
                    eor_log.info(a + "/" + e)
                else:
                    if rc == 0:
                        eor_log.info(a + "/" + e)
                    else:
                        eor_log.debug(a)

            
            #re-set fan to off - default state
            setFan(0)
            a = "Update STATION SET STR_Value = 'Fan Off' where LABEL = 'HAS_FAN'"
            test, e, rc = eoss.sqlUpdate(db, a)
            if test == False:
                eor_log.info(a + "/" + e)
            else:
                if rc == 0:
                    eor_log.info(a + "/" + e)
                else:
                    eor_log.debug(a)
            #restart station
            ser.write("SE-O 48" + chr(13))
            ser.write(chr(13))
            ser.flushInput()
            eor_log.info("Set station for EOS (48) Output")
            ser.write("Q")  #make sure that board is sending weather data
            has_serial = True
        except serial.SerialException:
            has_serial = False
            if len(Station.User_Key) > 0:
                eosp.sendpushover(Station.App_Token, Station.User_Key, "EOR Server NOT Running No Serial Port: " + ser.port, 1)
            eor_log.critical("EOR Server NOT Running No Serial Port: " + ser.port)
    except Exception, e:
        if len(Station.User_Key) > 0:
            eosp.sendpushover(Station.App_Token, Station.User_Key, "EOR Server NOT Running No DB", 1)
        has_db = False
        eor_log.critical("EOR server NOT Running: " + str(e) )
    if EOS_reader.Up():
        try:
            ## Station : Starting"    
            eorp = WeatherPoller()
            if len(Station.User_Key) > 0:
                eosp.sendpushover(Station.App_Token, Station.User_Key, "EOR Server Running", -1)
            eorp.run()
        except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
            print "Killing Thread..."
            eorp.running = False
            # wait for the thread to finish what it's doing                  
        except Exception,e:
            print str(e)
            eorp.running = False
    print 'Exiting'
    try:
        
        wiringpi.digitalWrite(LED3,0)
        wiringpi.digitalWrite(LED4,0)
        wiringpi.digitalWrite(LED5,0)
        a = "Update STATION SET STR_VALUE = '00000000' where LABEL = 'LED_STATE'"
        test, e, rc = eoss.sqlUpdate(db, a)
        if test == False:
            eor_log.info(a + "/" + e)
        else:
            if rc == 0:
                eor_log.info(a + "/" + e)
            else:
                eor_log.debug(a)
        db.close()
        if len(Station.User_Key) > 0:
            eosp.sendpushover(Station.App_Token, Station.User_Key, "EOR Server Stopped", 1)
    except Exception, e:
        print str(e)
        
    quit
    
if __name__ ==  '__main__':

    main()



        
