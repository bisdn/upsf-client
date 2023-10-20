#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client tsf create -n tsf-1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client tsf update -n tsf-1 -d "this is traffic steering function tsf-1" --ep type=vtep name=vxlan0 ip_address=11.11.11.11 udp_port=4789 vni=11111
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client tsf delete -n tsf-1
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client tsf
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
