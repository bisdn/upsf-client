#!/bin/bash

case "$1" in
  init)
    upsf-client sg create -n sg-A
    upsf-client up create -n up-A-1 --sg-name sg-A --max-session-count=1 --supported-service-group "basic-internet,auth-generic" --default-endpoint type=vtep name=up-A-1 ip_address=192.168.60.11 udp_port=4789 vni=111111
    upsf-client up create -n up-A-2 --sg-name sg-A --max-session-count=10 --supported-service-group "basic-internet,auth-generic" --default-endpoint type=vtep name=up-A-2 ip_address=192.168.60.12 udp_port=4789 vni=111111
    upsf-client up create -n up-A-3 --sg-name sg-A --max-session-count=100 --supported-service-group "dev-mgmt" --default-endpoint type=vtep name=up-A-3 ip_address=192.168.60.13 udp_port=4789 vni=111111
    upsf-client up create -n up-A-4 --sg-name sg-A --max-session-count=1000 --supported-service-group "bisdn,acme" --default-endpoint type=vtep name=up-A-4 ip_address=192.168.60.14 udp_port=4789 vni=111111
    ;;
  reset)
    upsf-client up delete -n up-A-1
    upsf-client up delete -n up-A-2
    upsf-client up delete -n up-A-3
    upsf-client up delete -n up-A-4
    upsf-client sg delete -n sg-A
    ;;
  tsfs)
    upsf-client tsf create -n tsf-B --default-endpoint type=vtep name=tsf-B ip_address=192.168.60.21 udp_port=4789 vni=111111
    upsf-client tsf create -n tsf-C --default-endpoint type=vtep name=tsf-C ip_address=192.168.60.22 udp_port=4789 vni=111111
    ;;
  no-tsfs)
    upsf-client tsf delete -n tsf-B
    upsf-client tsf delete -n tsf-C
    ;;
  *)
    echo "usage: $0 [init|reset|shards|no-shards|tsfs|no-tsfs]"
    ;;
esac
