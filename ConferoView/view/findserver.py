__author__ = 'Sol'

import select
import socket
import sys
import pybonjour

regtype = "_confero._tcp."
timeout  = 5
queried  = []
resolved = []

confero_server_bonjour_info=[]

def query_record_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                          rrtype, rrclass, rdata, ttl):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        confero_server_bonjour_info[-1]['ip'] = socket.inet_ntoa(rdata)
        queried.append(True)


def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    confero_server_bonjour_info.append({'fullname': fullname,
                                        'hosttarget': hosttarget,
                                        'port': port
                                        })
#    print 'Resolved service:'
#    print '  fullname   =', fullname
#    print '  hosttarget =', hosttarget
#    print '  port       =', port

    query_sdRef = \
        pybonjour.DNSServiceQueryRecord(interfaceIndex = interfaceIndex,
                                        fullname = hosttarget,
                                        rrtype = pybonjour.kDNSServiceType_A,
                                        callBack = query_record_callback)

    try:
        while not queried:
            ready = select.select([query_sdRef], [], [], timeout)
            if query_sdRef not in ready[0]:
                print 'Query record timed out'
                break
            pybonjour.DNSServiceProcessResult(query_sdRef)
        else:
            queried.pop()
    finally:
        query_sdRef.close()

    resolved.append(True)


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if not (flags & pybonjour.kDNSServiceFlagsAdd):
        #print 'Service removed'
        return

    #print 'Service added; resolving'

    resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                                interfaceIndex,
                                                serviceName,
                                                regtype,
                                                replyDomain,
                                                resolve_callback)

    try:
        while not resolved:
            ready = select.select([resolve_sdRef], [], [], timeout)
            if resolve_sdRef not in ready[0]:
                print 'Resolve timed out'
                break
            pybonjour.DNSServiceProcessResult(resolve_sdRef)
        else:
            resolved.pop()
    finally:
        resolve_sdRef.close()

def findConferoViewServer():
    """
    Call this to get a list of server s. A list will be returned in most cases
    because the computer running the server have multiple ip's.
    :return:
    """
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                          callBack = browse_callback)

    try:
        try:
            ready = select.select([browse_sdRef], [], [])
            if browse_sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(browse_sdRef)
        except KeyboardInterrupt:
            pass
    finally:
        browse_sdRef.close()
    ip_index = 1
    valid_inputs = len(confero_server_bonjour_info)
    print 'Number of IPs returned by Bonjour:', valid_inputs
    if valid_inputs > 1:
        print
        print
        print '*** Confero View Server IP Address Selection Required ***'
        for i, o in enumerate(confero_server_bonjour_info):
            print '\t', i+1, ':', o['ip']
        print
        ok_ip_selected = False
        while ok_ip_selected is False:
            ip_index = raw_input(">> Enter the ID of the Server IP Address:")
            try:
                ip_index = int(ip_index)
                if ip_index>0 and ip_index<=valid_inputs:
                    ok_ip_selected = True
            except:
                pass

    print 'Bonjour IP Selected:', ip_index
    return confero_server_bonjour_info[ip_index-1]
