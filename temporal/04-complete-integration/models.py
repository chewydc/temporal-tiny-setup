from dataclasses import dataclass
from typing import Optional, List

@dataclass
class NetworkDeploymentRequest:
    router_id: str
    router_ip: str
    software_version: str
    network_config: Optional[dict] = None

@dataclass
class ConnectivityTest:
    test_type: str  # "ping", "http", etc.
    source: str
    destination: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class DeploymentResult:
    status: str  # "success", "partial", "failed"
    router_deployed: bool
    connectivity_established: bool
    tests: List[ConnectivityTest]
    summary: str