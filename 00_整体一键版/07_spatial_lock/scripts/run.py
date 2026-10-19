from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from one_click import main
if __name__=='__main__':raise SystemExit(main())
