#!/usr/bin/env python3

# BSD 3-Clause License
#
# Copyright (c) 2023, BISDN GmbH
# All rights reserved.

"""upsf connector module"""

# pylint: disable=no-member
# pylint: disable=too-many-locals
# pylint: disable=too-many-nested-blocks
# pylint: disable=too-many-statements
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-branches

import os
import sys
import enum
import time
import logging
import argparse
import socket
import threading
import contextlib
import traceback

from upsf_client.upsf import (
    UPSF,
    UpsfError,
)


class ItemStatus(enum.Enum):
    """ItemStatus"""

    UNKNOWN = 0
    ACTIVE = 1
    UPDATING = 2
    DELETING = 3
    DELETED = 4
    INACTIVE = 5


class UpsfConnector(threading.Thread):
    """class UpsfConnector"""

    _defaults = {
        "upsf_host": os.environ.get("UPSF_HOST", "127.0.0.1"),
        "upsf_port": os.environ.get("UPSF_PORT", 50051),
        "loglevel": os.environ.get("LOGLEVEL", "info"),
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
        self._service_gateways = {}
        self._service_gateway_user_planes = {}
        self._traffic_steering_functions = {}
        self._network_connections = {}
        self._shards = {}
        self._session_contexts = {}
        self._rlock = threading.RLock()
        self.initialize(**kwargs)

    def initialize(self, **kwargs):
        """initialize"""
        for key, value in self._defaults.items():
            setattr(self, key, kwargs.get(key, value))

        # logger
        self._log = logging.getLogger(__name__)
        self._log.setLevel(self._loglevels[self.loglevel])

        self._upsf = UPSF(
            upsf_host=self.upsf_host,
            upsf_port=self.upsf_port,
        )

        self.sync(self._upsf)

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

    def sync(self, _upsf):
        """synchronize upsf database"""
        with self._rlock:
            try:
                self._service_gateways = {}
                for sgateway in _upsf.list_service_gateways():
                    self._service_gateways[sgateway.id] = sgateway
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync service gateway",
                            "sg.id": sgateway.id,
                            "sg.name": self._service_gateways[
                                sgateway.id
                            ].metadata.name,
                        }
                    )

                self._service_gateway_user_planes = {}
                for uplane in _upsf.list_service_gateway_user_planes():
                    self._service_gateway_user_planes[uplane.id] = uplane
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync service gateway user plane",
                            "up.id": uplane.id,
                            "up.name": self._service_gateway_user_planes[
                                uplane.id
                            ].metadata.name,
                        }
                    )

                self._traffic_steering_functions = {}
                for tsf in _upsf.list_traffic_steering_functions():
                    self._traffic_steering_functions[tsf.id] = tsf
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync traffic steering function",
                            "tsf.id": tsf.id,
                            "tsf.name": self._traffic_steering_functions[
                                tsf.id
                            ].metadata.name,
                        }
                    )

                self._network_connections = {}
                for netconn in _upsf.list_network_connections():
                    self._network_connections[netconn.id] = netconn
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync network connection",
                            "netconn.id": netconn.id,
                            "netconn.name": self._network_connections[
                                netconn.id
                            ].metadata.name,
                        }
                    )

                self._shards = {}
                for shard in _upsf.list_shards():
                    self._shards[shard.id] = shard
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync shard",
                            "shard.id": shard.id,
                            "shard.name": self._shards[shard.id].metadata.name,
                        }
                    )

                self._session_contexts = {}
                for context in _upsf.list_session_contexts():
                    self._session_contexts[context.id] = context
                    self.log.info(
                        {
                            "entity": str(self),
                            "event": "sync context",
                            "context.id": context.id,
                            "context.name": self._session_contexts[
                                context.id
                            ].metadata.name,
                            "context.lladdr": self._session_contexts[
                                context.id
                            ].spec.session_filter.mac_address,
                            "context.s_tag": self._session_contexts[
                                context.id
                            ].spec.session_filter.svlan,
                            "context.c_tag": self._session_contexts[
                                context.id
                            ].spec.session_filter.cvlan,
                            "context.circuit_id": self._session_contexts[
                                context.id
                            ].spec.session_filter.circuit_id,
                            "context.remote_id": self._session_contexts[
                                context.id
                            ].spec.session_filter.remote_id,
                        }
                    )

                self.map_all_contexts()

            except UpsfError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "sync, error occurred",
                        "error": error,
                    }
                )

    def context_dump(self):
        """dump all session contexts"""
        for _, context in self._session_contexts.items():
            self.log.info(
                {
                    "entity": str(self),
                    "event": "context_dump",
                    "context.id": context.id,
                    "context.name": context.metadata.name,
                    "context.lladdr": context.spec.session_filter.mac_address,
                    "context.s_tag": context.spec.session_filter.svlan,
                    "context.c_tag": context.spec.session_filter.cvlan,
                    "context.circuit_id": context.spec.session_filter.circuit_id,
                    "context.remote_id": context.spec.session_filter.remote_id,
                    "shard.id": context.spec.desired_shard,
                }
            )

    def shard_default(self):
        """get default shard"""
        for shard_id, shard in self._shards.items():
            if shard.metadata.name != "default":
                continue
            return shard_id
        return None

    def map_all_contexts(self):
        """assign a shard to each session context without desired or invalid shard"""

        with self._rlock:
            try:
                for _, context in self._session_contexts.items():
                    self.map_context(context)

                self.context_dump()

            except UpsfError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "map_all_contexts, error occurred",
                        "error": error,
                        "traceback": traceback.format_exc(),
                    }
                )

    def map_context(self, context):
        """assign a shard to a session context without desired or invalid shard"""

        with self._rlock:
            try:
                # no shards at all
                if len(self._shards) == 0:
                    self.log.warning(
                        {
                            "entity": str(self),
                            "event": "map_context: no shards available",
                        }
                    )

                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "map_context: no shards available",
                            "context.id": context.id,
                            "context.name": context.metadata.name,
                            "context.item_status": ItemStatus(
                                context.metadata.item_status
                            ).value,
                            "context.spec.desired_shard": context.spec.desired_shard,
                            "context.status.current_shard": context.status.current_shard,
                        }
                    )

                    # ignore contexts under deletion
                    if ItemStatus(context.metadata.item_status) in (
                        ItemStatus.DELETING,
                        ItemStatus.DELETED,
                    ):
                        return
                    if context.spec.desired_shard in ("", None):
                        return
                    # update session context
                    params = {
                        "name": context.metadata.name,
                        "desired_shard": "",
                        "current_shard": "",
                    }

                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "map_context: no shards available",
                            "context.id": context.id,
                            "context.name": context.metadata.name,
                            "context.spec.desired_shard": context.spec.desired_shard,
                            "context.status.current_shard": context.status.current_shard,
                            "params": params,
                        }
                    )

                    try:
                        self._upsf.update_session_context(**params)
                    except UpsfError as error:
                        self.log.error(
                            {
                                "entity": str(self),
                                "event": "map_context: no shards available, context update failed",
                                "error": error,
                                "params": params,
                            }
                        )

                # map session contexts to available shards, for now: map to shard "default"
                else:
                    # ignore contexts under deletion
                    if ItemStatus(context.metadata.item_status) in (
                        ItemStatus.DELETING,
                        ItemStatus.DELETED,
                    ):
                        return
                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "map_context: validate shard assignment",
                            "context.id": context.id,
                            "context.name": context.metadata.name,
                            "context.item_status": ItemStatus(
                                context.metadata.item_status
                            ).name,
                            "context.spec.desired_shard": context.spec.desired_shard,
                            "context.status.current_shard": context.status.current_shard,
                            "shards": self._shards.keys(),
                        }
                    )

                    # ignore contexts with valid shard
                    if context.spec.desired_shard in self._shards:
                        return

                    # no default shard
                    shard_id = self.shard_default()
                    if shard_id is None:
                        return

                    # update session context
                    params = {
                        "name": context.metadata.name,
                        "desired_shard": shard_id,
                    }

                    self.log.debug(
                        {
                            "entity": str(self),
                            "event": "map_context: validate shard assignment",
                            "context.id": context.id,
                            "context.name": context.metadata.name,
                            "context.spec.desired_shard": context.spec.desired_shard,
                            "context.status.current_shard": context.status.current_shard,
                            "shard.id": shard_id,
                            "shard.name": self._shards[shard_id].metadata.name,
                            "params": params,
                        }
                    )

                    try:
                        self._upsf.update_session_context(**params)
                    except UpsfError as error:
                        self.log.error(
                            {
                                "entity": str(self),
                                "event": "map_context: validate shard assignment, "
                                "context update failed",
                                "error": error,
                                "params": params,
                            }
                        )

                # self.context_dump()

            except UpsfError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "map_context, error occurred",
                        "error": error,
                        "traceback": traceback.format_exc(),
                    }
                )

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
                upsf_subscriber = UPSF(
                    upsf_host=self.upsf_host,
                    upsf_port=self.upsf_port,
                )

                self.sync(self.upsf_subscriber)

                for update in upsf_subscriber.subscribe(
                    # subscribe to sh, ctx
                    subscription=[0, 1],
                ):
                    with contextlib.suppress(Exception):
                        # session contexts
                        if update.session_context.id not in ("",):
                            if ItemStatus(
                                update.session_context.metadata.item_status
                            ) not in (ItemStatus.DELETED,):
                                self._session_contexts[
                                    update.session_context.id
                                ] = update.session_context
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "rcvd UPDATE SESSION CONTEXT",
                                        "context.id": update.session_context.id,
                                        "context.name": str(
                                            update.session_context.metadata.name
                                        ),
                                        "context.spec.desired_shard": str(
                                            update.session_context.spec.desired_shard
                                        ),
                                        "context.status.current_shard": str(
                                            update.session_context.status.current_shard
                                        ),
                                    }
                                )

                                # add session to hash
                                self._session_contexts[
                                    update.session_context.id
                                ] = update.session_context

                                if (
                                    update.session_context.spec.desired_shard
                                    in (
                                        "",
                                        None,
                                    )
                                    or update.session_context.spec.desired_shard
                                    not in self._shards
                                ):
                                    # check session context to shard mappings
                                    self.map_context(update.session_context)

                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "rcvd DELETE SESSION CONTEXT",
                                        "context.id": update.session_context.id,
                                        "context.name": str(
                                            update.session_context.metadata.name
                                        ),
                                        "context.spec.desired_shard": str(
                                            update.session_context.spec.desired_shard
                                        ),
                                        "context.status.current_shard": str(
                                            update.session_context.status.current_shard
                                        ),
                                    }
                                )
                                # drop session from hash
                                self._session_contexts.pop(
                                    update.session_context.id, None
                                )

                        # shards
                        elif update.shard.id not in ("",):
                            if ItemStatus(update.shard.metadata.item_status) not in (
                                ItemStatus.DELETED,
                            ):
                                new_shard = False
                                if update.shard.id not in self._shards:
                                    new_shard = True

                                self._shards[update.shard.id] = update.shard
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "update shard",
                                        "shard.id": update.shard.id,
                                        "shard.name": update.shard.metadata.name,
                                    }
                                )

                                # check session context to shards mappings
                                if new_shard:
                                    self.map_all_contexts()

                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "delete shard",
                                        "shard.id": update.shard.id,
                                        "shard.name": update.shard.metadata.name,
                                    }
                                )

                                # update all session contexts depending on this shard
                                # for ctx_id, context in self._session_contexts.items():
                                #     if context.spec.desired_shard != update.shard.id:
                                #         continue
                                #     context.spec.desired_shard = None

                                # drop shard from hash
                                self._shards.pop(update.shard.id, None)

                                # check session context to shards mappings
                                self.map_all_contexts()

                        # service gateways
                        elif update.service_gateway.id not in ("",):
                            if ItemStatus(
                                update.service_gateway.metadata.item_status
                            ) not in (ItemStatus.DELETED,):
                                self._service_gateways[
                                    update.service_gateway.id
                                ] = update.service_gateway
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "update service gateway",
                                        "id": update.service_gateway.id,
                                        "sg": self._service_gateways[
                                            update.service_gateway.id
                                        ],
                                    }
                                )
                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "delete service gateway",
                                        "id": update.service_gateway.id,
                                        "sg": self._service_gateways[
                                            update.service_gateway.id
                                        ],
                                    }
                                )
                                self._service_gateways.pop(
                                    update.service_gateway.id, None
                                )

                        # service gateway user planes
                        elif update.service_gateway_user_plane.id not in ("",):
                            if ItemStatus(
                                update.service_gateway_user_plane.metadata.item_status
                            ) not in (ItemStatus.DELETED,):
                                self._service_gateway_user_planes[
                                    update.service_gateway_user_plane.id
                                ] = update.service_gateway_user_plane
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "update service gateway user plane",
                                        "id": update.service_gateway_user_plane.id,
                                        "up": self._service_gateway_user_planes[
                                            update.service_gateway_user_plane.id
                                        ],
                                    }
                                )
                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "delete service gateway user plane",
                                        "id": update.service_gateway_user_plane.id,
                                        "up": self._service_gateway_user_planes[
                                            update.service_gateway_user_plane.id
                                        ],
                                    }
                                )

                                # drop service gateway user plane from hash
                                self._service_gateway_user_planes.pop(
                                    update.service_gateway_user_plane.id, None
                                )

                        # traffic steering functions
                        elif update.traffic_steering_function.id not in ("",):
                            if ItemStatus(
                                update.traffic_steering_function.metadata.item_status
                            ) not in (ItemStatus.DELETED,):
                                self._traffic_steering_functions[
                                    update.traffic_steering_function.id
                                ] = update.traffic_steering_function
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "update traffic steering function",
                                        "id": update.traffic_steering_function.id,
                                        "tsf": self._traffic_steering_functions[
                                            update.traffic_steering_function.id
                                        ],
                                    }
                                )
                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "delete traffic steering function",
                                        "id": update.traffic_steering_function.id,
                                        "tsf": self._traffic_steering_functions[
                                            update.traffic_steering_function.id
                                        ],
                                    }
                                )
                                # drop traffic steering function from hash
                                self._traffic_steering_functions.pop(
                                    update.traffic_steering_function.id, None
                                )

                        # network connections
                        elif update.network_connection.id not in ("",):
                            if ItemStatus(
                                update.network_connection.metadata.item_status
                            ) not in (ItemStatus.DELETED,):
                                self._network_connections[
                                    update.network_connection.id
                                ] = update.network_connection
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "update network connection",
                                        "id": update.network_connection.id,
                                        "nc": self._network_connections[
                                            update.network_connection.id
                                        ],
                                    }
                                )
                            else:
                                self.log.info(
                                    {
                                        "entity": str(self),
                                        "event": "delete network connection",
                                        "id": update.network_connection.id,
                                        "nc": self._network_connections[
                                            update.network_connection.id
                                        ],
                                    }
                                )
                                # drop network connection from hash
                                self._network_connections.pop(
                                    update.network_connection.id, None
                                )

                    if self._stop_thread.is_set():
                        break

            except UpsfError as error:
                self.log.error(
                    {
                        "entity": str(self),
                        "event": "error occurred",
                        "error": error,
                    }
                )
                time.sleep(1)


def parse_arguments(defaults, loglevels):
    """parse command line arguments"""
    parser = argparse.ArgumentParser(sys.argv[0])

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
        "--ip-prefixes",
        help="set list of ip prefixes for default shard",
        dest="ip_prefixes",
        action="store",
        type=str,
        nargs="*",
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

    connector = UpsfConnector()
    connector.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
