#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client sg create -n sg-1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client sg update -n sg-1 -d "this is service gateway sg-1"
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client sg delete -n sg-1
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client sg
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
