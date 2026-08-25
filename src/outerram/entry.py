from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cli import main as core_main
from .types import Strategy
from .virtual import MODELS, PROFILES, SCENARIOS, run_virtual_matrix, run_virtual_qualification


def _emit(payload: dict, output: str | None, as_json: bool) -> None:
    raw=json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)
    if output:
        path=Path(output).expanduser();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw+"\n",encoding="utf-8");print(raw if as_json else path)
    else: print(raw)


def _simulate(argv:list[str])->int:
    parser=argparse.ArgumentParser(prog="outerram simulate");parser.add_argument("--profile",choices=sorted(PROFILES),default="m5-16gb");parser.add_argument("--model-profile",choices=sorted(MODELS),default="qwen38-27b-3bit-text");parser.add_argument("--reserve-gib",type=float,default=None);parser.add_argument("--strategy",choices=[s.value for s in Strategy],default=None);parser.add_argument("--inject-failure",choices=["health","marker","tool-call","tool-roundtrip","empty-stream","usage"],default=None);parser.add_argument("--output",default=None);parser.add_argument("--json",action="store_true");args=parser.parse_args(argv)
    result=run_virtual_qualification(profile_name=args.profile,model_name=args.model_profile,strategy=Strategy(args.strategy) if args.strategy else None,reserve_gib=args.reserve_gib,failure=args.inject_failure);_emit(result,args.output,args.json);return 0 if result["simulation_passed"] else 10


def _simulate_matrix(argv:list[str])->int:
    parser=argparse.ArgumentParser(prog="outerram simulate-matrix");parser.add_argument("--model-profile",choices=sorted(MODELS),default="qwen38-27b-3bit-text");parser.add_argument("--profiles",nargs="+",choices=sorted(PROFILES),default=None);parser.add_argument("--scenarios",nargs="+",choices=sorted(SCENARIOS),default=None);parser.add_argument("--output",default=None);parser.add_argument("--json",action="store_true");args=parser.parse_args(argv)
    result=run_virtual_matrix(model_name=args.model_profile,profile_names=args.profiles or None,scenario_names=args.scenarios or None);_emit(result,args.output,args.json);summary=result["summary"];return 0 if summary["compatible_rows"]==summary["rows"] else 11


def main(argv:list[str]|None=None)->int:
    args=list(sys.argv[1:] if argv is None else argv)
    if args and args[0]=="simulate": return _simulate(args[1:])
    if args and args[0]=="simulate-matrix": return _simulate_matrix(args[1:])
    return core_main(args)

if __name__=="__main__": raise SystemExit(main())
