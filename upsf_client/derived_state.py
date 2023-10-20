#!/usr/bin/env python3

# BSD 3-Clause License
#
# Copyright (c) 2023, BISDN GmbH
# All rights reserved.

""" module DerivedState """

import enum


class DerivedState(enum.Enum):
    """DerivedState"""

    # Item state is unknown or undeterminable.
    UNKNOWN = 0
    # Item exists but cannot currently be used.
    INACTIVE = 1
    # Item is active and is correctly deployed in the network.
    ACTIVE = 2
    # Item exists, but requires action to be correctly deployed.
    UPDATING = 3
    # proprietary bisdn extension
    DELETING = 4
    # proprietary bisdn extension
    DELETED = 5
