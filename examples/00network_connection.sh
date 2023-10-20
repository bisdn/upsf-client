#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client nc create -n nc-1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client nc update -n nc-1 --qos 380 --maintenance=drain --allocated-shards 3 --sg-eps type=vtep name=vxlan0 ip_address=33.33.33.33 udp_port=4789 vni=99999 --tsf-endpoints type=vtep name=vxlan1 ip_address=33.33.33.34 udp_port=4789 vni=99999 type=l2vpn name=mpls0 vpn_id=11111 --nc-spec-type SsMptpSpec --nc-active vxlan0=true vxlan1=true mpls0=true
    #env UPSF_HOST=172.26.98.1 upsf-client nc update -n nc-1 --qos 380  --maintenance=drain --allocated-shards 3 --sg-eps type=vtep name=vxlan0 ip_address=33.33.33.33 udp_port=4789 vni=99999 --tsf-endpoints type=l2vpn name=mpls0 vpn_id=11111 --nc-spec-type MsPtpSpec
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client nc delete -n nc-1
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client nc
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
