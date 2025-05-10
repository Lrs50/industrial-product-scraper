from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import requests


def create_resilient_session(total:int = 5) -> requests.Session:
    """
    Creates a resilient HTTP session with retry logic for handling transient failures.

    Args:
        total_retries (int): The total number of retry attempts for failed requests.

    Returns:
        requests.Session: A configured session with retry behavior for HTTP and HTTPS requests.
    """
    
    retry_strategy = Retry(
        total=total,  # total retry attempts
        status_forcelist=[500, 502, 503, 504],  # which HTTP codes to retry
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=0.3  # wait 0.3s * (2 ** retry_number)
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

