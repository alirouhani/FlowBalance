from sqlalchemy import create_engine
import pandas as pd
from .base import BaseLoader
from .pandas_io import PandasLoader
from flowbalance.core.entities import Network

class SQLLoader(BaseLoader):
    def __init__(self, connection_string: str):
        """
        Initializes a secure connection to any SQL database engine.
        Example: 'sqlite:///local_network.db'
        """
        self.engine = create_engine(connection_string)

    def load_network(self) -> Network:
        # 1. Query the database tables directly into temporary DataFrames
        with self.engine.connect() as connection:
            df_nodes = pd.read_sql("SELECT * FROM nodes", connection)
            df_edges = pd.read_sql("SELECT * FROM edges", connection)
            df_commodities = pd.read_sql("SELECT * FROM commodities", connection)

        # 2. Re-use the PandasLoader mapping logic to avoid duplicate code
        pandas_adapter = PandasLoader(df_nodes, df_edges, df_commodities)
        return pandas_adapter.load_network()