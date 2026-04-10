from dataclasses import dataclass
from typing import Optional

@dataclass
class NetworkDeploymentRequest:
    router_id: str
    router_ip: str
    software_version: str
    network_config: Optional[dict] = None