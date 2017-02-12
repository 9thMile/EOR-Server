# EOR-Server

This is a python script to process data for the EOS weather system. It is normally run on the station (https://www.raspberrypi.org/) and will read raw serial data output from the EOS station hardware and stores all data into a MYSQL database (https://www.mysql.com/). These are stored as serial sentences only in a proprietary format and would require additional processing to extract the climate data. 

The EOS-Server will then be used to process the data and store it in appropriate table structures that is more readable and flatens the responce. The service can also send messages back into the hardware to control it's functionality (turn on/off for example or report that the system is still alive).
