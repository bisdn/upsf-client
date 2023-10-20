#!/usr/bin/env python3

# BSD 3-Clause License
#
# Copyright (c) 2023, BISDN GmbH
# All rights reserved.

""" upsf module """

# pylint: disable=no-member
# pylint: disable=too-many-locals
# pylint: disable=too-many-nested-blocks
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-lines
# pylint: disable=too-few-public-methods
# pylint: disable=no-name-in-module
# pylint: disable=too-many-return-statements

import os
import sys
import time
import socket
import argparse
import logging
import threading
import traceback
import contextlib
import hashlib


import grpc
from google.protobuf.wrappers_pb2 import StringValue
from upsf_client.protos.messages_v1_pb2 import (
    Item,
    MetaData,
    Maintenance,
    ServiceGateway,
    ServiceGatewayUserPlane,
    TrafficSteeringFunction,
    Shard,
    NetworkConnection,
    SessionContext,
    SessionFilter,
    L2vpn,
    PortVlan,
    Vtep,
)
from upsf_client.protos import service_v1_pb2_grpc as service_v1_pb2
from upsf_client.protos.service_v1_pb2 import (
    UpdateReq,
    ReadReq,
)


def str2bool(value):
    """map string to boolean value"""
    return value.lower() in [
        "true",
        "1",
        "t",
        "y",
        "yes",
    ]


def session_hash(session):
    """hashify session context to uniquely identify a session"""
    return hashlib.md5(  # nosec B303
        str(session["circuit_id"]).encode()
        + str(session["remote_id"]).encode()
        + str(session["source_mac_address"]).encode()
        + str(session["svlan"]).encode()
        + str(session["cvlan"]).encode()
    ).hexdigest()


def get_item(item_type, params):
    """get item by type and fill it"""
    if item_type == "NetworkConnection":
        return Item(
            network_connection=NetworkConnection(
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
                maintenance=Maintenance(
                    maintenance_req=Maintenance.MaintenanceReq.Value(
                        params["maintenance"]
                    ),
                ),
                spec=get_nc_spec(params),
                status=NetworkConnection.Status(
                    nc_active={
                        k: str2bool(v) for k, v in params.get("nc_active", {}).items()
                    },
                    allocated_shards=int(params["allocated_shards"]),
                ),
            )
        )
    if item_type == "TrafficSteeringFunction":
        return Item(
            traffic_steering_function=TrafficSteeringFunction(
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
                spec=TrafficSteeringFunction.Spec(
                    default_endpoint=get_transport_endpoint(
                        params["endpoint"][0] if len(params["endpoint"]) > 0 else None
                    ),
                ),
            )
        )
    if item_type == "ServiceGateway":
        return Item(
            service_gateway=ServiceGateway(
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
            )
        )
    if item_type == "ServiceGatewayUserPlane":
        return Item(
            service_gateway_user_plane=ServiceGatewayUserPlane(
                service_gateway_name=params["service_gateway_name"],
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
                maintenance=Maintenance(
                    maintenance_req=Maintenance.MaintenanceReq.Value(
                        params["maintenance"]
                    ),
                ),
                spec=ServiceGatewayUserPlane.Spec(
                    max_session_count=int(params["max_session_count"])
                    if params["max_session_count"] is not None
                    else None,
                    max_shards=int(params["max_shards"])
                    if params["max_shards"] is not None
                    else None,
                    supported_service_group=params["supported_service_group"],
                    default_endpoint=get_transport_endpoint(
                        params["endpoint"][0] if len(params["endpoint"]) > 0 else None
                    ),
                ),
                status=ServiceGatewayUserPlane.Status(
                    allocated_session_count=int(params["allocated_session_count"])
                    if params["allocated_session_count"] is not None
                    else None,
                    allocated_shards=int(params["allocated_shards"])
                    if params["allocated_shards"] is not None
                    else None,
                ),
            )
        )
    if item_type == "SessionContext":
        return Item(
            session_context=SessionContext(
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
                spec=SessionContext.Spec(
                    traffic_steering_function=params["traffic_steering_function"],
                    required_service_group=params["required_service_group"],
                    required_quality=int(params.get("required_quality", 0)),
                    circuit_id=params["circuit_id"],
                    remote_id=params["remote_id"],
                    session_filter=SessionFilter(
                        source_mac_address=params["source_mac_address"],
                        svlan=params["svlan"],
                        cvlan=params["cvlan"],
                    ),
                    desired_state=SessionContext.Spec.DesiredState(
                        shard=params["desired_shard"],
                    ),
                ),
                status=SessionContext.Status(
                    current_state=SessionContext.Status.CurrentState(
                        user_plane_shard=params["current_up_shard"],
                        tsf_shard=params["current_tsf_shard"],
                    ),
                ),
            )
        )
    if item_type == "Shard":
        return Item(
            shard=Shard(
                name=params["name"],
                metadata=MetaData(
                    description=params["description"],
                ),
                spec=Shard.Spec(
                    max_session_count=int(params["max_session_count"]),
                    virtual_mac=params["virtual_mac"],
                    desired_state=Shard.Spec.DesiredState(
                        service_gateway_user_plane=params[
                            "desired_service_gateway_user_plane"
                        ],
                        network_connection=params["desired_network_connection"],
                    ),
                    prefix=params.get("prefix"),
                ),
                status=Shard.Status(
                    allocated_session_count=int(params["allocated_session_count"])
                    if params["allocated_session_count"] is not None
                    else None,
                    current_state=Shard.Status.CurrentState(
                        service_gateway_user_plane=params[
                            "current_service_gateway_user_plane"
                        ],
                        tsf_network_connection=params["current_tsf_network_connection"],
                    ),
                    service_groups_supported=params["service_groups_supported"],
                ),
                mbb=Shard.Mbb(
                    mbb_state=Shard.Mbb.MbbState.Value(params["mbb_state"]),
                ),
            )
        )
    raise TypeError(f"Invalid Type {item_type}")


def get_item_name(item):
    """extract item name from sssitem"""
    item_type = item.WhichOneof("sssitem")
    if item_type in ("shard",):
        return item.shard.name
    if item_type in ("service_gateway"):
        return item.service_gateway.name
    if item_type in ("service_gateway_user_plane",):
        return item.service_gateway_user_plane.name
    if item_type in ("traffic_steering_function",):
        return item.traffic_steering_function.name
    if item_type in ("network_connection",):
        return item.network_connection.name
    if item_type in ("session_context",):
        return item.session_context.name
    return None


def get_transport_endpoint(params):
    """get transport endpoint by type"""
    if params is None:
        return None

    if params["type"] in (
        "vtep",
        "Vtep",
    ):
        return NetworkConnection.Spec.Endpoint(
            endpoint_name=params["name"],
            vtep=Vtep(
                ip_address=params["ip_address"],
                udp_port=int(params["udp_port"]),
                vni=int(params["vni"]),
            ),
        )
    if params["type"] in (
        "l2vpn",
        "L2vpn",
    ):
        return NetworkConnection.Spec.Endpoint(
            endpoint_name=params["name"],
            l2vpn=L2vpn(
                vpn_id=int(params["vpn_id"]),
            ),
        )
    if params["type"] in (
        "portvlan",
        "PortVlan",
    ):
        return NetworkConnection.Spec.Endpoint(
            endpoint_name=params["name"],
            port_vlan=PortVlan(
                logical_port=params["logical_port"],
                svlan=int(params["svlan"]),
                cvlan=int(params["cvlan"]),
            ),
        )
    raise TypeError(f"Invalid Type {params['type']}")


def get_nc_spec(params):
    """get nc_spec by type"""
    if params.get("nc_spec_type", None) is None:
        return NetworkConnection.Spec(
            maximum_supported_quality=int(params["maximum_supported_quality"]),
        )
    if params["nc_spec_type"] in ("SsPtpSpec", "ss_ptp"):
        tsf_eps = []
        if params["tsf_endpoints"] not in (
            "",
            "[]",
            [],
            None,
        ):
            for endpoint in params["tsf_endpoints"]:
                tsf_eps.append(get_transport_endpoint(endpoint))
            netconn = NetworkConnection.Spec.SsPtpSpec(
                tsf_endpoint=tsf_eps[0],
            )
        else:
            netconn = NetworkConnection.Spec.SsPtpSpec(
                tsf_endpoint=None,
            )
        sgup_eps = []
        if params["sgup_endpoints"] not in (
            "",
            "[]",
            [],
            None,
        ):
            for endpoint in params["sgup_endpoints"]:
                netconn.sgup_endpoint.append(get_transport_endpoint(endpoint))
        else:
            sgup_eps.append(None)
        return NetworkConnection.Spec(
            maximum_supported_quality=int(params["maximum_supported_quality"]),
            ss_ptp=netconn,
        )

    if params["nc_spec_type"] in ("SsMptpSpec", "ss_mptpc"):
        netconn = NetworkConnection.Spec.SsMptpSpec()
        for endpoint in params["sgup_endpoints"]:
            netconn.sgup_endpoint.append(get_transport_endpoint(endpoint))
        for endpoint in params["tsf_endpoints"]:
            netconn.tsf_endpoint.append(get_transport_endpoint(endpoint))
        return NetworkConnection.Spec(
            maximum_supported_quality=int(params["maximum_supported_quality"]),
            ss_mptpc=netconn,
        )

    if params["nc_spec_type"] in ("MsPtpSpec", "ms_ptp"):
        sgup_eps = []
        if params["sgup_endpoints"] not in (
            "",
            "[]",
            [],
            None,
        ):
            for endpoint in params["sgup_endpoints"]:
                sgup_eps.append(get_transport_endpoint(endpoint))
        else:
            sgup_eps.append(None)
        tsf_eps = []
        if params["tsf_endpoints"] not in (
            "",
            "[]",
            [],
            None,
        ):
            for endpoint in params["tsf_endpoints"]:
                tsf_eps.append(get_transport_endpoint(endpoint))
        else:
            tsf_eps.append(None)
        return NetworkConnection.Spec(
            maximum_supported_quality=int(params["maximum_supported_quality"]),
            ms_ptp=NetworkConnection.Spec.MsPtpSpec(
                sgup_endpoint=sgup_eps[0],
                tsf_endpoint=tsf_eps[0],
            ),
        )

    if params["nc_spec_type"] in ("MsMptpSpec", "ms_mptp"):
        sgup_eps = []
        for endpoint in params["sgup_endpoints"]:
            sgup_eps.append(get_transport_endpoint(endpoint))
        netconn = NetworkConnection.Spec.MsMptpSpec(
            sgup_endpoint=sgup_eps[0],
        )
        for endpoint in params["tsf_endpoints"]:
            netconn.tsf_endpoint.append(get_transport_endpoint(endpoint))
        return NetworkConnection.Spec(
            maximum_supported_quality=int(params["maximum_supported_quality"]),
            ms_mptp=netconn,
        )

    raise TypeError(f"Invalid Type {params['nc_spec_type']}")


class StoreDictKeyPair(argparse.Action):
    """
    store dict key pairs in array
    sep indicates a new set of dict key pairs
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        # super(StoreDictKeyPair, self).__init__(
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None, sep="type"):
        my_array = []
        my_dict = {}
        for kvpair in values:
            key, value = kvpair.split("=")
            if key == sep:
                if my_dict:
                    my_array.append(my_dict)
                    my_dict = {}
            my_dict[key] = value
        my_array.append(my_dict)
        setattr(namespace, self.dest, my_array)


class StoreDictKeyPairToDict(argparse.Action):
    """
    store dict key pairs in dict
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        # super(StoreDictKeyPairToDict, self).__init__(
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None, sep="type"):
        my_dict = {}
        for value in values:
            key, value = value.split("=")
            my_dict[key] = value
        # my_dict = {value.split("=")[0]: value.split("=")[1] for value in values}
        setattr(namespace, self.dest, my_dict)


class UpsfError(Exception):
    """upsf base error"""


class UpsfRpcConnectError(UpsfError):
    """gRPC connection establishment failed"""


class UPSF(threading.Thread):
    """class UPSF"""

    _defaults = {
        "upsf_host": os.environ.get("UPSF_HOST", "127.0.0.1"),
        "upsf_port": os.environ.get("UPSF_PORT", 50051),
        "loglevel": os.environ.get("LOGLEVEL", "info"),
        "upsf_subscribe": False,
        "grpc_channel": None,
        "grpc_client_stub": None,
    }

    _loglevels = {
        "critical": logging.CRITICAL,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "error": logging.ERROR,
        "debug": logging.DEBUG,
    }

    def __init__(self, **kwargs):
        """__init__"""
        threading.Thread.__init__(self)
        self._stop_thread = threading.Event()
        self._lock = threading.RLock()
        self.grpc_channel = None
        self.grpc_client_stub = None
        self.initialize(**kwargs)

    def initialize(self, **kwargs):
        """initialize"""
        for key, value in self._defaults.items():
            setattr(self, key, kwargs.get(key, value))

        # logger
        self._log = logging.getLogger(__name__)
        self._log.setLevel(self._loglevels[self.loglevel])

        # a threading lock for protecting the gRPC channel
        self._grpc_lock = threading.Lock()

        # the UPSF gRPC connection string
        self.upsf_grpc_svc = f"{self.upsf_host}:{self.upsf_port}"

        # start background thread
        if self.upsf_subscribe:
            self.start()

    def __str__(self):
        """return simple string"""
        return f"{self.__class__.__name__}()"

    def __repr__(self):
        """return descriptive string"""
        _attributes = "".join(
            [
                f"{key}={getattr(self, key, None)}, "
                for key, value in self._defaults.items()
            ]
        )
        return f"{self.__class__.__name__}({_attributes})"

    @property
    def log(self):
        """return read-only logger"""
        return self._log

    def connect(self, **kwargs):
        """connect to USPF gRPC service"""
        # connect to upsf grpc service
        self.grpc_channel = grpc.insecure_channel(self.upsf_grpc_svc)

        # get arguments
        backoff = float(kwargs.get("backoff", 1.0))
        backoff_max = float(kwargs.get("backoff_max", 4.0))
        max_retries = int(kwargs.get("max_retries", 16))

        # test gRPC channel for readiness
        while max_retries > 0:
            try:
                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "gRPC: connecting",
                        "backoff": backoff,
                        "retries": max_retries,
                        "upsf_host": self.upsf_host,
                        "upsf_port": self.upsf_port,
                    }
                )

                grpc.channel_ready_future(self.grpc_channel).result(timeout=backoff)

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "gRPC: connected",
                        "backoff": backoff,
                        "retries": max_retries,
                        "upsf_host": self.upsf_host,
                        "upsf_port": self.upsf_port,
                    }
                )

                self.grpc_client_stub = service_v1_pb2.upsfStub(self.grpc_channel)

                return self.grpc_client_stub
            except grpc.FutureTimeoutError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "gRPC: error occurred",
                        "error": str(error),
                        "backoff": backoff,
                        "retries": max_retries,
                        "upsf_host": self.upsf_host,
                        "upsf_port": self.upsf_port,
                    }
                )
                backoff = backoff_max if backoff >= backoff_max else 2 * backoff
                max_retries -= 1

        # error occurred: reset and raise exception
        self.grpc_channel = None
        self.grpc_client_stub = None
        raise UpsfRpcConnectError

    def disconnect(self):
        """disconnect from USPF gRPC service"""
        self.log.debug(
            {
                "entity": str(self),
                "event": "gRPC: disconnecting",
                "upsf_host": self.upsf_host,
                "upsf_port": self.upsf_port,
            }
        )
        if self.grpc_channel is not None:
            self.grpc_channel = None
        if self.grpc_client_stub is not None:
            self.grpc_client_stub = None

    def __enter__(self, **kwargs):
        """PEP 343: connect channel and return gRPC client stub"""

        blocking = bool(kwargs.get("blocking", True))

        with self._grpc_lock:
            while True:
                try:
                    # establish gRPC connection
                    if self.grpc_channel is None and self.grpc_client_stub is None:
                        self.connect(**kwargs)

                    # if connection establishment failed and blocking is True, retry
                    if blocking and self.grpc_client_stub is None:
                        continue

                    # return existing gRPC client stub
                    return self.grpc_client_stub

                except UpsfError as error:
                    self.log.error(
                        {
                            "entity": str(self),
                            "event": "gRPC: connection failed",
                            "error": str(error),
                            "upsf_host": self.upsf_host,
                            "upsf_port": self.upsf_port,
                            "blocking": blocking,
                        }
                    )
                    if blocking is False:
                        raise UpsfError from error

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """PEP343: release gRPC channel lock"""

    # Create Item
    def create_item(self, item_type, params):
        """create item"""
        try:
            sssitem = get_item(item_type, params)

            with self as upsf_stub:
                result = upsf_stub.CreateV1(sssitem)
                if result == "":
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": f"UPSF Create {item_type} (success)",
                        "item": sssitem,
                    }
                )

                return result

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": f"UPSF Create {item_type} (failure)",
                    "item": sssitem,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # UpdateItem
    def update_item(self, item_type, params):
        """update item"""
        try:
            sssitem = get_item(item_type, params)
            with self as upsf_stub:
                result = upsf_stub.UpdateV1(
                    UpdateReq(
                        item=sssitem,
                        update_options=UpdateReq.UpdateOptions(
                            list_merge_strategy=params["list_merge_strategy"]
                        ),
                    )
                )
                if result == "":
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": f"UPSF Update {item_type} (success)",
                        "item": sssitem,
                    }
                )

                return result

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": f"UPSF Update {item_type} (failure)",
                    "item": sssitem,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # DeleteItem
    def delete_items(self, **kwargs):
        """delete item"""
        _params = {
            "name_list": [],
            "itemtypes": [
                "service_gateway",
                "service_gateway_user_plane",
                "traffic_steering_function",
                "network_connection",
                "shard",
                "session_context",
            ],
        }
        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        item_names = []
        for item in self.read(
            name=params["name_list"], watch=False, itemtypes=params["itemtypes"]
        ):
            item_name = get_item_name(item)
            if item_name in (
                "",
                None,
            ):
                continue
            item_names.append(item_name)
        try:
            for item_name in item_names:
                with self as upsf_stub:
                    result = upsf_stub.DeleteV1(StringValue(value=item_name))
                    if result in ("",):
                        raise UpsfError

                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "UPSF Delete Item (success)",
                            "item": item_name,
                        }
                    )

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF Delete Item (failure)",
                    "item": item_name,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # Delete Shard
    def delete_shard(self, **kwargs):
        """
        delete item

        :param str item: handle (name) assigned to this item

        :return: the item name
        :rtype: String

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteShard (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF Delete DeleteShard (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    def read(self, **kwargs):
        """read"""
        try:
            # default parameters
            _params = {
                "itemtypes": [
                    "service_gateway",
                    "service_gateway_user_plane",
                    "traffic_steering_function",
                    "network_connection",
                    "shard",
                    "session_context",
                ],
                "itemstate": [],
                "parent": [],
                "name": [],
                "watch": False,
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                names = []
                if params["name"] is not None:
                    for name in params["name"]:
                        names.append(StringValue(value=name))
                if params["parent"] is not None:
                    parents = []
                    for name in params["parent"]:
                        parents.append(StringValue(value=name))

                read_req = ReadReq(
                    itemtype=params["itemtypes"],
                    itemstate=params["itemstate"],
                    parent=parents,
                    name=names,
                    watch=params["watch"],
                )
                for item in upsf_stub.ReadV1(read_req):
                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "UPSF Read (success)",
                            "item": item,
                        }
                    )
                    yield item

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF Read (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # CreateShard
    def create_shard(self, **kwargs):
        """
        create shard

        :param str name: assign this name to shard
        :param int max_session_count: int32 indicating maximum number of sessions in this shard
        :param str virtual_mac:
        :param str desired_service_gateway_user_plane: desired service gateway user plane
        :param list desired_network_connection: list of network connections needed for this shard

        :return: the shard
        :rtype: Shard

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "max_session_count": 0,
            "desired_service_gateway_user_plane": "",
            "desired_network_connection": [],
            "prefix": [],
            "current_service_gateway_user_plane": "",
            "current_tsf_network_connection": "",
            "allocated_session_count": 0,
            "virtual_mac": "",
            "mbb_state": "non_mbb_move_requried",
            "service_groups_supported": [],
            "list_merge_strategy": "union",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.create_item("Shard", params)

    # UpdateShard
    def update_shard(self, **kwargs):
        """
        update shard

        :param str name: assign this name to shard
        :param int max_session_count: int32 indicating maximum number of sessions in this shard
        :param str virtual_mac:
        :param str desired_service_gateway_user_plane: desired service gateway user plane
        :param list desired_network_connection: list of network connections needed for this shard

        :return: the shard
        :rtype: Shard

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "max_session_count": 0,
            "desired_service_gateway_user_plane": "",
            "desired_network_connection": [],
            "prefix": [],
            "current_service_gateway_user_plane": "",
            "current_tsf_network_connection": "",
            "allocated_session_count": 0,
            "virtual_mac": "",
            "mbb_state": "non_mbb_move_requried",
            "service_groups_supported": [],
            "list_merge_strategy": "union",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.update_item("Shard", params)

    # GetShard
    def get_shard(self, **kwargs):
        """
        get shard

        :param str shard_name: handle (name) assigned to this shard

        :return: the shard
        :rtype: Shard

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None
        for item in self.read(name=[params["name"]], watch=False, itemtypes=["shard"]):
            items.append(item.shard)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListShards
    def list_shards(self, **kwargs):
        """
        list shards

        :param list name_list: list of handles (names) for filtering

        :return: list of shards
        :rtype: list of Shards

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name_list": [],
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        for item in self.read(
            name=params["name_list"], watch=False, itemtypes=["shard"]
        ):
            items.append(item.shard)
        return items

    # CreateNetworkConnection
    def create_network_connection(self, **kwargs):
        """
        create network connection

        :param str name: assign this name to network connection
        :param str traffic_steering_function: name of the associated TSF endpoint
        :param str service_gateway_user_plane: name of the associated SG-UP endpoint
        :param int maximum_supported_quality
        :param int allocated_shards
        :param str maintenance
        :param str endpoint_name
        :param str transport_endpoint
        :param int tsf_status: traffic steering function status (0: unknown, 1: up, 2: down)
        :param int up_status: service gateway user plane status (0: unknown, 1: up, 2: down)

        :return: the network connection
        :rtype: NetworkConnection

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """

        # default parameters
        _params = {
            "name": "",
            "description": "",
            "maintenance": "none",
            "maximum_supported_quality": 0,
            "allocated_shards": 0,
            "nc_spec_type": "MsPtpSpec",
            "sgup_endpoints": [],
            "tsf_endpoints": [],
            "nc_active": {},
            "list_merge_strategy": "union",
            "cmd": "create",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        return self.create_item("NetworkConnection", params)

    # UpdateNetworkConnection
    def update_network_connection(self, **kwargs):
        """
        update network connection

        :param str name: assign this name to network connection
        :param str traffic_steering_function: name of the associated TSF endpoint
        :param str service_gateway_user_plane: name of the associated SG-UP endpoint
        :param int maximum_supported_quality
        :param int allocated_shards
        :param str maintenance
        :param str endpoint_name
        :param str transport_endpoint
        :param int tsf_status: traffic steering function status (0: unknown, 1: up, 2: down)
        :param int up_status: service gateway user plane status (0: unknown, 1: up, 2: down)

        :return: the network connection
        :rtype: NetworkConnection

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """

        # default parameters
        _params = {
            "name": "",
            "description": "",
            "maintenance": "none",
            "maximum_supported_quality": 0,
            "allocated_shards": 0,
            "nc_spec_type": "MsPtpSpec",
            "sgup_endpoints": [],
            "tsf_endpoints": [],
            "nc_active": {},
            "list_merge_strategy": "union",
            "cmd": "update",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        return self.update_item("NetworkConnection", params)

    # DeleteNetworkConnection
    def delete_network_connection(self, **kwargs):
        """
        delete network connection

        :param str network_connection_name: handle (id) assigned to this network connection

        :return: the network connection
        :rtype: NetworkConnection

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteNetworkConnection (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF DeleteNetworkConnection (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # GetNetworkConnection
    def get_network_connection(self, **kwargs):
        """
        get network connection

        :param str network_connection_name: handle (id) assigned to this network connection

        :return: the network connection
        :rtype: NetworkConnection

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None
        items = []
        for item in self.read(
            name=[params["name"]], watch=False, itemtypes=["network_connection"]
        ):
            items.append(item.network_connection)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListNetworkConnections
    def list_network_connections(self, **kwargs):
        """
        list network connections

        :param list of strings name_list: list of handles (names) for filtering

        :return: list of network connections
        :rtype: list of NetworkConnections

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {"name_list": []}

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        for item in self.read(
            name=params["name_list"], watch=False, itemtypes=["network_connection"]
        ):
            items.append(item.network_connection)
        return items

    # CreateTrafficSteeringFunction
    def create_traffic_steering_function(self, **kwargs):
        """
        create traffic steering function

        :param str name: assign this name to network connection
        :param str endpoint_name: name of the default endpoint

        :return: the traffic steering function
        :rtype: TrafficSteeringFunction

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "endpoint": [],
            "list_merge_strategy": "union",
            "cmd": "create",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.create_item("TrafficSteeringFunction", params)

    # UpdateTrafficSteeringFunction
    def update_traffic_steering_function(self, **kwargs):
        """
        update traffic steering function

        :param str name: assign this name to network connection
        :param str endpoint_name: name of the default endpoint

        :return: the traffic steering function
        :rtype: TrafficSteeringFunction

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "endpoint": [],
            "list_merge_strategy": "union",
            "cmd": "update",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.update_item("TrafficSteeringFunction", params)

    # DeleteTrafficSteeringFunction
    def delete_traffic_steering_function(self, **kwargs):
        """
        delete traffic steering function

        :param str traffic_steering_function_name: handle (id) assigned to this TSF

        :return: the traffic steering function
        :rtype: TrafficSteeringFunction

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteTrafficSteeringFunction (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF DeleteTrafficSteeringFunction (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # GetTrafficSteeringFunction
    def get_traffic_steering_function(self, **kwargs):
        """
        get traffic steering function

        :param str traffic_steering_function_name: handle (id) assigned to this TSF

        :return: the traffic steering function
        :rtype: TrafficSteeringFunction

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None
        items = []
        for item in self.read(
            name=[params["name"]], watch=False, itemtypes=["traffic_steering_function"]
        ):
            items.append(item.traffic_steering_function)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListTrafficSteeringFunctions
    def list_traffic_steering_functions(self, **kwargs):
        """
        list traffic steering functions

        :param list of strings name_list: list of handles (name) for filtering

        :return: list of traffic steering functions
        :rtype: list of TrafficSteeringFunction

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name_list": [],
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        for item in self.read(
            name=params["name_list"],
            watch=False,
            itemtypes=["traffic_steering_function"],
        ):
            items.append(item.traffic_steering_function)
        return items

    # CreateServiceGateway
    def create_service_gateway(self, **kwargs):
        """
        create service gateway

        :param str name: assign this name to service gateway

        :return: the service gateway
        :rtype: ServiceGateway

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "list_merge_strategy": "union",
            "cmd": "create",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.create_item("ServiceGateway", params)

    # UpdateServiceGateway
    def update_service_gateway(self, **kwargs):
        """
        update service gateway

        :param str name: assign this name to service gateway

        :return: the service gateway
        :rtype: ServiceGateway

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "list_merge_strategy": "union",
            "cmd": "update",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.update_item("ServiceGateway", params)

    # DeleteServiceGateway
    def delete_service_gateway(self, **kwargs):
        """
        delete service gateway

        :param str service_gateway_name: handle (id) assigned to this TSF

        :return: the service gateway
        :rtype: ServiceGateway

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteServiceGateway (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF DeleteServiceGateway (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # GetServiceGateway
    def get_service_gateway(self, **kwargs):
        """
        get service gateway

        :param str service_gateway_name: handle (id) assigned to this TSF

        :return: the service gateway
        :rtype: ServiceGateway

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None
        items = []
        for item in self.read(
            name=[params["name"]], watch=False, itemtypes=["service_gateway"]
        ):
            items.append(item.service_gateway)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListServiceGateways
    def list_service_gateways(self, **kwargs):
        """
        list service gateways

        :param list of strings name_list: list of handles (names) for filtering

        :return: list of service gateways
        :rtype: list of ServiceGateway

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name_list": [],
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        service_gateways = []
        for item in self.read(
            name=params["name_list"], watch=False, itemtypes=["service_gateway"]
        ):
            service_gateways.append(item.service_gateway)
        return service_gateways

    # CreateServiceGatewayUserPlane
    def create_service_gateway_user_plane(self, **kwargs):
        """
        create service gateway user plane

        :param str name: assign this name to service gateway
        :param str service_gateway_name: handle (id) associated to parent SG
        :param int max_session_count: int32 identifying max number
                                      of sessions available on this SG-UP
        :param int max_shards:
        :param list supported_service_group: the supported service group
        :param bool maintenance: SG-UP is in in state maintenance (no typo!)
        :param str endpoint_name:
        :param str default_transport_endpoint:

        :return: the service gateway user plane
        :rtype: ServiceGatewayUserPlane

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "service_gateway_name": "",
            "max_session_count": 0,
            "max_shards": 0,
            "supported_service_group": [],
            "maintenance": "none",
            "allocated_session_count": 0,
            "allocated_shards": 0,
            "network_connection": [],
            "endpoint": [],
            "list_merge_strategy": "union",
            "cmd": "create",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.create_item("ServiceGatewayUserPlane", params)

    # UpdateServiceGatewayUserPlane
    def update_service_gateway_user_plane(self, **kwargs):
        """
        update service gateway user plane

        :param str name: assign this name to service gateway
        :param str service_gateway_name: handle (id) associated to parent SG
        :param int max_session_count: int32 identifying max number
                                      of sessions available on this SG-UP
        :param int max_shards:
        :param list supported_service_group: the supported service group
        :param bool maintenance: SG-UP is in in state maintenance (no typo!)
        :param str endpoint_name:
        :param str default_transport_endpoint:

        :return: the service gateway user plane
        :rtype: ServiceGatewayUserPlane

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "service_gateway_name": "",
            "max_session_count": 0,
            "max_shards": 0,
            "supported_service_group": [],
            "maintenance": "none",
            "allocated_session_count": 0,
            "allocated_shards": 0,
            "network_connection": [],
            "endpoint": [],
            "list_merge_strategy": "union",
            "cmd": "update",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        return self.update_item("ServiceGatewayUserPlane", params)

    # DeleteServiceGatewayUserPlane
    def delete_service_gateway_user_plane(self, **kwargs):
        """
        delete service gateway user plane

        :param str service_gateway_user_plane_name: handle (id) assigned to this TSF

        :return: the service gateway user plane
        :rtype: ServiceGatewayUserPlane

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteServiceGatewayUserPlane (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF DeleteServiceGatewayUserPlane (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # GetServiceGatewayUserPlane
    def get_service_gateway_user_plane(self, **kwargs):
        """
        get service gateway user plane

        :param str service_gateway_user_plane_name: handle (names) for filtering

        :return: the service gateway user plane
        :rtype: ServiceGatewayUserPlane

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None

        items = []
        for item in self.read(
            name=[params["name"]], watch=False, itemtypes=["service_gateway_user_plane"]
        ):
            items.append(item.service_gateway_user_plane)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListServiceGatewayUserPlanes
    def list_service_gateway_user_planes(self, **kwargs):
        """
        list service gateway user planes

        :param list of strings name_list: list of handles (names) for filtering

        :return: list of service gateway user planes
        :rtype: list of ServiceGatewayUserPlane

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name_list": [],
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        items = []
        for item in self.read(
            name=params["name_list"],
            watch=False,
            itemtypes=["service_gateway_user_plane"],
        ):
            items.append(item.service_gateway_user_plane)
        return items

    # CreateSessionContext
    def create_session_context(self, **kwargs):
        """
        create session context

        :param str name: assign this name to session context
        :param str traffic_steering_function: desired TSF
        :param str desired_shard: desired shard
        :param str required_quality: list of required service group strings
        :param list str required_service_group:
        :param str source_mac_address: calling station id
        :param int svlan: S-TAG (outer vlan tag)
        :param int cvlan: C-TAG (inner vlan tag)
        :param str circuit_id: access node circuit id
        :param str remote_id: access node remote id
        :param str current_shard: current shard
        :param str list_merge_strategy: strategy how to merge items

        :return: the session context
        :rtype: SessionContext

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "traffic_steering_function": "",
            "required_service_group": [],
            "required_quality": 0,
            "circuit_id": "",
            "remote_id": "",
            "desired_shard": "",
            "source_mac_address": "",
            "svlan": 0,
            "cvlan": 0,
            "current_up_shard": "",
            "current_tsf_shard": "",
            "list_merge_strategy": "union",
            "cmd": "create",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        params["name"] = session_hash(params)

        return self.create_item("SessionContext", params)

    # UpdateSessionContext
    def update_session_context(self, **kwargs):
        """
        update session context

        :param str name: assign this name to session context
        :param str traffic_steering_function: desired TSF
        :param str desired_shard: desired shard
        :param str required_quality: list of required service group strings
        :param list str required_service_group:
        :param str source_mac_address: calling station id
        :param int svlan: S-TAG (outer vlan tag)
        :param int cvlan: C-TAG (inner vlan tag)
        :param str circuit_id: access node circuit id
        :param str remote_id: access node remote id
        :param str current_shard: current shard
        :param str list_merge_strategy: strategy how to merge items

        :return: the session context
        :rtype: SessionContext

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
            "description": "",
            "traffic_steering_function": "",
            "required_service_group": [],
            "required_quality": 0,
            "circuit_id": "",
            "remote_id": "",
            "desired_shard": "",
            "source_mac_address": "",
            "svlan": 0,
            "cvlan": 0,
            "current_up_shard": "",
            "current_tsf_shard": "",
            "list_merge_strategy": "union",
            "cmd": "update",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        if kwargs.get("subcmd") == "create":
            return self.create_item("SessionContext", params)
        return self.update_item("SessionContext", params)

    # DeleteSessionContext
    def delete_session_context(self, **kwargs):
        """
        delete session context

        :param str name: handle (name) assigned to this session_context

        :return: the session context
        :rtype: SessionContext

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "name": "",
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            with self as upsf_stub:
                result = upsf_stub.DeleteV1(StringValue(value=params["name"]))
                if result in ("",):
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF DeleteSessionContext (success)",
                    }
                )

                return result.value

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF DeleteSessionContext (failure)",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    # GetSessionContext
    def get_session_context(self, **kwargs):
        """
        get session context

        :param list of str name_list: handle (names) for filtering

        :return: the session context
        :rtype: SessionContext

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name": "",
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)
        items = []
        if params["name"] in (
            "",
            None,
        ):
            self.log.warning(
                {
                    "entity": str(self),
                    "event": "item name not provided",
                }
            )
            return None

        items = []
        for item in self.read(
            name=[params["name"]], watch=False, itemtypes=["session_context"]
        ):
            items.append(item.session_context)
        if len(items) == 1:
            return items[0]
        self.log.warning(
            {
                "entity": str(self),
                "event": "items count is not 1",
                "items": items,
            }
        )
        return None

    # ListSessionContexts
    def list_session_contexts(self, **kwargs):
        """
        list session contexts

        :param list of strings name_list: list of handles (names) for filtering

        :return: list of session contexts
        :rtype: list of SessionContexts

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        # default parameters
        _params = {
            "name_list": [],
        }

        # create effective parameters
        params = {}
        for key, value in _params.items():
            params[key] = kwargs.get(key, value)

        items = []
        for item in self.read(
            name=params["name_list"], watch=False, itemtypes=["session_context"]
        ):
            items.append(item.session_context)
        return items

    # Lookup
    def lookup(self, **kwargs):
        """
        lookup

        :param str traffic_steering_function: originating TSF
        :param str desired_shard: desired shard
        :param list required_service_group: list of required service group strings
        :param str required_quality: string identifying the required qos
        :param str source_mac_address: calling station id
        :param int svlan: S-TAG (outer vlan tag)
        :param int cvlan: C-TAG (inner vlan tag)
        :param str circuit_id: access node circuit id
        :param str remote_id: access node remote id

        :return: the session context
        :rtype: SessionContext

        :raises UpsfError: response message indicates a failure above grpc proto
        :raises grpc.RpcError: indicates an error in grpc transport
        """
        try:
            # default parameters
            _params = {
                "traffic_steering_function": "",
                "required_service_group": [],
                "required_quality": 0,
                "circuit_id": "",
                "remote_id": "",
                "desired_shard": "",
                "source_mac_address": "",
                "svlan": 0,
                "cvlan": 0,
            }

            # create effective parameters
            params = {}
            for key, value in _params.items():
                params[key] = kwargs.get(key, value)

            spec = SessionContext.Spec(
                traffic_steering_function=params["traffic_steering_function"],
                required_service_group=params["required_service_group"],
                required_quality=params["required_quality"],
                circuit_id=params["circuit_id"],
                remote_id=params["remote_id"],
                session_filter=SessionFilter(
                    source_mac_address=params["source_mac_address"],
                    svlan=params["svlan"],
                    cvlan=params["cvlan"],
                ),
                desired_state=SessionContext.Spec.DesiredState(
                    shard=params["desired_shard"],
                ),
            )

            with self as upsf_stub:
                result = upsf_stub.LookupV1(spec)
                if result == "":
                    raise UpsfError

                self.log.debug(
                    {
                        "entity": str(self),
                        "event": "UPSF UpdateSessionContext (success)",
                        "session_context": result,
                    }
                )

                return result

        except grpc.RpcError as error:
            self.log.error(
                {
                    "entity": str(self),
                    "event": "UPSF UpdateSessionContext (failure)",
                    "spec": spec,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

    def stop(self):
        """signals background thread a stop condition"""
        self.log.debug(
            {
                "entity": str(self),
                "event": "thread terminating ...",
            }
        )
        self._stop_thread.set()
        self.join()

    def run(self):
        """runs main loop as background thread"""
        while not self._stop_thread.is_set():
            try:
                with self as upfs_stub:
                    params = {
                        "itemtypes": [
                            "service_gateway",
                            "service_gateway_user_plane",
                            "traffic_steering_function",
                            "network_connection",
                            "shard",
                            "session_context",
                        ],
                        "itemstate": [],
                        "parent": [],
                        "name": [],
                        "watch": True,
                    }

                    for _update in upfs_stub.read(params):
                        self.log.info(
                            {
                                "entity": str(self),
                                "event": "UPSF Subscription Update",
                                "update": _update,
                            }
                        )

            except RuntimeError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "error occurred",
                        "error": str(error),
                    }
                )
                time.sleep(1)


def do_create_item(upsf, **kwargs):
    """Create Item"""
    if kwargs.get("cmd") == "sg":
        item_type = "ServiceGateway"
    if kwargs.get("cmd") == "up":
        item_type = "ServiceGatewayUserPlane"
    item = upsf.create_item(
        item_type,
        kwargs,
    )
    return item


def do_update_item(upsf, **kwargs):
    """Update Item"""
    item = upsf.update_item(
        **kwargs,
    )
    return item


def do_list_item(upsf, **kwargs):
    """List Item"""
    item = upsf.list_item(
        **kwargs,
    )
    return item


def do_delete_items(upsf, **kwargs):
    """Delete Item"""
    item = upsf.delete_items(
        **kwargs,
    )
    return item


# Subscribe
def do_subscribe(upsf, **kwargs):
    """Subscribe"""
    for _update in upsf.read(**kwargs, watch=True):
        print(_update)


# ServiceGateway
def do_service_gateway_create(upsf, **kwargs):
    """CreateServiceGateway"""
    service_gateway = upsf.create_service_gateway(
        **kwargs,
    )
    return service_gateway


def do_service_gateway_update(upsf, **kwargs):
    """UpdateServiceGateway"""
    service_gateway = upsf.update_service_gateway(
        **kwargs,
    )
    return service_gateway


def do_service_gateway_delete(upsf, **kwargs):
    """DeleteServiceGateway"""
    service_gateway = upsf.delete_service_gateway(
        **kwargs,
    )
    return service_gateway


def do_service_gateway_get(upsf, **kwargs):
    """GetServiceGateway"""
    service_gateway = upsf.get_service_gateway(
        **kwargs,
    )
    return service_gateway


def do_service_gateway_list(upsf, **kwargs):
    """ListServiceGateways"""
    service_gateways = upsf.list_service_gateways(
        **kwargs,
    )
    return service_gateways


# UserPlane
def do_user_plane_create(upsf, **kwargs):
    """CreateServiceGateway"""
    user_plane = upsf.create_service_gateway_user_plane(
        **kwargs,
    )
    return user_plane


def do_user_plane_update(upsf, **kwargs):
    """UpdateServiceGateway"""
    user_plane = upsf.update_service_gateway_user_plane(
        **kwargs,
    )
    return user_plane


def do_user_plane_delete(upsf, **kwargs):
    """DeleteServiceGateway"""
    user_plane = upsf.delete_service_gateway_user_plane(
        **kwargs,
    )
    return user_plane


def do_user_plane_get(upsf, **kwargs):
    """GetServiceGateway"""
    user_plane = upsf.get_service_gateway_user_plane(
        **kwargs,
    )
    return user_plane


def do_user_plane_list(upsf, **kwargs):
    """ListServiceGateways"""
    user_planes = upsf.list_service_gateway_user_planes(
        **kwargs,
    )
    return user_planes


# Shard
def do_shard_create(upsf, **kwargs):
    """CreateShard"""
    shard = upsf.create_shard(
        **kwargs,
    )
    return shard


def do_shard_update(upsf, **kwargs):
    """UpdateShard"""
    shard = upsf.update_shard(
        **kwargs,
    )
    return shard


def do_shard_delete(upsf, **kwargs):
    """DeleteShard"""
    shard = upsf.delete_shard(
        **kwargs,
    )
    return shard


def do_shard_get(upsf, **kwargs):
    """GetShard"""
    shard = upsf.get_shard(
        **kwargs,
    )
    return shard


def do_shard_list(upsf, **kwargs):
    """ListShards"""
    shards = upsf.list_shards(
        **kwargs,
    )
    return shards


# SessionContext
def do_session_context_create(upsf, **kwargs):
    """CreateSessionContext"""
    session_context = upsf.create_session_context(
        **kwargs,
    )
    return session_context


def do_session_context_update(upsf, **kwargs):
    """UpdateSessionContext"""
    session_context = upsf.update_session_context(
        **kwargs,
    )
    return session_context


def do_session_context_delete(upsf, **kwargs):
    """DeleteSessionContext"""
    session_context = upsf.delete_session_context(
        **kwargs,
    )
    return session_context


def do_session_context_get(upsf, **kwargs):
    """GetSessionContext"""
    session_context = upsf.get_session_context(
        **kwargs,
    )
    return session_context


def do_session_context_list(upsf, **kwargs):
    """ListSessionContexts"""
    session_contexts = upsf.list_session_contexts(
        **kwargs,
    )
    return session_contexts


# SessionContext => Lookup
def do_session_context_lookup(upsf, **kwargs):
    """Lookup"""
    session_context = upsf.lookup(
        **kwargs,
    )
    return session_context


# TrafficSteeringFunction
def do_traffic_steering_function_create(upsf, **kwargs):
    """CreateTrafficSteeringFunction"""
    traffic_steering_function = upsf.create_traffic_steering_function(
        **kwargs,
    )
    return traffic_steering_function


def do_traffic_steering_function_update(upsf, **kwargs):
    """UpdateTrafficSteeringFunction"""
    traffic_steering_function = upsf.update_traffic_steering_function(
        **kwargs,
    )
    return traffic_steering_function


def do_traffic_steering_function_delete(upsf, **kwargs):
    """DeleteTrafficSteeringFunction"""
    traffic_steering_function = upsf.delete_traffic_steering_function(
        **kwargs,
    )
    return traffic_steering_function


def do_traffic_steering_function_get(upsf, **kwargs):
    """GetTrafficSteeringFunction"""
    traffic_steering_function = upsf.get_traffic_steering_function(
        **kwargs,
    )
    return traffic_steering_function


def do_traffic_steering_function_list(upsf, **kwargs):
    """ListTrafficSteeringFunctions"""
    traffic_steering_functions = upsf.list_traffic_steering_functions(
        **kwargs,
    )
    return traffic_steering_functions


# NetworkConnection
def do_network_connection_create(upsf, **kwargs):
    """CreateNetworkConnection"""
    network_connection = upsf.create_network_connection(
        **kwargs,
    )
    return network_connection


def do_network_connection_update(upsf, **kwargs):
    """UpdateNetworkConnection"""
    network_connection = upsf.update_network_connection(
        **kwargs,
    )
    return network_connection


def do_network_connection_delete(upsf, **kwargs):
    """DeleteNetworkConnection"""
    network_connection = upsf.delete_network_connection(
        **kwargs,
    )
    return network_connection


def do_network_connection_get(upsf, **kwargs):
    """GetNetworkConnection"""
    network_connection = upsf.get_network_connection(
        **kwargs,
    )
    return network_connection


def do_network_connection_list(upsf, **kwargs):
    """ListNetworkConnections"""
    network_connections = upsf.list_network_connections(
        **kwargs,
    )
    return network_connections


def parse_arguments(defaults, loglevels):
    """parse command line arguments"""
    parser = argparse.ArgumentParser(sys.argv[0])

    subparsers = parser.add_subparsers(
        dest="cmd",
        help="help <cmd>",
    )

    parser.add_argument(
        "--upsf-host",
        help=f'upsf grpc host (default: {defaults["upsf_host"]})',
        dest="upsf_host",
        action="store",
        default=defaults["upsf_host"],
        type=str,
    )

    parser.add_argument(
        "--upsf-port",
        "-p",
        help=f'upsf grpc port (default: {defaults["upsf_port"]})',
        dest="upsf_port",
        action="store",
        default=defaults["upsf_port"],
        type=int,
    )

    parser.add_argument(
        "--loglevel",
        "-l",
        help=f'set log level (default: {defaults["loglevel"]})',
        dest="loglevel",
        choices=loglevels.keys(),
        action="store",
        default=defaults["loglevel"],
        type=str,
    )

    # Subscribe
    parser_subscribe = subparsers.add_parser("subscribe", help="subscribe to updates")

    parser_subscribe.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "subscribe",
        ],
        default="subscribe",
        type=str,
        nargs="?",
    )

    parser_subscribe.add_argument(
        "--type-list",
        "-types",
        help="list of subscriptions to retrieve from UPSF "
        "(0: shards, 1: session_contexts, 2: network_connections, "
        "3: service_gateway_user_planes, 4: traffic_steering_functions, "
        "5: service_gateways)",
        dest="itemtypes",
        choices=[
            "service_gateway",
            "service_gateway_user_plane",
            "session_context",
            "network_connection",
            "traffic_steering_function",
            "shard",
        ],
        default=[
            "service_gateway",
            "service_gateway_user_plane",
            "session_context",
            "network_connection",
            "traffic_steering_function",
            "shard",
        ],
        action="store",
        type=str,
        nargs="*",
    )

    parser_subscribe.add_argument(
        "--name-list",
        "--names",
        help="list of handles (names) to retrieve from UPSF",
        dest="names",
        action="store",
        type=str,
        nargs="*",
    )

    parser_subscribe.add_argument(
        "--parent-list",
        "--parents",
        help="list of parents to retrieve from UPSF including Children",
        dest="parents",
        action="store",
        type=str,
        nargs="*",
    )

    parser_subscribe.add_argument(
        "--itemstate-list",
        "--itemstates",
        help="list of item-states to filter when items retrieved from UPSF"
        "(unknown, inactive, active, updating, deleting, deleted)",
        dest="itemstates",
        choices=["unknown", "inactive", "active", "updating", "deleting", "deleted"],
        action="store",
        type=str,
        nargs="*",
    )

    # DeleteAll
    parser_delete = subparsers.add_parser("delete", help="manage delete items")

    parser_delete.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "delete",
        ],
        default="delete",
        type=str,
        nargs="?",
    )

    parser_delete.add_argument(
        "--type-list",
        "-types",
        help="list of items to delete from UPSF "
        "(0: shards, 1: session_contexts, 2: network_connections, "
        "3: service_gateway_user_planes, 4: traffic_steering_functions, "
        "5: service_gateways)",
        dest="itemtypes",
        choices=[
            "service_gateway",
            "service_gateway_user_plane",
            "session_context",
            "network_connection",
            "traffic_steering_function",
            "shard",
        ],
        default=[
            "service_gateway",
            "service_gateway_user_plane",
            "session_context",
            "network_connection",
            "traffic_steering_function",
            "shard",
        ],
        action="store",
        type=str,
        nargs="*",
    )

    # ServiceGateway
    parser_sg = subparsers.add_parser("sg", help="manage service gateway(s)")

    parser_sg.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_sg.add_argument(
        "-n",
        "--name",
        help="service gateway name",
        dest="name",
        action="store",
        type=str,
    )

    parser_sg.add_argument(
        "--name-list",
        help="list of handles (ID) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_sg.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    parser_sg.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    # ServiceGatewayUserPlane
    parser_up = subparsers.add_parser("up", help="manage service gateway user plane(s)")

    parser_up.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_up.add_argument(
        "--name",
        "-n",
        help="service gateway user plane name",
        dest="name",
        action="store",
        type=str,
    )

    parser_up.add_argument(
        "--service-gateway-name",
        "--sg-name",
        help="service gateway name",
        dest="service_gateway_name",
        action="store",
        type=str,
    )

    parser_up.add_argument(
        "--name-list",
        help="list of handles (names) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_up.add_argument(
        "--max-session-count",
        "-m",
        help="max session count",
        dest="max_session_count",
        action="store",
        type=int,
    )

    parser_up.add_argument(
        "--max-shards",
        "--shards",
        help="max shards",
        dest="max_shards",
        action="store",
        type=int,
    )

    parser_up.add_argument(
        "--supported-service-group",
        "--ssg",
        help="supported service group",
        dest="supported_service_group",
        action="store",
        default=[],
        type=str,
        nargs="*",
    )

    parser_up.add_argument(
        "--maintenance",
        help="enable maintenance mode on user plane",
        dest="maintenance",
        action="store",
        choices=["none", "drain", "drain_and_delete"],
        default="none",
    )

    parser_up.add_argument(
        "--default-endpoint",
        "--endpoint",
        "--ep",
        help="default endpoint",
        dest="endpoint",
        action=StoreDictKeyPair,
        default=[],
        metavar="KEY=VAL",
        nargs="+",
    )

    parser_up.add_argument(
        "--allocated-session-count",
        help="allocated session count",
        dest="allocated_session_count",
        action="store",
        default=0,
        type=int,
    )

    parser_up.add_argument(
        "--allocated-shards",
        help="allocated shards",
        dest="allocated_shards",
        action="store",
        default=0,
        type=int,
    )

    parser_up.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    parser_up.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    # Shard
    parser_shard = subparsers.add_parser("shard", help="manage shard(s)")

    parser_shard.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_shard.add_argument(
        "-n",
        "--name",
        help="shard name",
        dest="name",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--max-session-count",
        help="max session count",
        dest="max_session_count",
        action="store",
        default=0,
        type=int,
    )

    parser_shard.add_argument(
        "--desired-service-gateway-user-plane",
        "--desired-up",
        help="desired service gateway user plane (SG-UP)",
        dest="desired_service_gateway_user_plane",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--desired-network-connection",
        "--desired-nc",
        help="desired network connection",
        dest="desired_network_connection",
        action="store",
        type=str,
        nargs="*",
    )

    parser_shard.add_argument(
        "--prefixes",
        help="prefixes",
        dest="prefix",
        action="store",
        type=str,
        nargs="*",
    )

    parser_shard.add_argument(
        "--name-list",
        help="list of handles (names) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_shard.add_argument(
        "--virtual-mac",
        help="virtual mac",
        dest="virtual_mac",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--allocated-session-count",
        help="allocated session count",
        dest="allocated_session_count",
        action="store",
        type=int,
    )

    parser_shard.add_argument(
        "--current-service-gateway-user-plane",
        "--current-up",
        help="current service gateway user plane (SG-UP)",
        dest="current_service_gateway_user_plane",
        default="",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--current-tsf-network-connection",
        help="tsf network connection" "<string, string>",
        dest="current_tsf_network_connection",
        action=StoreDictKeyPairToDict,
        default=[],
        metavar="KEY=VAL",
        nargs="+",
    )

    parser_shard.add_argument(
        "--mbb-state",
        help="mbb state",
        dest="mbb_state",
        choices=[
            "non_mbb_move_requried",
            "userplane_mbb_initiation_required",
            "upstream_switchover_required",
            "downstream_switchover_required",
            "upstream_finalization_required",
            "mbb_complete",
            "mbb_failure",
        ],
        default="non_mbb_move_requried",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--service-group-supported",
        "--sgs",
        help="service groups supported",
        dest="service_groups_supported",
        action="store",
        type=str,
        nargs="*",
    )

    parser_shard.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    parser_shard.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    # Session Context
    parser_session = subparsers.add_parser("session", help="manage session context(s)")

    parser_session.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
            "lookup",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_session.add_argument(
        "--name",
        "-n",
        help="session name",
        dest="name",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--traffic-steering-function",
        "--tsf",
        help="traffic steering function",
        dest="traffic_steering_function",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--desired-shard",
        help="desired shard",
        dest="desired_shard",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--required-service-group",
        "--rsg",
        help="required service group",
        dest="required_service_group",
        action="store",
        default=[],
        type=str,
        nargs="*",
    )

    parser_session.add_argument(
        "--required-quality",
        "--qos",
        help="required qos",
        dest="required_quality",
        default=0,
        action="store",
        type=int,
    )

    parser_session.add_argument(
        "--name-list",
        help="list of handles (names) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_session.add_argument(
        "--source-mac",
        "--source-mac-address",
        help="source mac address",
        dest="source_mac_address",
        default="",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--s-tag",
        "--stag",
        "--svlan",
        help="VLAN S-TAG",
        dest="svlan",
        default=0,
        action="store",
        type=int,
    )

    parser_session.add_argument(
        "--c-tag",
        "--ctag",
        "--cvlan",
        help="VLAN C-TAG",
        dest="cvlan",
        default=0,
        action="store",
        type=int,
    )

    parser_session.add_argument(
        "--circuit-id",
        help="circuit id",
        dest="circuit_id",
        default="",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--remote-id",
        help="remote id",
        dest="remote_id",
        default="",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--current-shard-up",
        help="current up shard",
        dest="current_up_shard",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--current-shard-tsf",
        help="current tsf shard",
        dest="current_tsf_shard",
        action="store",
        type=str,
    )

    parser_session.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    # TrafficSteeringFunction
    parser_tsf = subparsers.add_parser(
        "tsf", help="manage traffic steering function(s)"
    )

    parser_tsf.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_tsf.add_argument(
        "--name",
        "-n",
        help="traffic steering function name",
        dest="name",
        action="store",
        type=str,
    )

    parser_tsf.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    parser_tsf.add_argument(
        "--default-endpoint",
        "--endpoint",
        "--ep",
        help="default endpoint",
        dest="endpoint",
        action=StoreDictKeyPair,
        default=[],
        metavar="KEY=VAL",
        nargs="+",
    )

    parser_tsf.add_argument(
        "--name-list",
        help="list of handles (names) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_tsf.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    # NetworkConnection
    parser_nc = subparsers.add_parser("nc", help="manage network connection(s)")

    parser_nc.add_argument(
        "subcmd",
        help="subcmd",
        choices=[
            "create",
            "update",
            "delete",
            "get",
            "list",
        ],
        default="list",
        type=str,
        nargs="?",
    )

    parser_nc.add_argument(
        "--name",
        "-n",
        help="nc name",
        dest="name",
        action="store",
        type=str,
    )

    parser_nc.add_argument(
        "--maintenance",
        "-m",
        help="set nc maintenance status",
        dest="maintenance",
        choices=["none", "drain", "drain_and_delete"],
        action="store",
        default="none",
        type=str,
    )

    parser_nc.add_argument(
        "--maximum-supported-quality",
        "--qos",
        help="maximum supported quality",
        dest="maximum_supported_quality",
        action="store",
        default=0,
        type=int,
    )

    parser_nc.add_argument(
        "--allocated-shards",
        help="number of allocated shards",
        dest="allocated_shards",
        action="store",
        default=0,
        type=int,
    )

    parser_nc.add_argument(
        "--nc-spec-type",
        "--nc-spec",
        help="nc spec",
        dest="nc_spec_type",
        choices=["SsPtpSpec", "SsMptpSpec", "MsPtpSpec", "MsMptpSpec"],
        action="store",
        type=str,
    )

    parser_nc.add_argument(
        "--service-gateway-endpoints",
        "--sg-eps",
        help="service gateway endpoints",
        dest="sgup_endpoints",
        action=StoreDictKeyPair,
        metavar="KEY=VAL",
        nargs="+",
    )

    parser_nc.add_argument(
        "--tsf-endpoints",
        "--tsf-eps",
        help="tsf endpoints",
        dest="tsf_endpoints",
        action=StoreDictKeyPair,
        metavar="KEY=VAL",
        nargs="+",
    )

    parser_nc.add_argument(
        "--nc-active-status",
        "--nc-active",
        help="active network connections" "( dict<string, bool> my-nc: True )",
        dest="nc_active",
        action=StoreDictKeyPairToDict,
        metavar="KEY=VAL",
        default={},
        nargs="+",
    )

    parser_nc.add_argument(
        "--name-list",
        help="list of handles (names) to retrieve from UPSF",
        dest="name_list",
        action="store",
        type=str,
        nargs="*",
    )

    parser_nc.add_argument(
        "--list-merge-strategy",
        "-lms",
        dest="list_merge_strategy",
        choices=["union", "replace", "subtract"],
        default="union",
        action="store",
        type=str,
    )

    parser_nc.add_argument(
        "--description",
        "-d",
        help="description",
        dest="description",
        action="store",
        type=str,
    )

    return parser.parse_args(sys.argv[1:])


def main():
    """main routine"""

    defaults = {
        # upsf host, default: 127.0.0.1
        "upsf_host": os.environ.get("UPSF_HOST", "127.0.0.1"),
        # upsf port, default: 50051
        "upsf_port": os.environ.get("UPSF_PORT", 50051),
        # loglevel, default: 'info'
        "loglevel": os.environ.get("LOGLEVEL", "info"),
    }

    loglevels = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "debug": logging.DEBUG,
    }

    if len(sys.argv) <= 1:
        sys.argv.extend(["-h"])

    args = parse_arguments(defaults, loglevels)

    # configure logging, here: root logger
    log = logging.getLogger("")

    # add StreamHandler
    hnd = logging.StreamHandler()
    formatter = logging.Formatter(
        f"%(asctime)s: [%(levelname)s] host: {socket.gethostname()}, "
        f"process: {sys.argv[0]}, "
        "module: %(module)s, "
        "func: %(funcName)s, "
        "trace: %(exc_text)s, "
        "message: %(message)s"
    )
    hnd.setFormatter(formatter)
    hnd.setLevel(loglevels[args.loglevel])
    log.addHandler(hnd)

    # set log level of root logger
    log.setLevel(loglevels[args.loglevel])

    log.debug(vars(args))

    upsf = UPSF(
        upsf_host=args.upsf_host,
        upsf_port=args.upsf_port,
    )

    funcs = {
        # "create": {
        #     "create": do_create_item,
        # },
        "update": {
            "update": do_update_item,
        },
        "delete": {
            "delete": do_delete_items,
        },
        "list": {
            "list": do_list_item,
        },
        "subscribe": {
            "subscribe": do_subscribe,
        },
        "sg": {
            "create": do_service_gateway_create,
            "update": do_service_gateway_update,
            "delete": do_service_gateway_delete,
            "get": do_service_gateway_get,
            "list": do_service_gateway_list,
        },
        "up": {
            "create": do_user_plane_create,
            "update": do_user_plane_update,
            "delete": do_user_plane_delete,
            "get": do_user_plane_get,
            "list": do_user_plane_list,
        },
        "shard": {
            "create": do_shard_create,
            "update": do_shard_update,
            "delete": do_shard_delete,
            "get": do_shard_get,
            "list": do_shard_list,
        },
        "session": {
            "create": do_session_context_create,
            "update": do_session_context_update,
            "delete": do_session_context_delete,
            "get": do_session_context_get,
            "list": do_session_context_list,
            "lookup": do_session_context_lookup,
        },
        "tsf": {
            "create": do_traffic_steering_function_create,
            "update": do_traffic_steering_function_update,
            "delete": do_traffic_steering_function_delete,
            "get": do_traffic_steering_function_get,
            "list": do_traffic_steering_function_list,
        },
        "nc": {
            "create": do_network_connection_create,
            "update": do_network_connection_update,
            "delete": do_network_connection_delete,
            "get": do_network_connection_get,
            "list": do_network_connection_list,
        },
    }

    with contextlib.suppress(Exception):
        if funcs.get(args.cmd, {}).get(args.subcmd, None) is None:
            return 1
    return funcs[args.cmd][args.subcmd](upsf, **vars(args))


if __name__ == "__main__":
    main()
