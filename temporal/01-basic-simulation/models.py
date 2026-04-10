from dataclasses import dataclass

@dataclass
class NetworkDeploymentRequest:
    router_id: str
    router_ip: str
    software_version: str