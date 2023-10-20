#!/usr/bin/env python3

# BSD 3-Clause License
#
# Copyright (c) 2023, BISDN GmbH
# All rights reserved.

""" module Endpoint """

import enum


class TransportEndpoint(enum.Enum):
    """enum TransportEndpoint"""

    UNKNOWN = 0
    VTEP = 2
    L2VPN = 3
    PORTVLAN = 4


class Endpoint:
    """class Endpoint"""

    def __init__(self, endpoint=None):
        """initialize"""
        self._endpoint = endpoint

    def __str__(self):
        """return simple string"""
        return f"{self.__class__.__name__}({self.map()}])"

    def map(self):
        """return endpoint parameters as dict"""
        _params = {}
        if self._endpoint in (
            "",
            None,
        ):
            return _params

        _ep_type = TransportEndpoint(self.get_endpoint_type(self._endpoint)).value
        if _ep_type in (TransportEndpoint.UNKNOWN.value,):
            pass

        elif _ep_type in (TransportEndpoint.VTEP.value,):
            _params = {
                "name": self._endpoint.endpoint_name,
                "type": "vtep",
                "ip_address": self._endpoint.vtep.ip_address,
                "udp_port": self._endpoint.vtep.udp_port,
                "vni": self._endpoint.vtep.vni,
            }

        elif _ep_type in (TransportEndpoint.L2VPN.value,):
            _params = {
                "name": self._endpoint.endpoint_name,
                "type": "l2vpn",
                "vpn_id": self._endpoint.l2vpn.vpn_id,
            }

        elif _ep_type in (TransportEndpoint.PORTVLAN.value,):
            _params = {
                "name": self._endpoint.endpoint_name,
                "type": "port_vlan",
                "logical_port": self._endpoint.port_vlan.logical_port,
                "svlan": self._endpoint.port_vlan.svlan,
                "cvlan": self._endpoint.port_vlan.cvlan,
            }

        return _params

    @property
    def name(self):
        """return endpoint name"""
        if self._endpoint in (
            "",
            None,
        ):
            return None
        return self._endpoint.endpoint_name

    @property
    def is_unspecified(self):
        """returns true if endpoint type is unknown"""
        if self._endpoint in (
            "",
            None,
        ):
            return True
        if self.get_endpoint_type(self._endpoint) in (TransportEndpoint.UNKNOWN.value,):
            return True
        return False

    @property
    def is_valid(self):
        """returns true if endpoint type is not unknown"""
        if self._endpoint in (
            "",
            None,
        ):
            return False
        if self.get_endpoint_type(self._endpoint) not in (
            TransportEndpoint.UNKNOWN.value,
        ):
            return True
        return False

    @staticmethod
    def get_endpoint_type(item):
        """get endpoint spec"""
        spec_type = item.WhichOneof("transport_endpoint")

        if spec_type in ("Vtep", "vtep"):
            return TransportEndpoint.VTEP.value

        if spec_type in ("L2vpn", "l2vpn"):
            return TransportEndpoint.L2VPN.value

        if spec_type in ("PortVlan", "port_vlan"):
            return TransportEndpoint.PORTVLAN.value

        return TransportEndpoint.UNKNOWN.value
