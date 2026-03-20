import os
import subprocess
import shlex
from dotenv import load_dotenv
import time
from datetime import datetime
import tempfile
import gzip
import pandas as pd
import io
import re

# Load environment variables from .env file
load_dotenv()

def log(msg):
    """Print log message with timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# Store all credentials upfront
"""Load credentials for Redshift from .env"""
BASTION_HOST = os.getenv("BASTION_HOST")
BASTION_USER = os.getenv("BASTION_USER")

log("🔐 Using Redshift credentials from .env")
DB_HOST = os.getenv("REDSHIFT_HOST")
DB_NAME = os.getenv("REDSHIFT_NAME")
DB_USER = os.getenv("REDSHIFT_USER")
DB_PORT = os.getenv("REDSHIFT_PORT")
DB_PASS = os.getenv("REDSHIFT_PASS")

# Global variable to hold the persistent SSH connection
_bastion_process = None

def open_bastion_connection():
    """
    Open a persistent SSH connection to bastion host.
    The connection stays open for the lifetime of the application.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    global _bastion_process
    
    if _bastion_process is not None:
        log("✅ Bastion connection already open")
        return True
    
    try:
        log("🚀 Opening persistent bastion connection...")
        log(f"🔐 Connecting to {BASTION_USER}@{BASTION_HOST}...")
        
        # Start SSH connection with port forwarding or shell
        # We use a simple SSH connection that stays open
        _bastion_process = subprocess.Popen(
            ['ssh', '-N', f'{BASTION_USER}@{BASTION_HOST}'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(1)  # Give connection time to establish
        
        if _bastion_process.poll() is None:
            log("✅ Bastion connection established and ready")
            return True
        else:
            error = _bastion_process.stderr.read() if _bastion_process.stderr else "Unknown error"
            log(f"❌ Bastion connection failed: {error}")
            _bastion_process = None
            return False
    
    except Exception as e:
        log(f"❌ Error opening bastion connection: {str(e)}")
        _bastion_process = None
        return False


def close_bastion_connection():
    """
    Close the persistent bastion connection.
    """
    global _bastion_process
    
    if _bastion_process is not None:
        try:
            log("🔌 Closing bastion connection...")
            _bastion_process.terminate()
            _bastion_process.wait(timeout=5)
            _bastion_process = None
            log("✅ Bastion connection closed")
        except Exception as e:
            log(f"❌ Error closing bastion connection: {str(e)}")
            if _bastion_process:
                _bastion_process.kill()
                _bastion_process = None


def execute_query_to_dataframe(sql_query):
    """
    Execute a SQL query via bastion and return results as a pandas DataFrame.
    Uses the persistent bastion connection.
    
    Parameters:
        sql_query (str): SQL SELECT query to execute
    
    Returns:
        tuple: (success: bool, dataframe: pd.DataFrame or None, message: str)
    """
    log("� Starting query execution via bastion")
    total_start = time.perf_counter()
    
    try:
        if _bastion_process is None:
            error_msg = "❌ Bastion connection not open. Call open_bastion_connection() first."
            log(error_msg)
            return False, None, error_msg
        
        log(f"🔐 Executing query on Redshift database {DB_NAME} at {DB_HOST}...")
        log("Executing query via bastion...")
        exec_start = time.perf_counter()
        
        # Build the psql command with CSV output for Redshift
        # Use -f - to read from stdin and --single-transaction to process properly
        psql_cmd = f"PGPASSWORD='{DB_PASS}' psql -h {DB_HOST} -U {DB_USER} -d {DB_NAME} -p {DB_PORT} -q --csv -f -"
        
        # Execute query through SSH, passing SQL via stdin
        result = subprocess.run(
            ['ssh', f'{BASTION_USER}@{BASTION_HOST}', psql_cmd],
            input=sql_query,
            capture_output=True,
            text=True,
            timeout=1200
        )
        
        exec_time = time.perf_counter() - exec_start
        log(f"Query executed (took {exec_time:.2f}s)")
        
        # Debug output
        if result.stderr:
            log(f"DEBUG - Stderr: {result.stderr[:500]}")
        log(f"DEBUG - Stdout length: {len(result.stdout)}")
        log(f"DEBUG - Return code: {result.returncode}")
        
        if result.returncode == 0:
            # Parse CSV output to DataFrame
            log("Parsing results into DataFrame...")
            parse_start = time.perf_counter()
            
            # Remove any trailing newlines and parse CSV
            csv_output = result.stdout.strip()
            
            if not csv_output:
                df = pd.DataFrame()
            else:
                df = pd.read_csv(io.StringIO(csv_output))
            
            parse_time = time.perf_counter() - parse_start
            total_time = time.perf_counter() - total_start
            
            message = f"✅ Query successful!\n"
            message += f"   📊 Rows: {len(df)}\n"
            message += f"   📋 Columns: {len(df.columns)}\n"
            message += f"   ⏱️ Query time: {exec_time:.2f}s\n"
            message += f"   ⏱️ Parse time: {parse_time:.2f}s\n"
            message += f"   ⏱️ Total time: {total_time:.2f}s"
            
            log(message)
            return True, df, message
        else:
            error_msg = f"❌ Query failed with error:\n{result.stderr}"
            log(error_msg)
            return False, None, error_msg
    
    except subprocess.TimeoutExpired:
        error_msg = "❌ Query execution timed out (20 minutes)"
        log(error_msg)
        return False, None, error_msg
    except pd.errors.ParserError as e:
        error_msg = f"❌ Failed to parse query results: {str(e)}"
        log(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        log(error_msg)
        return False, None, error_msg