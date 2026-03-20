"""

Xerenity python library
"""

__version__ = "0.2.2"
__author__ = 'Xerenity'

from xerenity.connection.db import Connection
from xerenity.search.series import Series
from xerenity.loans.loans import Loans
from xerenity.marks.marks import Marks


class Xerenity:

    def __init__(self, username, password):
        self.username: username
        self.password = password
        self.conn = Connection()
        self.conn.login(username=username, password=password)
        self.series: Series = Series(connection=self.conn)
        self.loans: Loans = Loans(connection=self.conn)
        self.marks: Marks = Marks(connection=self.conn)
