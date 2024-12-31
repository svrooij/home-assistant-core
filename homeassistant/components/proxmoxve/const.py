"""Constants for ProxmoxVE."""

import logging

DOMAIN = "proxmoxve"
PROXMOX_CLIENTS = "proxmox_clients"
CONF_TOKEN_ID = "token_id"
CONF_REALM = "realm"
CONF_NODE = "node"
CONF_NODES = "nodes"
CONF_VMS = "vms"
CONF_CONTAINERS = "containers"

COORDINATORS = "coordinators"

DEFAULT_PORT = 8006
DEFAULT_REALM = "pve"
DEFAULT_VERIFY_SSL = False
TYPE_VM = 0
TYPE_CONTAINER = 1
UPDATE_INTERVAL = 60

_LOGGER = logging.getLogger(__package__)
