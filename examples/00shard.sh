#!/bin/bash

case "$1" in
  create)
    env UPSF_HOST=172.26.98.1 upsf-client shard create -n shard-1
    ;;
  update)
    env UPSF_HOST=172.26.98.1 upsf-client shard update -n shard-1 -d "this is shard shard-1" --desired-up up-1.b
    ;;
  delete)
    env UPSF_HOST=172.26.98.1 upsf-client shard delete -n shard-1
    ;;
  list)
    env UPSF_HOST=172.26.98.1 upsf-client shard
    ;;
  *)
    echo "usage: $0 [create|update|delete|list]"
    ;;
esac
