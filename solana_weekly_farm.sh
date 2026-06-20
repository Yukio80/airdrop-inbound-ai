#!/bin/bash
cd /root/Airdrop\ Inbound\ AI || exit 1
export PYTHONPATH=src
python3 solana_weekly_farm.py >> logs/cron.log 2>&1