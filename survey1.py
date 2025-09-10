import os, sys, runpy

BASE = os.path.dirname(__file__)
TARGET = os.path.join(BASE, "youareplan-survey", "survey1.py")

# youareplan-survey 폴더를 import 경로에 추가(필요시)
sys.path.insert(0, os.path.join(BASE, "youareplan-survey"))

# 실제 앱 진입점 실행
runpy.run_path(TARGET, run_name="__main__")
