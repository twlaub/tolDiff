:: Test tolDiff with tolerances

:: Test 00 - no tolerances
python ..\tolDiff.py -f tolDiff-Test00.txt input-1.txt input-2.txt

:: Test 01 - default tolerances
python ..\tolDiff.py --defaultTolerances -f tolDiff-Test01.txt input-1.txt input-2.txt

:: Test 02 - absolute tolerance
python ..\tolDiff.py --absolute 1.e-15 -f tolDiff-Test02.txt input-1.txt input-2.txt

:: Test 03 - relative tolerance
python ..\tolDiff.py --relative 1.e-16 -f tolDiff-Test03.txt input-1.txt input-2.txt
