import requests
import logging
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
