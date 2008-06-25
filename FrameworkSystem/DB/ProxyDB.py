########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/FrameworkSystem/DB/ProxyDB.py,v 1.1 2008/06/25 20:00:50 acasajus Exp $
########################################################################
""" ProxyRepository class is a front-end to the proxy repository Database
"""

__RCSID__ = "$Id: ProxyDB.py,v 1.1 2008/06/25 20:00:50 acasajus Exp $"

import time
from DIRAC  import gConfig, gLogger, S_OK, S_ERROR
from DIRAC.Core.Base.DB import DB
from DIRAC.Core.Security.X509Request import X509Request
from DIRAC.Core.Security.X509Chain import X509Chain
from DIRAC.Core.Security.MyProxy import MyProxy
from DIRAC.Core.Security.VOMS import VOMS
from DIRAC.Core.Security import CS

class ProxyDB(DB):

  def __init__(self, requireVoms = False,
               useMyProxy = False,
               MyProxyServer = False,
               maxQueueSize = 10 ):
    DB.__init__(self,'ProxyDB','Framework/ProxyDB',maxQueueSize)
    self.__defaultRequestLifetime = 300 # 5min
    self.__vomsRequired = requireVoms
    self.__useMyProxy = useMyProxy
    self.__MyProxyServer = MyProxyServer
    retVal = self.__initializeDB()
    if not retVal[ 'OK' ]:
      raise Exception( "Can't create tables: %s" % retVal[ 'Message' ])

  def __initializeDB(self):
    """
    Create the tables
    """
    retVal = self._query( "show tables" )
    if not retVal[ 'OK' ]:
      return retVal

    tablesInDB = [ t[0] for t in retVal[ 'Value' ] ]
    tablesD = {}

    if 'ProxyDB_Requests' not in tablesInDB:
      tablesD[ 'ProxyDB_Requests' ] = { 'Fields' : { 'Id' : 'INTEGER AUTO_INCREMENT NOT NULL',
                                                     'UserDN' : 'VARCHAR(255) NOT NULL',
                                                     'UserGroup' : 'VARCHAR(255) NOT NULL',
                                                     'Pem' : 'BLOB',
                                                     'ExpirationTime' : 'DATETIME'
                                                   },
                                        'PrimaryKey' : 'Id'
                                      }
    if 'ProxyDB_Proxies' not in tablesInDB:
      tablesD[ 'ProxyDB_Proxies' ] = { 'Fields' : { 'UserDN' : 'VARCHAR(255) NOT NULL',
                                                    'UserGroup' : 'VARCHAR(255) NOT NULL',
                                                    'Pem' : 'BLOB',
                                                    'ExpirationTime' : 'DATETIME',
                                                    'PersistentFlag' : 'ENUM ("True","False") NOT NULL DEFAULT "True"',
                                                  },
                                      'PrimaryKey' : [ 'UserDN', 'UserGroup' ]
                                     }
    return self._createTables( tablesD )

  def generateDelegationRequest( self, proxyChain, userDN, userGroup ):
    """
    Generate a request  and store it for a given proxy Chain
    """
    retVal = self._getConnection()
    if not retVal[ 'OK' ]:
      return retVal
    connObj = retVal[ 'Value' ]
    retVal = proxyChain.generateProxyRequest()
    if not retVal[ 'OK' ]:
      return retVal
    request = retVal[ 'Value' ]
    retVal = request.dumpAll()
    if not retVal[ 'OK' ]:
      return retVal
    reqStr = retVal[ 'Value' ]
    cmd = "INSERT INTO `ProxyDB_Requests` ( Id, UserDN, UserGroup, Pem, ExpirationTime )"
    cmd += " VALUES ( 0, '%s', '%s', '%s', TIMESTAMPADD( SECOND, %s, NOW() ) )" % ( userDN,
                                                                              userGroup,
                                                                              reqStr,
                                                                              self.__defaultRequestLifetime )
    retVal = self._update( cmd, conn = connObj )
    if not retVal[ 'OK' ]:
      return retVal
    #99% of the times we will stop here
    if 'lastRowId' in retVal:
      return S_OK( { 'id' : retVal['lastRowId'], 'request' : reqStr } )
    #If the lastRowId hack does not work. Get it by hand
    retVal = self._query( "SELECT Id FROM `ProxyDB_Requests` WHERE Pem='%s'" % reqStr )
    if not retVal[ 'OK' ]:
      return retVal
    data = retVal[ 'Value' ]
    if len( data ) == 0:
      return S_ERROR( "Insertion of the request in the db didn't work as expected" )
    #Here we go!
    return S_OK( { 'id' : data[0][0], 'request' : reqStr } )

  def retrieveDelegationRequest( self, requestId, userDN, userGroup ):
    """
    Retrieve a request from the DB
    """
    cmd = "SELECT Pem FROM `ProxyDB_Requests` WHERE Id = %s AND UserDN = '%s' and UserGroup = '%s'" % ( requestId,
                                                                                                userDN,
                                                                                                userGroup )
    retVal = self._query( cmd)
    if not retVal[ 'OK' ]:
      return retVal
    data = retVal[ 'Value' ]
    if len( data ) == 0:
      return S_ERROR( "No requests with id %s" % requestId )
    request = X509Request()
    retVal = request.loadAllFromString( data[0][0] )
    if not retVal[ 'OK' ]:
      return retVal
    return S_OK( request )

  def purgeExpiredRequests( self ):
    """
    Purge expired requests from the db
    """
    cmd = "DELETE FROM `ProxyDB_Requests` WHERE ExpirationTime < NOW()"
    return self._update( cmd )

  def deleteRequest( self, requestId ):
    """
    Delete a request from the db
    """
    cmd = "DELETE FROM `ProxyDB_Requests` WHERE Id=%s" % requestId
    return self._update( cmd )

  def __checkVOMSisAlignedWithGroup( self, userGroup, chain ):
    voms = VOMS()
    if not voms.vomsInfoAvailable():
      if self.__vomsRequired:
        return S_ERROR( "VOMS is required, but it's not available" )
      gLogger.warn( "voms-proxy-info is not available" )
      return S_OK()
    retVal = voms.getVOMSAttributes( chain )
    if not retVal[ 'OK' ]:
      return retVal
    attr = retVal[ 'Value' ]
    validVOMSAttrs = CS.getVOMSAttributeForGroup( userGroup )
    if len( attr ) == 0 or attr[0] in validVOMSAttrs:
      return S_OK( 'OK' )
    msg = "VOMS attributes are not aligned with dirac group"
    msg += "Attributes are %s and allowed are %s for group %s" % ( attr, validVOMSAttrs, userGroup )
    return S_ERROR( msg )

  def completeDelegation( self, requestId, userDN, userGroup, delegatedPem ):
    """
    Complete a delegation and store it in the db
    """
    retVal = self.retrieveDelegationRequest( requestId, userDN, userGroup )
    if not retVal[ 'OK' ]:
      return retVal
    request = retVal[ 'Value' ]
    chain = X509Chain( keyObj = request.getPKey() )
    retVal = chain.loadChainFromString( delegatedPem )
    if not retVal[ 'OK' ]:
      return retVal
    retVal = chain.isValidProxy()
    if not retVal[ 'OK' ]:
      return retVal
    if not retVal[ 'Value' ]:
      return S_ERROR( "Chain received is not a valid proxy: %s" % retVal[ 'Message' ] )

    retVal = request.checkChain( chain )
    if not retVal[ 'OK' ]:
      return retVal
    if not retVal[ 'Value' ]:
      return S_ERROR( "Received chain does not match request: %s" % retVal[ 'Message' ] )

    retVal = self.__checkVOMSisAlignedWithGroup(userGroup, chain )
    if not retVal[ 'OK' ]:
      return retVal

    #TODO:Check for VOMS and make sure it's aligned
    retVal = self.storeProxy( userDN, userGroup, chain )
    if not retVal[ 'OK' ]:
      return retVal
    return self.deleteRequest( requestId )

  def storeProxy(self, userDN, userGroup, chain ):
    """ Store user proxy into the Proxy repository for a user specified by his
        DN and group.
    """
    retVal = chain.getRemainingSecs()
    if not retVal[ 'OK' ]:
      return retVal
    remainingSecs = retVal[ 'Value' ]
    retVal = chain.getIssuerCert()
    if not retVal[ 'OK' ]:
      return retVal
    proxyIdentityDN = retVal[ 'Value' ].getSubjectDN()[ 'Value' ]
    if not userDN == proxyIdentityDN:
      msg = "Mismatch in the user DN"
      vMsg = "Proxy says %s and credentials are %s" % ( proxyIdentityDN, userDN )
      gLogger.error( msg, vMsg )
      return S_ERROR(  "%s. %s" % ( msg, vMsg ) )
    retVal = chain.getDIRACGroup()
    if not retVal[ 'OK' ]:
      return retVal
    proxyGroup = retVal[ 'Value' ]
    if not proxyGroup:
      proxyGroup = CS.getDefaultUserGroup()
    if not userGroup == proxyGroup:
      msg = "Mismatch in the user group"
      vMsg = "Proxy says %s and credentials are %s" % ( proxyGroup, userGroup )
      gLogger.error( msg, vMsg )
      return S_ERROR(  "%s. %s" % ( msg, vMsg ) )
    gLogger.info( "Storing proxy for credentials %s (%s secs)" %( proxyIdentityDN,remainingSecs ) )

    # Check what we have already got in the repository
    cmd = "SELECT TIMESTAMPDIFF( SECOND, NOW(), ExpirationTime ) FROM `ProxyDB_Proxies` WHERE UserDN='%s' AND UserGroup='%s'" % ( userDN,
                                                                                                               userGroup)
    result = self._query( cmd )
    if not result['OK']:
      return result
    # check if there is a previous ticket for the DN
    data = result[ 'Value' ]
    insert = True
    if data:
      insert = False
      remainingSecsInDB = result['Value'][0][0]
      if remainingSecs <= remainingSecsInDB:
        gLogger.info( "Proxy stored is longer than uploaded, omitting.", "%s in uploaded, %s in db" % (remainingSecs, remainingSecsInDB ) )
        return S_OK()

    pemChain = chain.dumpAllToString()['Value']
    if insert:
      cmd = "INSERT INTO `ProxyDB_Proxies` ( UserDN, UserGroup, Pem, ExpirationTime, PersistentFlag ) VALUES "
      cmd += "( '%s', '%s', '%s', TIMESTAMPADD( SECOND, %s, NOW() ), 'False' )" % ( userDN,
                                                                                  userGroup,
                                                                                  pemChain,
                                                                                  remainingSecs )
    else:
      cmd = "UPDATE `ProxyDB_Proxies` set Pem='%s', ExpirationTime = TIMESTAMPADD( SECOND, %s, NOW() ) WHERE UserDN='%s' AND UserGroup='%s'" % ( pemChain,
                                                                                                                                                remainingSecs,
                                                                                                                                                userDN,
                                                                                                                                                userGroup)

    return self._update( cmd )

  def purgeExpiredProxies( self ):
    """
    Purge expired requests from the db
    """
    cmd = "DELETE FROM `ProxyDB_Proxies` WHERE ExpirationTime < NOW() and PersistentFlag = 'False'"
    return self._update( cmd )

  def deleteProxy( self, userDN, userGroup ):
    """ Remove proxy of the given user from the repository
    """

    req = "DELETE FROM `ProxyDB_Proxies` WHERE UserDN='%s' AND UserGroup='%s'" % ( userDN,
                                                                                   userGroup )
    return self._update(req)

  def __getPemAndTimeLeft( self, userDN, userGroup ):
    cmd = "SELECT Pem, TIMESTAMPDIFF( SECOND, NOW(), ExpirationTime ) from `ProxyDB_Proxies`"
    cmd += "WHERE UserDN='%s' AND UserGroup = '%s' AND TIMESTAMPDIFF( SECOND, NOW(), ExpirationTime ) > 0" % ( userDN, userGroup )
    retVal = self._query(cmd)
    if not retVal['OK']:
      return retVal
    data = retVal[ 'Value' ]
    if len( data ) == 0:
      return S_ERROR( "%s@%s has no proxy registered" % ( userDN, userGroup ) )
    return S_OK( ( data[0][0], data[0][1] ) )

  def renewFromMyProxy( self, userDN, userGroup, lifeTime = False, chain = False ):
    if not lifeTime:
      lifeTime = 43200
    if not self.__useMyProxy:
      return S_ERROR( "myproxy is disabled" )
    #Get the chain
    if not chain:
      retVal = self.__getPemAndTimeLeft( userDN, userGroup )
      if not retVal[ 'OK' ]:
        return retVal
      pemData = retVal[ 'Value' ][0]
      chain = X509Chain()
      retVal = chain.loadProxyFromString( pemData )
      if not retVal[ 'OK' ]:
        return retVal

    myProxy = MyProxy( server = self.__MyProxyServer )
    retVal = myProxy.getDelegatedProxy( chain, lifeTime )
    if not retVal[ 'OK' ]:
      return retVal
    chain = retVal[ 'Value' ]
    self.storeProxy( userDN, userGroup, chain )
    return S_OK( chain )



  def getProxy( self, userDN, userGroup, requiredLifeTime = False ):
    """ Get proxy string from the Proxy Repository for use with userDN
        in the userGroup
    """

    retVal = self.__getPemAndTimeLeft( userDN, userGroup )
    if not retVal[ 'OK' ]:
      return retVal
    pemData = retVal[ 'Value' ][0]
    timeLeft = retVal[ 'Value' ][1]
    chain = X509Chain()
    retVal = chain.loadProxyFromString( pemData )
    if not retVal[ 'OK' ]:
      return retVal
    if requiredLifeTime:
      if timeLeft < requiredLifeTime:
        retVal = self.renewFromMyProxy( userDN, userGroup, lifeTime = requiredLifeTime, chain = chain )
        if not retVal[ 'OK' ]:
          return S_ERROR( "Can't get a proxy for %s seconds: %s" % ( requiredLifeTime, retVal[ 'Message' ] ) )
        chain = retVal[ 'Value' ]
    #Proxy is invalid for some reason, let's delete it
    if not chain.isValidProxy()['Value']:
      self.deleteProxy( userDN, userGroup )
      return S_ERROR( "%s@%s has no proxy registered" % ( userDN, userGroup ) )
    return S_OK( chain )

  def getUsers( self, validSecondsLeft = 0 ):
    """ Get all the distinct users from the Proxy Repository. Optionally, only users
        with valid proxies within the given validity period expressed in seconds
    """

    cmd = "SELECT UserDN, UserGroup, ExpirationTime, PersistentFlag FROM `ProxyDB_Proxies`"
    if validSecondsLeft:
      cmd += " WHERE ( NOW() + INTERVAL %d SECOND ) < ExpirationTime" % validSecondsLeft
    retVal = self._query( cmd )
    if not retVal[ 'OK' ]:
      return retVal
    data = []
    for record in retVal[ 'Value' ]:
      data.append( { 'DN' : record[0], 'group' : record[1], 'expirationtime' : record[2] } )
    return S_OK( data )

  def getCredentialsAboutToExpire( self, requiredSecondsLeft, onlyPersistent = True ):
    cmd = "SELECT UserDN, UserGroup, ExpirationTime, PersistentFlag FROM `ProxyDB_Proxies`"
    cmd += " WHERE TIMESTAMPDIFF( SECOND, NOW(), ExpirationTime ) < %s" % requiredSecondsLeft
    if onlyPersistent:
      cmd += " AND PersistentFlag = 'True'"
    return self._query( cmd )

  def setPersistencyFlag( self, userDN, userGroup, flag = True ):
    """ Set the proxy PersistentFlag to the flag value
    """

    if flag:
      sqlFlag="True"
    else:
      sqlFlag="False"
    cmd = "UPDATE `ProxyDB_Proxies` SET PersistentFlag='%s' WHERE UserDN='%s' AND UserGroup='%s'" % ( sqlFlag,
                                                                                            userDN,
                                                                                            userGroup )

    return self._update(cmd)
