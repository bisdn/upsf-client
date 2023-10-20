#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client up create -n up-1.b --sg-name sg-1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client up update -n up-1.b --sg-name sg-1 --ssg ssg1,ssg2,ssg3 --ep type=vtep name=vxlan0 ip_address=11.11.11.11 udp_port=4789 vni=12345 -lms replace
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client up delete -n up-1.b
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client up
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
