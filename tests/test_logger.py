import os
import sys
import time

# Add the src/ folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils import get_logger

def test_logger_basic():

    logger = get_logger("test_logger", to_console=True, to_file=True)
    
    logger.info("This is an info message for testing.")
    logger.warning("This is a warning for testing.")
    logger.error("This is an error for testing.")
    
    time.sleep(0.1)
    
    log_path = os.path.join("logs", "project.log")
    assert os.path.exists(log_path), "Log file was not created."
    
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "This is an info message for testing." in content, "Info log missing."
        assert "This is a warning for testing." in content, "Warning log missing."
        assert "This is an error for testing." in content, "Error log missing."

    print("✅ Logger basic test passed!")
    
if __name__ == "__main__":
    test_logger_basic()