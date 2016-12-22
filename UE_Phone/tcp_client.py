import socket 
import sys

sock= socket.socket(socket.AF_INET,socket.SOCK_STREAM)

serveraddress=('dsplab-wc3.local',10000)
print >>sys.stderr,'conncting to %s port %s ' %serveraddress
sock.connect(serveraddress)

try:
    
    message='My first message, so it will be repeated'
    print >>sys.stderr,'sending "%s"' %message
    sock.sendall(message)
    
    amount_received = 0
    amount_expected =len(message)
    
    while amount_received <amount_expected:
        data =sock.recv(16)
        amount_received +=len(data)
        print >>sys.stderr,'received "%s"' %data
        
finally:
    print >>sys.stderr,'closing socket'
    sock.close()        
    
    
    
