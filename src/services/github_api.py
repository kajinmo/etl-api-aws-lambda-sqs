import requests
import logging
import time
from typing import Dict, List, Any

logger = logging.getLogger()

def fetch_public_events(token: str, url: str) -> List[Dict[str, Any]]:
    """Retrieves public events from GitHub API using the bearer token."""
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    logger.info(f"Making extraction request to endpoint: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Strict HTTP Error handling
        if response.status_code == 401:
            logger.error("Request Denied (401). Check the Token in SSM Parameter Store.")
            response.raise_for_status()
        elif response.status_code == 403:
            logger.error("Rate Limit Exceeded (403).")
            response.raise_for_status()
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Communication failure with Github API: {e}")
        raise

# In-memory dictionary to store user locations across executions within the same container
user_location_cache = {}

def fetch_user_location(user_url: str, token: str) -> str:
    """Hits the GitHub User API to extract their location, utilizing the ephemeral cache."""
    # 1. Check container ephemeral cache first
    if user_url in user_location_cache:
        logger.debug(f"CACHE HIT for user: {user_url}")
        return user_location_cache[user_url]
        
    # 2. Cache Miss -> Ask Github
    logger.debug(f"CACHE MISS. Fetching from GitHub: {user_url}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    try:
        # Give GitHub a fast 200ms sleep to avoid blasting rate limits
        time.sleep(0.2)
        resp = requests.get(user_url, headers=headers, timeout=5)
        
        if resp.status_code == 404:
            val = "Unknown (404)"
            # Rate Limiting BackOff
        elif resp.status_code == 403:
            logger.warning(f"Rate Limiting hit trying to fetch user location. Pausing...")
            # If hit rate limit, we just back-off and assign Unknown for this batch.
            val = "Unknown (Rate Limited)"
        else:
            resp.raise_for_status()
            user_data = resp.json()
            val = user_data.get("location", "Not Specified")
            if not val:
                val = "Not Specified"
        
        # 3. Store in cache for future iterations
        user_location_cache[user_url] = val
        return val
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error fetching user {user_url}: {e}")
        return "Unknown (Error)"
