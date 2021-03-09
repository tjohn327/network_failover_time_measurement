# Refer https://csce.ucmss.com/cr/books/2018/LFS/CSREA2018/CSC3530.pdf
# for more details about the method.
# Run this using python 2

import dpkt
import socket
import os
import select
import time
import signal

run = True

def sigHandler(signum, frame):
    print "\nTerminating..."
    run = False    

def createEchoRequest(id, seq):  
    echo = dpkt.icmp.ICMP.Echo()
    echo.id = id
    echo.seq = seq
    echo.data = 64 * 'Q' #payload
    icmp = dpkt.icmp.ICMP()
    icmp.type = dpkt.icmp.ICMP_ECHO
    icmp.data = echo
    return icmp

def getSequence(buf):
    ip = dpkt.ip.IP(buf)
    icmp = ip.data
    echo = icmp.data    
    return echo.seq

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigHandler)
    signal.signal(signal.SIGTERM, sigHandler)

    #Change host and timeout 
    #timeout should be greater that the latency of the highest latency path.
    host = "192.168.1.101"
    timeout = 0.01 #timeout in seconds

    pid = os.getgid()
    if pid > 65535:
        pid = 0
    
    seq = 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_ICMP)
    sock.connect((host, 1))

    state = 0
    failover = False
    discardedPackets = []
    packetsLost = 0
    icmp = createEchoRequest(pid,seq)
    start = time.time()
    print "Test Started"
    print "Sending pings to ", host
    sock.send(str(icmp))    

    while run:
        if seq >= 65535:
            #reset sequence
            print "\nSeq exceeded, starting over"
            seq = 0
            packetsLost = 0
            discardedPackets = []
            state = 0

        s,_,_ = select.select([sock],[],[],timeout)
        if s == []:
            if state == 0:
                state = 1
                continue

            if state == 1:                
                state = 2

            if state == 2:
                state = 3

            if seq not in discardedPackets:
                discardedPackets.append(seq)
            packetsLost += 1
            seq += 1
            sock.send(str(createEchoRequest(pid, seq)))


        elif sock in s:
            buf = sock.recv(1024)
            receivedSeq = getSequence(buf)
            if state == 0:
                if receivedSeq in discardedPackets:
                    continue

            if state == 1 or state == 2:
                if receivedSeq in discardedPackets:
                    continue
                else:
                    state = 0


            if state == 3:
                if receivedSeq in discardedPackets:
                    continue
                else:
                    state = 0
                    failoverTime = (packetsLost * timeout) + timeout
                    print "Failover detected, Time: ", failoverTime*1000, " ms"
                    packetsLost = 0
            seq += 1
            sock.send(str(createEchoRequest(pid, seq)))
               
