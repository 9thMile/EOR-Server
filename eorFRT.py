import paho.mqtt.publish as publish
from array import *
import sys
import os
import re
import string
import math
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
S_Version = "1.1-5a"


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

class EOSTIME:
    Hours = 0
    Minutes = 0
    Seconds = 0

def getTime():
    global EOSTIME
    
    t = datetime.now()
    EOSTIME.Hours = float(t.hour)
    EOSTIME.Minutes = float(t.minute)
    EOSTIME.Seconds = float(t.second)

class C_Wind:
    R = ''
    I = ''
    A = ''
    G = ''
    U = ''
    D = ''
    N = ''
    F = ''

class C_Temp:
    R = ''
    I = ''
    P = ''
    T = ''

class C_Rain:
    R = ''
    I = ''
    U = ''
    S = ''
    M = ''
    Z = ''
    P = ''
    X = ''
    Y = ''

class C_Solar:
    R = ''
    M = ''

class C_UV:
    R = ''
    M = ''
    
    
class C_Station:
    D_Address = 0
    aR1 = '0R1' + chr(13) + chr(10)
    aR2 = '0R2' + chr(13) + chr(10)
    aR3 = '0R3' + chr(13) + chr(10)
    aR4 = '0R4' + chr(13) + chr(10)
    aR5 = '0R5' + chr(13) + chr(10)
    aWU = '0WU' + chr(13) + chr(10)
    aTU = '0TU' + chr(13) + chr(10)
    aRU = '0RU' + chr(13) + chr(10)
    aYU = '0YU' + chr(13) + chr(10)
    aUV = '0UV' + chr(13) + chr(10)
    aXU = '0XU' + chr(13) + chr(10)
    aR1L = ''  #Stores last sentance recieved to compair to incoming
    aR2L = ''
    aR3L = ''
    aR4L = ''
    aR5L = ''
    aXZRU = '0XZRU' + chr(13) + chr(10) #rain reset
    EOSwind = '1'
    EOSpressure = '2'
    EOStemp = '3'
    EOSrain = '4'
    EOSsolar = '5'
    Sn = 0
    Sm = 0
    Sx = 0
    Dn = 0
    Dm = 0
    Dx = 0
    Pa = 0
    Ta = 0
    Td = 0
    Tp = 0
    Ua = 0
    Rc = 0
    Rd = 0
    Ri = 0
    Rp = 0
    Sr = 0
    Uv = 0
    
class C_Settings:
    A = ''
    M = ''
    T = ''
    C = ''
    I = ''
    B = ''
    D = ''
    P = ''
    S = ''
    L = ''
    N = ''
    V = ''
    
    
class Station:
    port = "/dev/ttyUSB0"    # Expected port
    baudrate = 19200          # change to 19200 for station
    bytesize = serial.EIGHTBITS
    parity = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE
    timeout = 0.1
    xonoff = 0
    rtscts = 0
    #interCharTimeout = none
    datetime
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
    Altitude = 0
    ID = ""
    App_Token = ""
    User_Key = ""
    Error_Level = 0
    Msg_Count = 0
    Altitude = 0
    Update = 0
    Name = "EOS_Station"
    Broker_Address = ''
    Broker_Port = ''
    Broker_USN = ''
    Broker_PWD = ''  

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


def calc_dewpoint(temp, hum):

    c = temp
    x = 1 - 0.01 * hum;
    dewpoint = (14.55 + 0.114 * c) * x;
    dewpoint = dewpoint + ((2.5 + 0.007 * c) * x) ** 3;
    dewpoint = dewpoint + (15.9 + 0.117 * c) * x ** 14;
    dewpoint = c - dewpoint;
    return dewpoint

def EOS_Send():
    global ser
    global ADDRESS
    global Station
    global C_Station
    global EOS_String
    global cur
    global db
    global has_serial
    global has_db
    global Buff
    global E1
    global eor_log    
    sleep(1)
    E = array("B",Buff)
    if EOS(E[ADDRESS.INDICATOR]) == True:
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
                            
        if E[ADDRESS.INDICATOR] == 3:
            ##check if EOS is processing items                                
            cur.execute("Select count(TYPE) C from FEED where IS_DONE = 0")
            row = cur.fetchone()
            if row is not None:
                b = int(row["C"])
                if b > 1000:
                    if len(Station.User_Key) > 0:
                        eosp.sendpushover(Station.App_Token, Station.User_Key, "EOS Server appears to be down - exiting", 1)
                    
                    eor_log.critical("Shutting Down - No EOS Server running")
                    has_db = False
                    

                
class WeatherPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global Station
    global eor_log
    try:
        self.current_value = None
        self.running = True #setting the thread running to true
        eor_log.info("Starting EOR Server")     
    except:
        self.running = False
 
  def run(self):
    global ser
    global ADDRESS
    global Station
    global EOSTIME
    global C_Station
    global EOS_String
    global cur
    global db
    global has_serial
    global has_db
    global Buff
    global E1
    global LED
    global EOS_reader
    global eor_log
    Cycles = 0
    while self.running:
        getTime()
        if has_db == False:
            self.running = False
        try:
            ## reset rain at midnight
            if EOSTIME.Hours == 0 and EOSTIME.Minutes == 0:
                Buff = ''
                c = 0
                while Buff == '' and c < 5:
                    try:
                        ser.flushInput()
                        ser.write(C_Station.aXZRU)
                        sleep(.2)
                        Buff = ser.readline()
                        eor_log.debug(Buff)
                        if Buff[0:4] == '0TX,':
                            eor_log.info("Rain Reset :" + Buff)
                        else:
                            Buff = ''
                            eor_log.error("Error on Rain Reset :" + Buff)
                            sleep(5)
                            c = c +1
                    except Exception, e:
                        eor_log.error("Error sending Rain Reset:" + C_Station.aXZRU + ' -' + str(e))
                        Buff = ''
                        sleep(1)
                        c = c + 1                        
                sleep(60) #wait for a minute to pass
            
            if EOSTIME.Minutes < 2:
                Buff = ''
                c = 0
                while Buff =='' and c < 5:
                    try:
                        ser.flushInput()
                        sleep(1)
                        ser.write(C_Station.aXU)
                        sleep(.2)
                        Buff = ser.readline()
                        eor_log.debug(Buff)
                        
                        if Buff[0:4] == '0XU,':
                        
                            Buff = Buff[4:]
                            Buff = Buff[:-2]
                            buff = Buff
                            items = dict(item.split("=") for item in Buff.split(","))
                            C_Settings.V = items['V']
                            C_Settings.V = C_Settings.V[1:-4]
                            Buff = '$EOS' + chr(6) + chr(0) + chr(0)  + chr(0)  + chr(0) + chr(0) + chr(0) + chr(0) + chr(0) + chr(int(C_Settings.V[:2])) + chr(int(C_Settings.V[3:])) + chr(0) + chr(13) + chr(10)
                            EOS_Send()
                        else:
                            eor_log.error("Error reading settings :" + Buff)
                            Buff = ''
                            sleep(1)
                            c = c + 1
                    except Exception, e:
                        eor_log.error("Error sending settings:" + C_Station.aXU + ' -' + str(e))
                        Buff = ''
                        sleep(1)
                        c = c + 1                        
                    
            if Cycles == 11:
                Cycles = 0
            Buff = ''
            print Cycles
            eor_log.info('Doing Cycle ' + str(Cycles))
            eor_log.debug('Cycle: ' + str(Cycles))
            if Station.Wind_Count > 0:
                Buff = ''
                c = 0
                while Buff == '' and c < 5:
                    try:
                        ser.flushInput()
                        ser.write(C_Station.aR1)
                        sleep(.2)
                        Buff = ser.readline()
                        if Buff[0:4] == '0R1,':
                            Buff = Buff[:-2]
                            eor_log.debug(Buff)
                            if Buff <> C_Station.aR1L:  ##only send if something has changed
                                C_Station.aR1L = Buff 
                            
                                Buff = Buff[4:]
                                items = dict(item.split("=") for item in Buff.split(","))
                                ## verify we have valid data which will have # in UoM if not valid
                                wdunits = items['Dm'][-1:]
                                wsunits = items['Sm'][-1:]
                                if wdunits == 'D' and wsunits == 'K':
                                        
                                    C_Station.Dn = float(items['Dn'][:-1])
                                    C_Station.Dm = float(items['Dm'][:-1])
                                    C_Station.Dx = float(items['Dx'][:-1])
                                    C_Station.Sn = float(items['Sn'][:-1])
                                    C_Station.Sm = float(items['Sm'][:-1])
                                    C_Station.Sx = float(items['Sx'][:-1])
                                    items.clear()
                                    if C_Station.Dm > 255:
                                        WD1 = chr(255)
                                        WD2 = chr(abs(int(C_Station.Dm))- 255)
                                    else:
                                        WD1 = chr(abs(int(C_Station.Dm)))
                                        WD2 = chr(0)
                                    Buff = '$EOS' + chr(1) + chr(abs(int(C_Station.Sx))) + chr(int((C_Station.Sx - int(C_Station.Sx)) * 10))  + chr(abs(int(C_Station.Sx))) + chr(int((C_Station.Sx - int(C_Station.Sx)) * 10))  + chr(abs(int(C_Station.Sm))) + chr(int((C_Station.Sm - int(C_Station.Sm)) * 10)) + chr(1) + WD1 + WD2 + chr(0) + chr(0) + chr(13) + chr(10)
                                    EOS_Send()
                                else:
                                    items.clear()
                                    eor_log.error("Invalid wind sentence recieved: " + Buff)
                                    
                            else:
                                eor_log.debug("Same wind sentence")
                        else:
                            eor_log.error("Error reading wind:" + Buff)
                            Buff = ''
                            c = c + 1
                            sleep(1)
                    except Exception, e:
                        eor_log.error("Error sending :" + C_Station.aR1 + ' -' + str(e))
                        Buff = ''
                        sleep(1)
                        c = c + 1
            if Cycles == 5:
                if Station.Solar_Count > 0:
                    Buff = ''
                    c = 0
                    while Buff =='' and c < 5:
                        try:
                            ser.flushInput()
                            ser.write(C_Station.aR4)
                            sleep(.2)
                            Buff = ser.readline()
                            
                            if Buff[0:4] == '0R4,':
                                
                                Buff = Buff[:-2]
                                eor_log.debug(Buff)
                                if Buff <> C_Station.aR4L: ##only send if something has changed
                                    Buff = Buff[4:]
                                    C_Station.aR4L = Buff
                                    C_Station.Sr = float(Buff[3:-1])
                                    if C_Station.Sr > 256:
                                        W1 = abs(int(C_Station.Sr / 256))
                                        W2 = abs(int((int(C_Station.Sr ))-(W1*256)))
                                    else:
                                        W1 = 0
                                        W2 = abs(int(C_Station.Sr))
                                else:
                                    eor_log.debug("Same solar sentence")
                                    
                            else:
                                eor_log.error("Error reading solar:" + Buff)
                                Buff = ''
                                c = c + 1
                                sleep(1)
                        except Exception, e:
                            eor_log.error("Error sending :" + C_Station.aR4 + ' -' + str(e))
                            Buff = ''
                            c = c + 1
                            sleep(1)

                            
                    Buff =''
                    c = 0
                    while Buff == '' and c < 5:
                        try:
                            ser.flushInput()
                            ser.write(C_Station.aR5)
                            sleep(.2)
                            Buff = ser.readline()
                            
                            if Buff[0:4] == '0R5,':
                                Buff = Buff[:-2]
                                eor_log.debug(Buff)
                                if Buff <> C_Station.aR5L: ##only send if something has changed
                                    Buff = Buff[4:]
                                    C_Station.aR5L = Buff
                                    
                                    C_Station.Uv = float(Buff[3:-1])

                                    Buff = '$EOS' + chr(5) + chr(0) + chr(0) + chr(abs(int(C_Station.Uv))) + chr(W1) + chr(W2) + chr(0) + chr(0) + chr(0) + chr(0) + chr(0) + chr(0) +chr(13) + chr(10)
                                    EOS_Send()
                                else:
                                    eor_log.debug("Same UV sentence")
                                    
                            else:
                                eor_log.error("Error reading UV:" + Buff)
                                Buff = ''
                                c = c + 1
                                sleep(1)
                        except Exception, e:
                            eor_log.error("Error sending :" + C_Station.aR5 + ' -' + str(e))
                            Buff = ''
                            c = c + 1
                            sleep(1)
                        
            if Cycles == 9:
                if Station.Rain_Count > 0:
                    Buff = ''
                    c = 0
                    while Buff == '' and c < 5:
                        try:
                            ser.flushInput()
                            ser.write(C_Station.aR3)
                            sleep(.2)
                            Buff = ser.readline()
                            
                            if Buff[0:4] == '0R3,':
                                Buff = Buff[:-2]
                                eor_log.debug(Buff)

                                if Buff <> C_Station.aR3L: ##only send if something has changed
                                    C_Station.aR3L = Buff
                                    Buff = Buff[4:]
                                    
                                    items = dict(item.split("=") for item in Buff.split(","))
                                    runits = items['Rc'][-1:]
                                    if runits == 'M':
                                        C_Station.Rc = float(items['Rc'][:-1])   ##these are tips = .1 mm
                                        C_Station.Rd = float(items['Rd'][:-1])
                                        C_Station.Ri = float(items['Ri'][:-1])
                                        items.clear()

                                    
                                        Tips = C_Station.Rc/10
                                        Tips2 = int(Tips)
                                        Tips1 = int((Tips - Tips2)*100)
                                        Tips3 = int(C_Station.Rc)
                                        Tips4 = int((C_Station.Rc-float(Tips3))*10)

                                        Buff = '$EOS' + chr(4) + chr(abs(int(C_Station.Ri))) + chr(int(((C_Station.Ri - int(C_Station.Ri)) * 10))) + chr(Tips3) + chr(Tips4) + chr(0) + chr(0) + chr(Tips1) + chr(Tips2) + chr(0) + chr(0) + chr(0) + chr(13) + chr(10)
                                        EOS_Send()
                                    else:
                                        items.clear()
                                        eor_log.error("Invalid rain sentence recieved: " + Buff)
                                        
                                else:
                                    eor_log.debug("Same Rain sentence")
                            else:
                                eor_log.error("Error reading rain:" + Buff)
                                Buff = ''
                                c = c + 1
                                sleep(1)                               
 
                        except Exception, e:
                            eor_log.error("Error sending rain:" + C_Station.aR3 + ' -' + str(e))
                            Buff = ''
                            c = c + 1
                            sleep(1)

            if Cycles == 10:
                if Station.Temp_Count + Station.Pressure_Count > 0:
                    Buff = ''
                    c = 0
                    while Buff =='' and c < 5:
                        try:
                            ser.flushInput()
                            ser.write(C_Station.aR2)
                            sleep(.1)
                            Buff = ser.readline()
                            
                            if Buff[0:4] == '0R2,':
                                Buff = Buff[:-2]
                                eor_log.debug(Buff)
                                if Buff <> C_Station.aR2L: ##only send if something has changed
                                    Buff = Buff[4:]
                                    C_Station.aR2L = Buff
                                    items = dict(item.split("=") for item in Buff.split(","))
                                    tunits = items['Ta'][-1:]
                                    punits = items['Pa'][-1:]
                                    hunits = items['Ua'][-1:]
                                    if tunits == 'C' and punits == 'H' and hunits == 'P':
                                        C_Station.Ta = float(items['Ta'][:-1])
                                        ##print C_Station.Ta
                                        C_Station.Ua = float(items['Ua'][:-1])
                                        C_Station.Pa = float(items['Pa'][:-1])
                                        C_Station.Td = round(calc_dewpoint(C_Station.Ta, C_Station.Ua),1)
                                        
                                        items.clear()
                                        if C_Station.Ta < 0 :
                                            tNeg = 1
                                            C_Station.Ta = abs(C_Station.Ta)
                                        else:
                                            tNeg = 0
                                        if C_Station.Td < 0 :
                                            dNeg =1
                                            C_Station.Td = abs(C_Station.Td)
                                        else:
                                            dNeg = 0
                                        if Station.Altitude > 256:
                                            A2 = abs(int(Station.Altitude / 256))
                                            A1 = abs(int((int(Station.Altitude ))-(A2*256)))
                                        else:
                                            A2 = 0
                                            A1 = abs(int(Station.Altitude))
                                        if Station.Temp_Count > 0:
    ##                                        print C_Station.Ta
    ##                                        print chr(abs(int(C_Station.Ta))) 
    ##                                        print chr(int((C_Station.Ta - int(C_Station.Ta)) * 10))
    ##                                        print chr(abs(int(C_Station.Td)))
    ##                                        print chr(int((C_Station.Td - int(C_Station.Td)) * 10))
    ##                                        print chr(abs(int(C_Station.Ua)))
    ##                                        print chr(ONeg) 
                                            
                                            Buff = '$EOS' + chr(3) + chr(abs(int(C_Station.Ta))) + chr(int((C_Station.Ta - int(C_Station.Ta)) * 10)) + chr(abs(int(C_Station.Td))) + chr(int((C_Station.Td - int(C_Station.Td)) * 10)) + chr(abs(int(C_Station.Ua))) + chr(tNeg) + chr(dNeg) + chr(0) + chr(0) + chr(0) + chr(0) + chr(13) + chr(10)
                                            EOS_Send()
                                        P1 = abs(int(C_Station.Pa * 10/ 256))
                                        P2 = abs(int((int(C_Station.Pa * 10))-(P1*256)))
                                        if Station.Pressure_Count > 0:
                                            Buff = '$EOS' + chr(2) + chr(P1) + chr(P2) + chr(A1) + chr(A2) + chr(P1) + chr(P2) + chr(0) + chr(0) + chr(0) + chr(0) + chr(0) + chr(13) + chr(10)
                                            EOS_Send()  
                                        else:
                                            items.clear()
                                            eor_log.error("Invalid Temp/Pressure sentence recieved: " + Buff)

                                else:
                                    eor_log.debug("Same Temp/Pressure sentence")
                            else:
                                eor_log.error("Error reading Temp/Pressure:" + Buff)
                                Buff = ''
                                c = c + 1
                                sleep(1)
                        except Exception, e:
                            eor_log.error("Error sending :" + C_Station.aR2 + ' -' + str(e))
                            Buff = ''
                            c = c + 1
                            sleep(1)
            Cycles = Cycles + 1
            sleep(1)
            

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
        Station.Altitude = eosu.getsetting(db,"ALTITUDE",1)
        Station.Name  = eosu.getsetting(db, "NAME", 0)
        Station.Broker_Address = eosu.getsetting(db, "BROKER_ADDRESS", 0)
        Station.Broker_Port = eosu.getsetting(db, "BROKER_PORT", 0)
        Station.Broker_USN = eosu.getsetting(db, "BROKER_USN", 0)
        Station.Broker_PWD = eosu.getsetting(db, "BROKER_PWD", 0)
        
        
        return True
    except Exception, e:
        eor_log.error("Setting Update issue : " + str(e))
        return False

def main():
    global ADDRESS
    global SQL
    global Station
    global C_Station
    global C_Settings
    global has_db
    global has_serial
    global EOS_String
    global Buff
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
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d -> %(message)s")
    handler.setFormatter(formatter)
    eor_log.addHandler(handler)
    eor_log.info("Waiting for MYSQL... to start")
    sleep(1) #wait a couple of min for services to start in case this is a bootup (65)
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
                auth = {'username':Station.Broker_USN,'password':Station.Broker_PWD}
                publish.single(topic= Station.Name + '/Version/Software/EOR',payload=S_Version,qos=0,retain=True, hostname=Station.Broker_Address,port=Station.Broker_Port,client_id='EOS_Station',auth=auth)
                sleep(5)
                
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

            try:
                ser.open() #starting the stream of info
                eor_log.info("Serial Port Found")                
                sleep(1)
                ser.flushInput()
                ser.write('?'+ chr(13) + chr(10))
                sleep(.2)
                Buff = ser.readline()
                print Buff
                Buff = Buff[:-2]
                
                if Buff[:1] <> '0':
                    print 'Station not set up on Device Address 0:' + Buff
                    eor_log.critical("Station not set up as Device Address 0: " + Buff)
                    has_serial = True
                    
                else:
                    Buff = ''
                    while Buff =='':
                        ser.flushInput()
                        sleep(1)
                        ser.write(C_Station.aXU)
                        sleep(.2)
                        Buff = ser.readline()
                        eor_log.info('Reading serial port for configuration: ' + Buff)
                        if Buff[0:4] == '0XU,':
                        
                            Buff = Buff[4:]
                            Buff = Buff[:-2]
                            buff = Buff
                            items = dict(item.split("=") for item in Buff.split(","))
                            C_Settings.A = items['A'] #address - 0
                            C_Settings.M = items['M'] #Communication Protocal - 
                            C_Settings.T = items['T'] #Test
                            C_Settings.C = items['C'] #Serial Interface - 
                            C_Settings.I = items['I'] #Automatic Interval
                            C_Settings.B = items['B'] #Baud Rate
                            C_Settings.D = items['D'] #Bits
                            C_Settings.P = items['P'] #Parity
                            C_Settings.S = items['S'] #Stop Bits
                            C_Settings.L = items['L'] #Line delay
                            C_Settings.N = items['N'] #Name of device
                            C_Settings.V = items['V'] #Version
                            #Get version
                            C_Settings.V = C_Settings.V[1:-4]
                            Buff = '$EOS' + chr(6) + chr(0) + chr(0)  + chr(0)  + chr(0) + chr(0) + chr(0) + chr(0) + chr(0) + chr(int(C_Settings.V[:2])) + chr(int(C_Settings.V[3:])) + chr(0) + chr(13) + chr(10)
                            EOS_Send()
                            #test configuration
                            if C_Settings.M == 'P' and C_Settings.C == '2' and C_Settings.B == '019200' and C_Settings.D == '8' and C_Settings.P == 'N' and C_Settings.S == '1':
                                ser.flushInput()
                                sleep(1)
                                #Get wind configuration
                                ser.write(C_Station.aWU)
                                sleep(.2)
                                Buff = ser.readline()
                                eor_log.info('Reading serial port for wind configuration: ' + Buff)
                                Buff = Buff[4:]
                                Buff = Buff[:-2]
                                buff = Buff
                                items = dict(item.split("=") for item in Buff.split(","))
                                C_Wind.R = items['R'] #Parameter selection
                                C_Wind.I = items['I'] #Update interval
                                C_Wind.A = items['A'] #Average Time
                                C_Wind.G = items['G'] #Min/Max calculation mode
                                C_Wind.U = items['U'] #Speed Units
                                C_Wind.N = items['N'] #NMEA formater
                                C_Wind.D = items['D'] #Direction offsedt
                                C_Wind.F = items['F'] #Sample Rate
                                #Test wind configuration
                                if C_Wind.G == '1' and C_Wind.U == 'K' and C_Wind.N == 'W' and C_Wind.F == '4':
                                    ser.flushInput()
                                    sleep(1)
                                    #Get Temp/Pressure configuration
                                    ser.write(C_Station.aTU)
                                    sleep(.2)
                                    Buff = ser.readline()
                                    eor_log.info('Reading serial port for temp configuration: ' + Buff)
                                    Buff = Buff[4:]
                                    Buff = Buff[:-2]
                                    buff = Buff
                                    items = dict(item.split("=") for item in Buff.split(","))
                                    C_Temp.R = items['R'] #Parameter selection
                                    C_Temp.I = items['I'] #Update Interval
                                    C_Temp.P = items['P'] #Pressure Units
                                    C_Temp.T = items['T'] #Temperature Units
                                    #Test temp/pressure configuration 
                                    if C_Temp.P == 'H' and C_Temp.T == 'C':
                                        ser.flushInput()
                                        sleep(1)
                                        #Get Rain configuration
                                        ser.write(C_Station.aRU)
                                        sleep(.2)
                                        Buff = ser.readline()
                                        eor_log.info('Reading serial port for rain configuration: ' + Buff)
                                        Buff = Buff[4:]
                                        Buff = Buff[:-2]
                                        buff = Buff
                                        items = dict(item.split("=") for item in Buff.split(","))
                                        C_Rain.R = items['R'] #Parameter selection
                                        C_Rain.I = items['I'] #Update interval
                                        C_Rain.U = items['U'] #Persipitation Unots
                                        C_Rain.S = items['S'] #Hail Units
                                        C_Rain.M = items['M'] #Auto send mode
                                        C_Rain.Z = items['Z'] #Counter reste method
                                        C_Rain.P = items['P'] #Enabled
                                        C_Rain.X = items['X'] #?
                                        C_Rain.Y = items['Y'] #?
                                        #Test Rain configuration
                                        if C_Rain.U =='M' and C_Rain.M == 'T' and C_Rain.Z == 'M' and C_Rain.P == 'Y':
                                            ser.flushInput()
                                            sleep(1)
                                            #Get Solar/Uv configuration
                                            ser.write(C_Station.aYU)
                                            sleep(.2)
                                            Buff = ser.readline()
                                            eor_log.info('Reading serial port for solar configuration: ' + Buff)
                                            Buff = Buff[4:]
                                            Buff = Buff[:-2]
                                            buff = Buff
                                            items = dict(item.split("=") for item in Buff.split(","))
                                            C_Solar.R = items['R'] #Parameter selection
                                            C_Solar.M = items['M'] #Factor
                                            if C_Solar.M <> '01045':
                                                eor_log.info("FRT Station Solar is out of spec :" + buff)

                                            ser.flushInput()
                                            sleep(1)
                                            ser.write(C_Station.aUV)
                                            sleep(.2)
                                            Buff = ser.readline()
                                            eor_log.info('Reading serial port for Uv configuration: ' + Buff)
                                            Buff = Buff[4:]
                                            Buff = Buff[:-2]
                                            buff = Buff
                                            
                                            items = dict(item.split("=") for item in Buff.split(","))
                                            C_UV.R = items['R'] #Parameter selection
                                            C_UV.M = items['M'] #Factor
                                            if C_UV.M <> '00010':
                                                eor_log.info("FRT Station UV is out of spec :" + buff)

                                            ##everything passed, can proceed    
                                            eor_log.info("Station ready for FRT Output")
                                            has_serial = True
                                        else:
                                            eor_log.critical("FRT Station rain is misconfigured :" + buff)
                                            has_serial = False                                    
                                    else:
                                        eor_log.critical("FRT Station temp is misconfigured :" + buff)
                                        has_serial = False
                                else:
                                    eor_log.critical("FRT Station wind is misconfigured :" + buff)
                                    has_serial = False
                            else:
                                eor_log.critical("FRT Station is misconfigured :" + buff)
                                has_serial = False
                        else:
                            eor_log.error("Error reading :" + Buff)
                            Buff = ''
                            sleep(1)
            except:
                eor_log.critical("Error reading FRT Station")
                has_serial = False
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

        db.close()
        if len(Station.User_Key) > 0:
            eosp.sendpushover(Station.App_Token, Station.User_Key, "EOR Server Stopped", 1)
    except Exception, e:
        print str(e)
        
    quit
    
if __name__ ==  '__main__':

    main()



        
