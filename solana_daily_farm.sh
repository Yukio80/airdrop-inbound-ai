#!/bin/bash
cd /root/Airdrop\ Inbound\ AI || exit 1
export PYTHONPATH=src
python3 solana_daily_farm.py >> logs/daily_cron.log 2>&1