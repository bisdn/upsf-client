#!/bin/bash

SHARD="default-shard"
DESIRED_UP="dbng-up-a"

case "$1" in
  status)
    upsf-client shard get -n ${SHARD}
    ;;
  # UPSF => CP
  init)
    upsf-client shard update -n ${SHARD} --desired-up ${DESIRED_UP} --mbb-state userplane_mbb_initiation_required
    ;;
  # TSF => UPSF
  down)
    upsf-client shard update -n ${SHARD} --desired-up ${DESIRED_UP} --mbb-state downstream_switchover_required
    ;;
  # UPSF => CP
  complete)
    upsf-client shard update -n ${SHARD} --desired-up ${DESIRED_UP} --mbb-state mbb_complete
    ;;
  none)
    upsf-client shard update -n ${SHARD} --mbb-state non_mbb_move_requried
    ;;
  *)
    echo "usage: $0 [status|init|down|complete|none]"
    ;;
esac
