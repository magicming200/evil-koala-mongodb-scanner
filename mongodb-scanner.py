#!/usr/bin/env python
#coding:utf-8

"""
@software: 邪恶考拉mongodb空口令扫描器 v1.0
@author: magicming
"""

import threading
from pymongo import MongoClient
import time
import Queue
import getopt
import sys
import socket
import struct

class MongodbScanner:
    def __init__(self):
        self.success_count = 0
        self.conn_timeout = 1
        self.thread_timeout = 45
        self.lock = threading.Lock()
        self.queue=Queue.Queue()

    def ipToNum(self,ip):
        packedIP = socket.inet_aton(ip)
        return struct.unpack("!L", packedIP)[0]

    def numToIp(self,num):
        return socket.inet_ntoa(struct.pack('!L', num))

    def getIpList(self,ip):
        errMsg = 'format is wrong,correct usage:\n' \
                 'python mongodb-scanner.py -h 10.34\n' \
                 'python mongodb-scanner.py -h 192.168.10\n' \
                 'python mongodb-scanner.py -h 192.168.1.1 -p 27017 -m 100\n' \
                 'python mongodb-scanner.py -h ip.txt\n'
        gIpList = []
        if '.txt' in ip:  # ip文件 ip.txt
            try:
                ipFile = open(ip, 'r')
                for ipf in ipFile:
                    gIpList.append(ipf.strip())
                ipFile.close()
            except Exception, e:
                print e
                exit()
        elif '-' in ip:  # ip段 192.168.1.1-192.168.10.200
            ipRange = ip.split('-')
            ipStart = long(self.ipToNum(ipRange[0]))
            ipEnd = long(self.ipToNum(ipRange[1]))
            ipCount = ipEnd - ipStart
            if ipCount >= 0 and ipCount <= 65536:
                for ipNum in range(ipStart, ipEnd + 1):
                    gIpList.append(self.numToIp(ipNum))
            else:
                print errMsg
                exit()
        else:  # ip 192.168  192.168.1  192.168.1.1
            ipSplit = ip.split('.')
            section = len(ipSplit)
            if section == 2:
                for c in range(1, 255):
                    for d in range(1, 255):
                        ip = '%s.%s.%d.%d' % (ipSplit[0], ipSplit[1], c, d)
                        gIpList.append(ip)
            elif section == 3:
                for d in range(1, 255):
                    ip = '%s.%s.%s.%d' % (ipSplit[0], ipSplit[1], ipSplit[2], d)
                    gIpList.append(ip)
            elif section == 4:
                gIpList.append(ip)
            else:
                print errMsg
                exit()
        return gIpList

    def prepareQueue(self,ips):
        for ip in ips:
            self.queue.put(ip)


    def clearResult(self):
        file = open(self.fileout, 'w')
        file.truncate()
        file.close()


    def run(self):
        for i in range(self.mcount):
            try:
                t = threading.Thread(target=self.threadScan, name=str(i))
                t.setDaemon(True)
                t.start()
            except:
                pass
        tmp_count = 0
        i = 0
        while True:
            #print 'activeCount '+str(threading.activeCount())
            time.sleep(1)
            ac_count = threading.activeCount()
            if ac_count < self.mcount and ac_count == tmp_count:#防止出现僵尸线程
                i+=1
            else:
                i = 0
            tmp_count = ac_count
            if (self.queue.empty() and threading.activeCount() <= 1) or i>self.thread_timeout:
                self.lock.acquire()
                print '----------------------------------------'
                if self.success_count>0:
                    print 'Scan Result: success '+str(self.success_count) + ', see '+self.fileout
                else:
                    print 'Scan Result: success ' + str(self.success_count)
                self.lock.release()
                break

    def threadScan(self):
        while not self.queue.empty():
            ip = self.queue.get()
            try:
                self.lock.acquire()
                print 'try to connect ' + ip + ':' + str(self.port)
                self.lock.release()
                client = MongoClient(ip, self.port, connectTimeoutMS=self.conn_timeout*1000, socketTimeoutMS=self.conn_timeout*1000,waitQueueTimeoutMS=self.conn_timeout*1000)
                client.server_info()
                client.database_names()
                client.close()
                self.lock.acquire()
                print '########## ' + ip + ':' + str(self.port) + ' Connect Success!'
                file = open(self.fileout, 'a')
                file.write(ip + ':' + str(self.port) + '\n')
                file.close()
                self.success_count +=1
                self.lock.release()
            except Exception,e:
                self.lock.acquire()
                print e
                self.lock.release()

if __name__=='__main__':
    ipcmd=''
    port = 27017
    mcount = 200
    fileout = 'result.txt'

    options, args = getopt.getopt(sys.argv[1:], 'h:p:m:')
    for opt, arg in options:
        if opt == '-h':
            ipcmd = arg
        elif opt == '-p':
            port = int(arg)
        elif opt == '-m':
            mcount = int(arg)

    mo = MongodbScanner()
    mo.port = port
    mo.mcount = mcount
    mo.fileout = fileout
    mo.prepareQueue(mo.getIpList(ipcmd))
    mo.clearResult()
    mo.run()