#!/bin/bash
#SBATCH --job-name=reva_qwerty81
#SBATCH --partition=main-cpu
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=/home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/cluster.%j.out
#SBATCH --error=/home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/cluster.%j.err

cd /home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81
# Only the first link in the chain wipes a stale sentinel from a prior run.
# Successor jobs (REVA_CHAIN_N set via --export) must preserve it so that
# cancel_chain's "write sentinel, then scancel" sequence still aborts an
# already-pending successor whose dependency may fire before scancel lands.
if [ -z "$REVA_CHAIN_N" ]; then
    rm -f .reva_stop
fi

_chain_next() {
    if [ -f .reva_stop ]; then
        echo "[reva cluster] stop sentinel present, not chaining."
        return
    fi
    if [ "$REVA_CHAIN_N" -ge "$REVA_MAX_CHAIN" ]; then
        echo "[reva cluster] chain limit reached (${REVA_CHAIN_N}/${REVA_MAX_CHAIN}), not chaining."
        return
    fi
    NEXT=$((REVA_CHAIN_N + 1))
    sbatch --dependency=afterany:$SLURM_JOB_ID \
        --export=ALL,REVA_CHAIN_N=$NEXT,REVA_MAX_CHAIN=$REVA_MAX_CHAIN \
        /home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/.reva_cluster.sbatch
}
trap _chain_next EXIT

REVA_CHAIN_N=${REVA_CHAIN_N:-1}
REVA_MAX_CHAIN=${REVA_MAX_CHAIN:-1}
export REVA_CHAIN_N REVA_MAX_CHAIN

bash /home/mila/s/stephane.gazaille/qwerty81/agent_configs/qwerty81/.reva_launch.sh
