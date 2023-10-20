# BBF WT-474 compliant Subscriber Session Steering (SSS) client

a python based UPSF gRPC client implementation and command line interface

## Config options

| option | description | default |
|---|---|---|
| UPSF_HOST | the UPSF server IPv4 address | 127.0.0.1 |
| UPSF_PORT | the Port of the UPSF server | 50051 |
| LOGLEVEL | the level of information printed. Available options: info, warning, critical, error, debug | info |

## Getting started

in order to use the client python3.9 is required. Also either use a virtualenv
or use the system python in an isolated environment. Then install the
requirements.txt and build/install the client:

``` shell
pip install -r requirements.txt
python3 setup.py build install
```

with the requirements and module installed you are able to create a new python
application utilizing the module. In example to create a new Service Gateway
User Plane (sgup/up) and then get the previously created sgup:

``` python
from upsf_grpc_client.upsf import (
    UPSF,
    UpsfError,
)
...
upsf = UPSF(
upsf_host='127.0.0.1',
upsf_port='50051',
)
upsf.create_service_gateway_user_plane(
name='up-1.b',
description=None,
service_gateway_name='sg-1',
max_session_count=None,
max_shards=None,
supported_service_group=['ssg1,ssg2,ssg3'],
maintenance='none',
allocated_session_count=0,
allocated_shards=0,
network_connection=[],
endpoint=[{'type': 'vtep', 'name': 'vxlan0', 'ip_address': '11.11.11.11', 'udp_port': '4789', 'vni': '12345'}]
)

upsf.get_service_gateway_user_plane(name='up-1.b')
```

Output:

``` shell
name: "up-1.b"
metadata {
  created {
    seconds: 1697191744
    nanos: 417217000
  }
  last_updated {
    seconds: 1697191744
    nanos: 417217000
  }
  derived_state: active
}
maintenance {
}
spec {
  supported_service_group: "ssg1"
  supported_service_group: "ssg2"
  supported_service_group: "ssg3"
  default_endpoint {
    endpoint_name: "vxlan0"
    vtep {
      ip_address: "11.11.11.11"
      udp_port: 4789
      vni: 12345
    }
  }
}
status {
}
```

## Commandline interface

besides the python module there is also the command line interface to quickly
utilze the functions. In order to use the cli the same prerequities are
required as for the module. When installed please refer to the following
command line options:

``` shell
upsf-client [TYPE] [command] [flags]
```

where `TYPE`, `command`, `flags` are:

- `TYPE`: Specifies the resource type. In example: `session`, `up`, `sg`.
          Could also be `subscribe` to listen for incoming events of certain
          resources, like: `CREATE`, `UPDATE`. Or `DELETE` to delete specific
          resources like `session_context`, `shard`, WARNING default is to
          delete ALL resource types.
- `command`: Specifies the operation that you want to perform on one or more
             resources, for example `create`, `get`, `list`, `update`, `delete`.
- `flags`: Specifies optional flags. For example, you can use the
           `--upsf-host` flag to specify the address of the UPSF gRPC server.

### Operations

| Type | command | flag | description | default | optional |
|---|---|---|---|---|---|
| `sg` |  |  | the ServiceGateway (sg) resource | `list` |  |
|  | `create`, `update` |  | creates/updates a sg |  |  |
|  |  | `--name`, `-n` | the name of the sg |  | false |
|  |  | `--description` | description of the sg |  | true |
|  | `list` |  | list all sg |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one sg specified by name |  |  |
|  | `delete` |  | deletes the sg specified by name |  |  |
| `up` |  |  | the ServiceGateway UserPlane resource (up) | `list` |  |
|  | `create`, `update` |  | creates/updates a up |  |  |
|  |  | `--name`, `-n` | the name of the up |  | false |
|  |  | `--description` | description of the up |  | true |
|  |  | `--service-gateway-name`, `--sg-name` | the corresponding sg name |  | true |
|  |  | `--max-session-count`, `-m` | the maximum session count to allocate |  | true |
|  |  | `--max-shards`, `--shards` | the maximum of shards to assign |  |  |
|  |  | `--supported-service-group`, `--ssg` | array of supported service groups | [] | true |
|  |  | `--maintenance` | mark the up as under maintenance (none,drain,drain_and_delete) | none | true |
|  |  | `--default-endpoint`, `--endpoint`, `--ep` [KEY=VAL ...] | the default endpoint of the up (read more in the Endpoint section) | [] | true |
|  |  | `--allocated-session-count` | currently allocated session count |  | true |
|  |  | `--allocated-shards` | currently allocated shards |  | true |
|  | `list` |  | list all up |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one up specified by name |  |  |
|  |  | `--name`, `-n` | the name of the sg |  | false |
|  | `delete` |  | deletes the up specified by name |  |  |
| `session` |  |  | the session context (session) resource | `list` |  |
|  | `create`, `update` |  | creates/updates a session |  |  |
|  |  | `--name`, `-n` | the name of the session (is ignored as the name will be a hash) |  | ignored |
|  |  | `--description` | description of the session |  | true |
|  |  | `--traffic-steering-function`, `--tsf` | the underlying tsf |  | true |
|  |  | `--desired-shard` | the desired shard were the session should be allocated to |  | true |
|  |  | `--required-service-group`, `--rsg` [REQUIRED_SERVICE_GROUP ...] | array of required service groups | [] | true |
|  |  | `--required-quality`, `--qos` | the required quality of the session |  | true |
|  |  | `--source-mac`, `--source-mac-address` | the source mac address |  | true |
|  |  | `--s-tag`, `--stag`, `--svlan` | the s-tag of the session |  | true |
|  |  | `--c-tag`, `--ctag`, `--cvlan` | the c-tag of the session |  | true |
|  |  | `--circuit-id` | the circuit id of the session |  | true |
|  |  | `--remote-id` | the remote id of the session |  | true |
|  |  | `--current-shard-up` | the currend up shard where the session resides |  | true |
|  |  | `--current-shard-tsf` | the current tsf shard where the session resides |  | true |
|  | `list` |  | list all sessions |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one up specified by name |  |  |
|  |  | `--name`, `-n` | the name of the session |  | ignored |
|  | `lookup` |  | performs a session lookup with individual data |  |  |
|  |  | `--traffic-steering-function`, `--tsf` | the underlying tsf |  | true |
|  |  | `--desired-shard` | the desired shard were the session should be allocated to |  | true |
|  |  | `--required-service-group`, `--rsg` [REQUIRED_SERVICE_GROUP ...] | array of required service groups | [] | true |
|  |  | `--required-quality`, `--qos` | the required quality of the session |  | true |
|  |  | `--source-mac`, `--source-mac-address` | the source mac address |  | true |
|  |  | `--s-tag`, `--stag`, `--svlan` | the s-tag of the session |  | true |
|  |  | `--c-tag`, `--ctag`, `--cvlan` | the c-tag of the session |  | true |
|  |  | `--circuit-id` | the circuit id of the session |  | true |
|  |  | `--remote-id` | the remote id of the session |  | true |
|  | `delete` |  | deletes the up specified by name |  |  |
| `shard` |  |  | the subscriber group (shard) resource | `list` |  |
|  | `create`, `update` |  | creates/updates a shard |  |  |
|  |  | `--name`, `-n` | the name of the shard |  | false |
|  |  | `--description` | description of the shard |  | true |
|  |  | `--max-session-count`, `-m` | the maximum session count to allocate |  | true |
|  |  | `--desired-service-gateway-user-plane`, `--desired-up` | the desired up for this shard |  | true |
|  |  | `--desired-network-connection`, `--desired-nc` | array of desired network connections (nc) | [] | true |
|  |  | `--prefixes` | array of prefixes served by this shard | [] | true |
|  |  | `--virtual-mac` | the virtual mac of this shard |  | true |
|  |  | `--allocated-session-count` | currently allocated session count |  | true |
|  |  | `--current-service-gateway-user-plane`, `--current-up` | the current up were the shard is assigned to |  | true |
|  |  | `--current-tsf-network-connection` [KEY=VAL ...] | array of currently assigned TSF NCs | [] | true |
|  |  | `--mbb-state` | the current make before break (mbb) state. Read more in the MBB section (non_mbb_move_requried,userplane_mbb_initiation_required,upstream_switchover_required,downstream_switchover_required,upstream_finalization_required,mbb_complete,mbb_failure) | non_mbb_move_requried | true |
|  |  | `--service-group-supported`, `--sgs` [SERVICE_GROUPS_SUPPORTED ...] | array of supported service groups | [] | true |
|  | `list` |  | list all shards |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one shard specified by name |  |  |
|  |  | `--name`, `-n` | the name of the shard |  | false |
|  | `delete` |  | deletes the shard specified by name |  |  |
| `tsf` |  |  | the TrafficSteeringFunction (tsf) resource | `list` |  |
|  | `create`, `update` |  | creates/updates a tsf |  |  |
|  |  | `--name`, `-n` | the name of the tsf |  | false |
|  |  | `--description` | description of the tsf |  | true |
|  |  | `--default-endpoint`, `--endpoint`, `--ep` KEY=VAL [KEY=VAL ...] | the default endpoint for the tsf. Read more in the Endpoint section | [] | true |
|  | `list` |  | list all tsf |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one tsf specified by name |  |  |
|  |  | `--name`, `-n` | the name of the tsf |  | false |
|  | `delete` |  | deletes the tsf specified by name |  |  |
| `nc` |  |  | the NetworkConnection (nc) resource | `list` |  |
|  | `create`, `update` |  | creates/updates a nc |  |  |
|  |  | `--name`, `-n` | the name of the nc |  | false |
|  |  | `--description` | description of the nc |  | true |
|  |  | `--maintenance`, `-m` | the current maintenance state of the nc (none,drain,drain_and_delete) | none | true |
|  |  | `--maximum-supported-quality`, `--qos` | the maximum supported quality |  | true |
|  |  | `--allocated-shards` | currently allocated shards |  | true |
|  |  | `--nc-spec-type`, `--nc-spec` | the nc spec type (SsPtpSpec,SsMptpSpec,MsPtpSpec,MsMptpSpec) Read more in the NC-Spec section |  | true |
|  |  | `--service-gateway-endpoints`, `--sg-eps` KEY=VAL [KEY=VAL ...] | array of up endpoints | [] | true |
|  |  | `--tsf-endpoints`, `--tsf-eps` KEY=VAL [KEY=VAL ...] | array of tsf endpoints | [] | true |
|  |  | `--nc-active-status`, `--nc-active` KEY=VAL [KEY=VAL ...] | the active status of th nc |  | true |
|  | `list` |  | list all nc |  |  |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  | `get` |  | retrieves one nc specified by name |  |  |
|  |  | `--name`, `-n` | the name of the nc |  | false |
|  | `delete` |  | deletes the nc specified by name |  |  |
| `delete` |  |  | deletes all resources | all  |  |
|  |  | `--type-list`, `-types` | resources to delete (service_gateway,service_gateway_user_plane,session_context,network_connection,traffic_steering_function,shard) | service_gateway,service_gateway_user_plane,session_context,network_connection,traffic_steering_function,shard | true |
| `subscribe` |  |  | subscribe to incoming events |  |  |
|  |  | `--type-list`, `-types` | resources to filter (service_gateway,service_gateway_user_plane,session_context,network_connection,traffic_steering_function,shard) | service_gateway,service_gateway_user_plane,session_context,network_connection,traffic_steering_function,shard | true |
|  |  | `--name-list` | a name list to filter | [] (all) | true |
|  |  | `--parent-list` | a parent list to filter | [] (all) | true |
|  |  | `--itemstate-list`, `--itemstates` | a item state list to filter for (unknown,inactive,active,updating,deleting,deleted) | all | true |
