while pgrep -f "bench_ab.py 8 S_reb,S_D0" > /dev/null; do sleep 5; done
timeout 1500 /workspace/scratch_er_dropout/venv/bin/python bench_ab.py 8 S_reb,S_SOA,S_U4,S_U4_KM4,A_reb 0 > bench6.log 2>&1
