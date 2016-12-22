#!/usr/bin/env python

import socket


sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        
serveraddress= ('',12004)
sock.bind(serveraddress)
print 'Connected to listen '
sock.listen(10)
        
while True:
    connection,client_address = sock.accept()
            
    try:
        print 'connection from',client_address
                
                
        while True:
            data = connection.recv(16)
            if data:
                print "received data is --->%s" %data
                print'sending data to client'
                connection.sendall('T&A')
               
                break
            else:
                print 'insufficient data for tuning'
                break
                #connection.close()
    finally:
        connection.close()

