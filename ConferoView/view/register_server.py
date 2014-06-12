__author__ = 'Sol'
import select
import pybonjour

class ConferoBonjourService(object):
    name = "Confero View Server"
    regtype = "_confero._tcp."
    port = 8888

    def __init__(self):
        self.sdRef = pybonjour.DNSServiceRegister(name = self.name,
                                     regtype = self.regtype,
                                     port = self.port,
                                     callBack = self._register_callback)
        self.tornado_callback = None

    def _register_callback(self, sdRef, flags, errorCode, name, regtype, domain):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            #print 'Registered service:'
            #print '  name    =', name
            #print '  regtype =', regtype
            #print '  domain  =', domain
            pass

    def checkForDaemonRequests(self):
            ready = select.select([self.sdRef], [], [], 0)
            if self.sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(self.sdRef)

    def close(self):
        self.sdRef.close()
        self.sdRef = None
        if self.tornado_callback:
            self.tornado_callback.stop()
            self.tornado_callback = None

    def __del__(self):
        if self.sdRef:
            self.close()