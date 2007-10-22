""" File catalog client for LCG File Catalog proxy service
"""

from DIRAC  import gLogger, gConfig, S_OK, S_ERROR
from DIRAC.Core.DISET.RPCClient import RPCClient

class LcgFileCatalogProxyClient:
  """ File catalog client for LCG File Catalog proxy service
  """

  def __init__(self, url = False, useCertificates = False):
    """ Constructor of the LCGFileCatalogProxy client class
    """
    self.name = 'LFCProxy'
    if not url:
      self.url = gConfig.getValue('Systems/DataManagement/Development/URLs/LcgFileCatalogProxy')
    else:
      self.url = url
    self.server = RPCClient(self.url,useCertificates,timeout = 120)

  def getName(self,DN=''):
    """ Get the file catalog type name
    """
    return self.name

  def __getattr__(self, name):
    self.call = name
    return self.execute

  def execute(self, *parms, **kws):
    """ Magic method dispatcher """
    try:
      result = self.server.callProxyMethod(self.call,parms,kws)
    except Exception,x:
      return S_ERROR('Exception while calling the server '+str(x))
    return result
