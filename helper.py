import os
import subprocess
import shlex
from dotenv import load_dotenv
import time
from datetime import datetime
import tempfile
import gzip

# Load environment variables from .env file
load_dotenv()

# Get credentials from .env
BASTION_HOST = os.getenv("BASTION_HOST")
BASTION_USER = os.getenv("BASTION_USER")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PORT = os.getenv("DB_PORT")
DB_PASS = os.getenv("DB_PASS")


def log(msg):
    """Print log message with timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def execute_copy_query_via_bastion(copy_sql_query, output_file):
    """
    Execute a COPY query via bastion and save the output to a local file.
    
    Parameters:
        copy_sql_query (str): SQL COPY query to execute
        output_file (str): Path to save the output file on local machine
    
    Returns:
        tuple: (success: bool, message: str, file_path: str)
    """
    log("🚀 Starting COPY query execution via bastion")
    total_start = time.perf_counter()
    
    try:
        # Write query to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(copy_sql_query)
            temp_query_file = f.name
        
        log(f"📝 Query written to temp file: {temp_query_file}")
        
        # Build the psql command to read from file
        psql_cmd = f"PGPASSWORD='{DB_PASS}' psql -h {DB_HOST} -U {DB_USER} -d {DB_NAME} -p {DB_PORT} -f -"
        
        log("📤 Connecting via SSH and executing COPY query...")
        exec_start = time.perf_counter()
        
        # Read query file and pipe to ssh/psql
        with open(temp_query_file, 'r') as query_file:
            result = subprocess.run(
                ['ssh', f'{BASTION_USER}@{BASTION_HOST}', psql_cmd],
                stdin=query_file,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=5000
            )
        
        # Clean up temp file
        os.remove(temp_query_file)
        
        exec_time = time.perf_counter() - exec_start
        log(f"✅ Query executed (took {exec_time:.2f}s)")
        
        # if result.returncode == 0:
        #     # Write the CSV data to file (optionally gzip)
        #     log(f"💾 Writing data to file: {output_file}")
        #     write_start = time.perf_counter()

        #     if output_file.lower().endswith(".gz"):
        #         with gzip.open(output_file, "wb", compresslevel=9) as f:
        #             f.write(result.stdout.encode("utf-8"))
        #     else:
        #         with open(output_file, "w") as f:
        #             f.write(result.stdout)

        #     write_time = time.perf_counter() - write_start

        if result.returncode == 0:
            # Write the CSV data to file (optionally gzip)
            log(f"💾 Writing data to file: {output_file}")
            write_start = time.perf_counter()

            # 🔥 Clean hidden unicode characters (important)
            clean_output = result.stdout.replace("\u200e", "").replace("\u200f", "")

            if output_file.lower().endswith(".gz"):
                with gzip.open(output_file, "wt", encoding="utf-8", compresslevel=9, newline="") as f:
                    f.write(clean_output)
            else:
                with open(output_file, "w", encoding="utf-8", newline="") as f:
                    f.write(clean_output)

            write_time = time.perf_counter() - write_start


                    # Get file size
            file_size = os.path.getsize(output_file)
            file_size_mb = file_size / (1024 * 1024)
            
            total_time = time.perf_counter() - total_start
            
            message = f"✅ COPY query successful!\n"
            message += f"   📁 File: {output_file}\n"
            message += f"   📊 Size: {file_size_mb:.2f} MB ({file_size} bytes)\n"
            message += f"   ⏱️ Query time: {exec_time:.2f}s\n"
            message += f"   ⏱️ Write time: {write_time:.2f}s\n"
            message += f"   ⏱️ Total time: {total_time:.2f}s"
            
            log(message)
            return True, message, output_file
        else:
            error_msg = f"❌ Query failed with error:\n{result.stderr}"
            log(error_msg)
            return False, error_msg, None
    
    except subprocess.TimeoutExpired:
        error_msg = "❌ Query execution timed out (5 minutes)"
        log(error_msg)
        return False, error_msg, None
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        log(error_msg)
        return False, error_msg, None
