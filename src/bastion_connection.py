import os
from dotenv import load_dotenv
import time
from datetime import datetime
import pandas as pd
import io
import re
from clickhouse_driver import Client
import subprocess
import socket
import threading

# Load environment variables from .env file
load_dotenv()

def log(msg):
    """Print log message with timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# Store all credentials upfront
# SSH tunnel credentials (public ClickHouse host)
"""Load credentials for SSH tunnel from .env"""
log("🔐 Using SSH tunnel credentials from .env")
SSH_HOST = os.getenv("CLICKHOUSE_HOST")  # 148.113.47.241
SSH_USER = os.getenv("CLICKHOUSE_USER")  # ubuntu

# ClickHouse internal credentials (accessed through SSH tunnel)
"""Load credentials for ClickHouse from .env"""
log("🔐 Using ClickHouse credentials from .env")
CLICKHOUSE_INTERNAL_HOST = os.getenv("CLICKHOUSE_INTERNAL_HOST")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")

# Global variables for tunnel and client
_clickhouse_client = None
_ssh_tunnel_process = None
_local_bind_port = None

# ============================================================================
# ClickHouse Connection Functions
# ============================================================================

def find_available_port(start_port=9001):
    """Find an available local port for SSH tunnel"""
    port = start_port
    while port < 65535:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            port += 1
    raise RuntimeError("No available ports found")


def open_clickhouse_connection():
    """
    Open a ClickHouse connection via SSH tunnel.
    
    The process:
    1. SSH into CLICKHOUSE_HOST (148.113.47.241) as ubuntu
    2. Create a port forward to CLICKHOUSE_INTERNAL_HOST:CLICKHOUSE_PORT (10.12.0.10:9000)
    3. Connect to ClickHouse through the tunnel on localhost:local_port
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    global _clickhouse_client, _ssh_tunnel_process, _local_bind_port
    
    if _clickhouse_client is not None:
        log("✅ ClickHouse connection already open")
        return True
    
    try:
        log("🚀 Opening ClickHouse connection via SSH tunnel...")
        log(f"🔐 SSH tunnel: {SSH_USER}@{SSH_HOST} -> {CLICKHOUSE_INTERNAL_HOST}:{CLICKHOUSE_PORT}")
        
        # Find an available local port
        _local_bind_port = find_available_port()
        log(f"📡 Using local port {_local_bind_port} for tunnel")
        
        # Build SSH tunnel command
        # ssh -L local_port:remote_host:remote_port user@ssh_host -N
        tunnel_cmd = [
            'ssh',
            '-L', f'127.0.0.1:{_local_bind_port}:{CLICKHOUSE_INTERNAL_HOST}:{CLICKHOUSE_PORT}',
            '-N',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            f'{SSH_USER}@{SSH_HOST}'
        ]
        
        log(f"🔌 Starting SSH tunnel: {' '.join(tunnel_cmd)}")
        
        # Start SSH tunnel process
        _ssh_tunnel_process = subprocess.Popen(
            tunnel_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give tunnel time to establish
        log("⏳ Waiting for SSH tunnel to establish...")
        time.sleep(3)
        
        # Check if tunnel process is still running
        if _ssh_tunnel_process.poll() is not None:
            stderr = _ssh_tunnel_process.stderr.read() if _ssh_tunnel_process.stderr else "Unknown error"
            error_msg = f"❌ SSH tunnel failed to start: {stderr}"
            log(error_msg)
            _ssh_tunnel_process = None
            _local_bind_port = None
            return False
        
        log("✅ SSH tunnel established")
        
        # Now connect to ClickHouse through the tunnel
        log("🔐 Connecting to ClickHouse through tunnel...")
        _clickhouse_client = Client(
            host='127.0.0.1',
            port=_local_bind_port,
            user='default',
            password=CLICKHOUSE_PASS,
            database=CLICKHOUSE_DB,
            settings={'use_numpy': False}
        )
        
        # Test connection with a simple query
        _clickhouse_client.execute('SELECT 1')
        
        log("✅ ClickHouse connection established and ready")
        return True
    
    except Exception as e:
        log(f"❌ Error opening ClickHouse connection: {str(e)}")
        _clickhouse_client = None
        if _ssh_tunnel_process:
            try:
                _ssh_tunnel_process.terminate()
                _ssh_tunnel_process.wait(timeout=2)
            except:
                _ssh_tunnel_process.kill()
            _ssh_tunnel_process = None
        _local_bind_port = None
        return False


def close_clickhouse_connection():
    """
    Close the ClickHouse connection and SSH tunnel.
    """
    global _clickhouse_client, _ssh_tunnel_process, _local_bind_port
    
    if _clickhouse_client is not None:
        try:
            log("🔌 Closing ClickHouse connection...")
            _clickhouse_client.disconnect()
            _clickhouse_client = None
            log("✅ ClickHouse connection closed")
        except Exception as e:
            log(f"⚠️  Error closing ClickHouse connection: {str(e)}")
            _clickhouse_client = None
    
    if _ssh_tunnel_process is not None:
        try:
            log("🔌 Closing SSH tunnel...")
            _ssh_tunnel_process.terminate()
            _ssh_tunnel_process.wait(timeout=5)
            _ssh_tunnel_process = None
            log("✅ SSH tunnel closed")
        except Exception as e:
            log(f"⚠️  Error closing SSH tunnel: {str(e)}")
            if _ssh_tunnel_process:
                _ssh_tunnel_process.kill()
                _ssh_tunnel_process = None
    
    _local_bind_port = None


def execute_clickhouse_query(sql_query):
    """
    Execute a SQL query on ClickHouse and return results as a pandas DataFrame.
    Uses the persistent ClickHouse connection.
    
    Parameters:
        sql_query (str): SQL SELECT query to execute
    
    Returns:
        tuple: (success: bool, dataframe: pd.DataFrame or None, message: str)
    """
    log("📊 Starting ClickHouse query execution")
    total_start = time.perf_counter()
    
    try:
        if _clickhouse_client is None:
            error_msg = "❌ ClickHouse connection not open. Call open_clickhouse_connection() first."
            log(error_msg)
            return False, None, error_msg
        
        log(f"🔐 Executing query on ClickHouse database {CLICKHOUSE_DB}...")
        exec_start = time.perf_counter()
        
        # Execute the query WITHOUT with_column_types to get just data rows
        data_rows = _clickhouse_client.execute(sql_query)
        
        exec_time = time.perf_counter() - exec_start
        log(f"Query executed (took {exec_time:.2f}s)")
        
        # Parse result into DataFrame
        log("Parsing results into DataFrame...")
        parse_start = time.perf_counter()
        
        if data_rows:
            # Convert list of tuples to DataFrame
            # DataFrame will automatically use numeric column indices initially
            df = pd.DataFrame(data_rows)
            
            # Get column names from the database using a helper query
            try:
                log(f"📋 Retrieving column information...")
                # Execute the query with WITH clause to get column types
                query_with_info = f"SELECT * FROM ({sql_query}) LIMIT 0"
                result_with_types = _clickhouse_client.execute(query_with_info, with_column_types=True)
                
                # Extract column names from the column types result
                if result_with_types:
                    # When with_column_types=True, execute returns the column metadata
                    # We need to inspect the client's last query info
                    # For now, use a simpler approach: extract from SELECT clause aliases
                    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
                    if select_match:
                        select_clause = select_match.group(1)
                        # Find all AS aliases
                        aliases = re.findall(r'AS\s+(\w+)', select_clause, re.IGNORECASE)
                        if aliases and len(aliases) == len(df.columns):
                            df.columns = aliases
                            log(f"✅ Set column names from SELECT aliases: {aliases}")
                        else:
                            log(f"⚠️  Could not match all aliases ({len(aliases)} vs {len(df.columns)} columns)")
            except Exception as e:
                log(f"⚠️  Could not get column names: {str(e)}")
            
            log(f"✅ Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        else:
            df = pd.DataFrame()
            log("⚠️  Query returned no rows")
        
        parse_time = time.perf_counter() - parse_start
        total_time = time.perf_counter() - total_start
        
        message = f"✅ ClickHouse query successful!\n"
        message += f"   📊 Rows: {len(df)}\n"
        message += f"   📋 Columns: {len(df.columns)}\n"
        message += f"   ⏱️ Query time: {exec_time:.2f}s\n"
        message += f"   ⏱️ Parse time: {parse_time:.2f}s\n"
        message += f"   ⏱️ Total time: {total_time:.2f}s"
        
        log(message)
        return True, df, message
    
    except Exception as e:
        error_msg = f"❌ ClickHouse query error: {str(e)}"
        log(error_msg)
        import traceback
        log(traceback.format_exc())
        return False, None, error_msg