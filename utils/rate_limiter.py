"""Rate limiting utilities for web scraping."""

import time
import random
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple rate limiter to control request frequency."""
    
    def __init__(self, min_delay: float = 1.0, jitter: float = 0.5):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            jitter: Random jitter to add to delay (0.0 to jitter)
        """
        self.min_delay = min_delay
        self.jitter = jitter
        self.last_request_time = 0.0
    
    def wait(self):
        """Wait until enough time has passed since last request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Calculate delay with jitter
        delay = self.min_delay + random.uniform(0, self.jitter)
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
