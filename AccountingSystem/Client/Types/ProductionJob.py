# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/AccountingSystem/Client/Types/Attic/ProductionJob.py,v 1.2 2008/05/06 20:51:38 acasajus Exp $
__RCSID__ = "$Id: ProductionJob.py,v 1.2 2008/05/06 20:51:38 acasajus Exp $"

from DIRAC.AccountingSystem.Client.Types.BaseAccountingType import BaseAccountingType

class ProductionJob( BaseAccountingType ):

  def __init__( self ):
    BaseAccountingType.__init__( self )
    self.definitionKeyFields = [ ( 'JobGroup', "VARCHAR(32)" ),
                                 ( 'ProductionType', 'VARCHAR(32)' ),
                                 ( 'JobType', 'VARCHAR(32)' ),
                                 ( 'Site', 'VARCHAR(32)' ),
                                 ( 'User', 'VARCHAR(32)' ),
                                 ( 'FinalState', 'VARCHAR(32)' )
                               ]
    self.definitionAccountingFields = [ ( 'CPUTime', "INT" ),
                                        ( 'NormCPUTime', "INT" ),
                                        ( 'ExecTime', "INT" ),
                                        ( 'InputData', 'INT' ),
                                        ( 'OutputData', 'INT' ),
                                        ( 'InputEvents', 'INT' ),
                                        ( 'OutputEvents', 'INT' )
                                      ]
    self.checkType()