# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/AccountingSystem/Client/Types/Attic/WMSJob.py,v 1.7 2008/05/06 20:51:38 acasajus Exp $
__RCSID__ = "$Id: WMSJob.py,v 1.7 2008/05/06 20:51:38 acasajus Exp $"

from DIRAC.AccountingSystem.Client.Types.BaseAccountingType import BaseAccountingType

from DIRAC                                                  import gConfig

class WMSJob( BaseAccountingType ):

  def __init__( self ):
    BaseAccountingType.__init__( self )
    self.definitionKeyFields = [ ( 'JobGroup', "VARCHAR(32)" ),
                                 ( 'JobType', 'VARCHAR(32)' ),
                                 ( 'JobClass', 'VARCHAR(32)' ),
                                 ( 'Site', 'VARCHAR(32)' ),
                                 ( 'ProcType', 'VARCHAR(32)' ),
                                 ( 'FinalMajorStatus', 'VARCHAR(32)' ),
                                 ( 'FinalMinorStatus', 'VARCHAR(64)' )
                               ]
    self.definitionAccountingFields = [ ( 'CPUTime', "INT" ),
                                        ( 'NormCPUTime', "INT" ),
                                        ( 'ExecTime', "INT" ),
                                        ( 'InputData', 'INT' ),
                                        ( 'OutputData', 'INT' ),
                                        ( 'DiskSpace', 'INT' ),
                                        ( 'InputSandBox', 'INT' ),
                                        ( 'OutputSandBox', 'INT' )
                                      ]
    self.checkType()
    #Fill the setup
    self.setValueByKey( "Setup", gConfig.getValue( "/DIRAC/Setup", "unknown" ) )
    #Fill the site
    self.setValueByKey( "Site", gConfig.getValue( "/LocalSite/Site", "DIRAC.unknown.no" ) )