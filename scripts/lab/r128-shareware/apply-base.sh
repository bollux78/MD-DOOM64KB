set -euo pipefail
python3 scripts/lab/apply_r81.py
python3 scripts/lab/test_r80_pixofs.py --src src
R80_EXPERIMENTS="P1+F1" python3 scripts/lab/apply_r80_performance.py
R83_CANDIDATE=sprites python3 scripts/lab/apply_r83.py
R85_CANDIDATE=all python3 scripts/lab/apply_r85.py
R88_CANDIDATE=ai python3 scripts/lab/apply_r88.py
python3 scripts/lab/apply_r89.py
R90_CANDIDATE=control python3 scripts/lab/apply_r90.py
R91_CANDIDATE=sh1 python3 scripts/lab/apply_r91.py
R92_CANDIDATE=toggle python3 scripts/lab/apply_r92.py
R95_NAME=flat python3 scripts/lab/apply_r95.py
R96_NAME=wall python3 scripts/lab/apply_r96.py
R97_NAME=shasm python3 scripts/lab/apply_r97.py
R98_CANDIDATE=sprmul python3 scripts/lab/apply_r98.py
R100_MODE=f1t R100_PREFIX=r102 R100_NAME=twoface python3 scripts/lab/apply_r100.py; R104_PREFIX=r105 R104_NAME=twoface python3 scripts/lab/apply_r104.py
python3 scripts/lab/apply_r107.py
python3 scripts/lab/apply_r113.py
python3 scripts/lab/apply_r115.py
python3 scripts/lab/apply_r116.py
python3 scripts/lab/apply_r117.py
R118_MODE=mulvc python3 scripts/lab/apply_r118.py
R119_MODE=both python3 scripts/lab/apply_r119.py
python3 scripts/lab/apply_r122.py
python3 scripts/lab/apply_r126.py
R128_MODE=all python3 scripts/lab/apply_r128.py
