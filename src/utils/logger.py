import logging 
import os

def get_logger(
    name: str,
    to_console: bool = True,
    to_file: bool = False,
    level: int = logging.INFO
    ) -> logging.Logger:
    
    """
    Creates and returns a named logger with optional console and file output.

    Args:
        name (str): The name of the logger instance.
        to_console (bool): Whether to output logs to the console.
        to_file (bool): Whether to output logs to a file (./logs/project.log).
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: Configured logger with specified handlers and format.
    """
    
    log_file = "project.log"
    log_dir = "logs"
    
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
    
        formatter = logging.Formatter(
            fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        if to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        if to_file:
            os.makedirs(log_dir,exist_ok=True)
            log_path = os.path.join(log_dir,log_file)
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Avoid propagating logs to the root logger if you don't want duplicates from other configurations
        logger.propagate = False
        
    return logger 

def attach_urllib3_to_logger(base_logger: logging.Logger, level: int = logging.INFO) -> None:
    """
    Routes urllib3 logs through the given logger's handlers and sets the log level.

    Args:
        base_logger (logging.Logger): Your configured logger.
        level (int): Logging level for urllib3 (e.g., logging.DEBUG).
    """
    urllib3_logger = logging.getLogger("urllib3")

    # Set level explicitly, or it defaults to WARNING (which hides INFO logs)
    urllib3_logger.setLevel(level)

    for handler in base_logger.handlers:
        if handler not in urllib3_logger.handlers:
            urllib3_logger.addHandler(handler)

    urllib3_logger.propagate = False