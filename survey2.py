import os, sys, runpy

BASE = os.path.dirname(__file__)
TARGET = os.path.join(BASE, "youareplan-survey", "survey2.py")
sys.path.insert(0, os.path.join(BASE, "youareplan-survey"))
runpy.run_path(TARGET, run_name="__main__")
