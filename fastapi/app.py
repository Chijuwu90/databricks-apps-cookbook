"""
Main FastAPI application.

This module creates and configures the FastAPI application.
"""
import os
from contextlib import asynccontextmanager
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, Query

from routes import api_router
from services.db.connector import close_connections
from errors.handlers import register_exception_handlers

from databricks import sql
from databricks.sdk.core import Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup code (if any)
    yield
    # Shutdown code
    close_connections()


# Create the main FastAPI application
app = FastAPI(
    title="FastAPI & Databricks Apps",
    description="A simple FastAPI application example for Databricks Apps runtime",
    version="1.0.0",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# Include the API router
app.include_router(api_router)

# Connection to SQL warehouse
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID") or None
databricks_cfg = Config()

# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "app": "Databricks FastAPI Example",
        "message": "Welcome to the Databricks FastAPI example app",
        "docs": "/docs",
    }


@app.get("/hello")
async def root() -> Dict[str, str]:
    return {
        "app": "Databricks FastAPI Example",
        "message": "Hello World"
    }


def get_connection(warehouse_id: str):
    http_path = f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}"
    return sql.connect(
        server_hostname=databricks_cfg.host,
        http_path=http_path,
        credentials_provider=lambda: databricks_cfg.authenticate,
    )


def query(sql_query: str, warehouse_id: str, as_dict: bool = True) -> List[Dict]:
    conn = get_connection(warehouse_id)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            result = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in result]

    except Exception as e:
        raise Exception(f"DBSQL Query Failed: {str(e)}")


@app.get("/api/v1/table")
def table(
    sql_query: str = Query("select * from ju_demos.dbdemos_dlt_loans.cleaned_new_txs limit 10", description="SQL query to execute"),
):
    results = None
    try:
        results = query(sql_query, warehouse_id=DATABRICKS_WAREHOUSE_ID)
    except Exception as e:
        raise Exception(f"FastAPI Request Failed: {str(e)}")

    return {"results": results}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)