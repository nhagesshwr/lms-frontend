import sys
import os

# Add parent directory to path to find app module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine

try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    for table_name in tables:
        columns = inspector.get_columns(table_name)
        column_names = [c['name'] for c in columns]
        print(f"Table: {table_name} -> columns: {column_names}")
except Exception as e:
    print(f"Error checking schema: {e}")
