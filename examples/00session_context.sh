#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client session create -n session-1 --source-mac-address 22:22:22:22:22:22 --s-tag 50 --c-tag 100 --circuit-id circuit_id.6378A2 --remote-id fritzbox1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client session update -n session-1 -d "this is session context session-1" --s-tag 60 --current-shard-up default --current-shard-tsf default
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client session delete -n session-1
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client session
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
