# tolDiff
A toleranced differ for checking results of regressions tests.

This is a one-file python script that uses the Hunt–McIlroy algorithm to find diffs.
The results of the algorithm are saved in a list which is then processed to remove 
diffs due to numerical differences within specified tolerances.

No optimizations to the Hunt–McIlroy algorithm have been implemented and will
not be as the intended use of the script does not require it. I built this
script for a single purpose for a program I used to work on before retiring.

I do not intend to market this software. It is free to all users without 
any reservation on my part. The software does contain functions that I 
copied from another source and then modified. I do not believe there were 
any restrictions on the function software that I copied. The source is
given in the script.
