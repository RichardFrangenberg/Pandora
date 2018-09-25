import sys, pprint
from pysideuic import compileUi

fname = "InstallList"

pyfile = open(fname + "_ui.py", 'w')
compileUi(fname + ".ui", pyfile, False, 4,False)
pyfile.close()