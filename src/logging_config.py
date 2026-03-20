import logging
import os
from datetime import datetime


def setup_logging(log_name: str = "app"):
    """
    Configure logging for the application.
    
    Logs are written to both console and file.
    Log files are stored in the 'logs' directory with timestamp.
    
    Parameters:
        log_name (str): Name of the logger (default: "app")
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler (INFO level and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler (DEBUG level and above)
    log_filename = os.path.join(
        log_dir,
        f"{log_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "app"):
    """
    Get a logger instance. 
    Call setup_logging() at least once before using this function.
    
    Parameters:
        name (str): Name of the logger
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
