"""
Script per mostrare lo schema del database PostgreSQL
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)

    print("\n" + "="*80)
    print("TABELLE NEL DATABASE")
    print("="*80 + "\n")

    for table_name in inspector.get_table_names():
        print(f"\n📋 Tabella: {table_name}")
        print("-" * 80)

        columns = inspector.get_columns(table_name)
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get('default') else ""
            print(f"  {col['name']:30} {col_type:20} {nullable:10}{default}")

        # Foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print("\n  Foreign Keys:")
            for fk in fks:
                print(f"    {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

        # Primary keys
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk['constrained_columns']:
            print(f"\n  Primary Key: {', '.join(pk['constrained_columns'])}")

    print("\n" + "="*80)
