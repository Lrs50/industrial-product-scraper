import logging 
import os

def get_logger(
    name: str,
    to_console: bool = True,
    to_file: bool = False,
    level: int = logging.INFO
    ) -> logging.Logger:
    
    """Returns a logger with a specific name, avoiding duplicate handlers."""
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