
from socket import *
import os
import sys
import struct
import time
import select
import binascii
import signal

ICMP_ECHO_REQUEST = 8
timeout_statement = "Request timed out."
list_of_times = []

class statistic_functions():
    def __init__(self, all_times):
        self.all_times_received = all_times
        self.all_filtered_times = [time for time in self.all_times_received if time != timeout_statement]

    def min_ping_times(self):
        return min(self.all_filtered_times)


    def max_ping_times(self):
        return max(self.all_filtered_times)

    def avg_ping_times(self):
        return float(sum(self.all_filtered_times) / len(self.all_filtered_times))

    def percent_lost(self):
        number_of_lost = 0
        for time in self.all_times_received:
            if time == timeout_statement:
                number_of_lost+=1
        return 100 * float(number_of_lost)/float(len(self.all_times_received))


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = ord(string[count+1]) * 256 + ord(string[count])
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    
    if countTo < len(string):
        csum = csum + ord(string[len(string) - 1])
        csum = csum & 0xffffffff
    
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
    
def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while 1:
        startedSelect = time.time()

        whatReady = select.select([mySocket], [], [], timeLeft)
        
        howLongInSelect = (time.time() - startedSelect)
        
        if whatReady[0] == []: # Timeout
            return timeout_statement
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        #Fill in start
        # len(recPacket) is returned at 36
        # The entire ICMP packet is 64 bits/8 Bytes long
        
        #Fetch the ICMP header from the IP packet
        # The ICMP is 8 bypes long, and starts at (160 Bit mark or 20 Byte Mark)
        icmpHeader = recPacket[20:28]

        # Then using the diagram from the assignment, 
        # I know there are 5 sections of the packet. Using unpack, correctly assign
        type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        if type != 8 and packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0] # Get one bit at 
            return timeReceived - timeSent

        #Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return timeout_statement

def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(str(header + data))
    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)
    
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):

    icmp = getprotobyname("icmp")
    # SOCK_RAW is a powerful socket type. For more details: http://sockraw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF # Return the current process i
    
    sendOnePing(mySocket, destAddr, myID)
    
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    
    mySocket.close()

    return delay

def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("Pinging " + dest + " using Python:")
    print("Press Ctrl + C to stop")
    print("")
    # Send ping requests to a server separated by approximately one second
    increment = 1
    while 1:
        try:
            delay = doOnePing(dest, timeout)
            list_of_times.append(delay)
            print "{0}. \t{1:.5f} ms".format(increment, delay * 1000)
        except ValueError as e:
            print "{0}. \t{1}".format(increment, delay)
        increment += 1
        time.sleep(1)# one second
    delay = 0 
    return delay

def exit_handler(signal, frame):
        stats = statistic_functions(list_of_times)
        print ""
        if(len(list_of_times) > 0):
            print "Min: {0:.5f} ms".format( (stats.min_ping_times() *1000 ) )
            print "Max: {0:.5f} ms".format( (stats.max_ping_times() *1000 ) )
            print "Avg: {0:.5f} ms".format( (stats.avg_ping_times() *1000 ) )
            print "Lost: {0:.3f}% ms".format(stats.percent_lost())
        else:
            print "No packets were collected before program exited"
        sys.exit(0)
signal.signal(signal.SIGINT, exit_handler)


# ping("localhost")
# ping("google.com")
# ping("sgp-1.valve.net")
ping("sto.valve.net")
# ping("10.1.1.1")
# ping('mc-central.net')
