import re
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

def get_engine(database="retail", server="localhost\\MSSQLSERVER03"):
    odbc = quote_plus(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={odbc}")


# build the engine once and reuse it — don't reconnect on every call
_engine = get_engine()


def validate_select_query(query):
    """Allow exactly one plain SELECT statement."""
    normalized = query.strip()
    if not normalized:
        raise ValueError("The query is empty.")

    if normalized.endswith(";"):
        normalized = normalized[:-1].rstrip()

    if ";" in normalized or "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise ValueError("Only one SELECT statement is allowed.")

    if not re.match(r"^SELECT\b", normalized, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")


def run_query(query, params=None):
    """Run a SQL query and return the result as a DataFrame."""
    validate_select_query(query)
    with _engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    return df

def get_schema(table_name):
    query = f'''
    select 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
    from INFORMATION_SCHEMA.COLUMNS
    where TABLE_SCHEMA = 'dbo'
    and TABLE_NAME = '{table_name}'
    order by ORDINAL_POSITION;
    '''
    schema = run_query(query)
    return schema


def get_tables():
        """Return all user tables in the dbo schema as a DataFrame."""
        query = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
            AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME;
        """
        return run_query(query)

# result = get_schema('orders')
# print(result)