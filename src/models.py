from pydantic import BaseModel, Optional
from typing import Dict, Any

# --- Pydantic Models (Typing and Validation Layer) ---
class GithubActor(BaseModel):
    id: int
    login: str

class GithubRepo(BaseModel):
    id: int
    name: str

class GithubEvent(BaseModel):
    id: str
    type: str # Ex: PushEvent, WatchEvent
    actor: GithubActor
    repo: GithubRepo
    created_at: str
    
    # Raw payload varies greatly across distinct events, so we leave it dynamic for NoSQL/Lake storage.
    payload: Optional[Dict[str, Any]] = None
