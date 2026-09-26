#!/usr/bin/env python3
"""VEIP Conformance Runner v0.1.

This runner intentionally contains NO VEIP adjudication semantics. It validates the
frozen corpus's internal integrity and compares an external engine adapter's outputs
against frozen expected results.
"""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, sys
from pathlib import Path

SUCCESS_TYPES={"ClaimEvaluationResult","CompletionEvaluationResult","BoundaryExplanationResult"}
ERROR_TYPE="EngineError"

class CorpusError(Exception): pass

def jcs_bytes(obj):
    # v0.3 frozen corpus contains no floats and uses ASCII structural keys;
    # this serialization is byte-equivalent to RFC 8785 for corpus values.
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def sha256_obj(obj): return hashlib.sha256(jcs_bytes(obj)).hexdigest()

def manifest_hash(refs):
    fields=("evidence_id","payload_sha256","source_type","channel_ref","receipt","observed_at","subject_ref","extent_ref","run_id")
    projection=[{k:r[k] for k in fields if k in r} for r in refs]
    projection.sort(key=lambda x:x["evidence_id"].encode("utf-8"))
    return sha256_obj(projection)

def validate_corpus(corpus):
    failures=[]
    if corpus.get("suite")!="VEIP-CANONICAL-CONFORMANCE-v0.3": failures.append("unexpected suite")
    if corpus.get("engine_version")!="0.1.0": failures.append("unexpected engine_version")
    fixtures=corpus.get("fixtures")
    if not isinstance(fixtures,list) or not fixtures: failures.append("fixtures missing/empty"); return failures
    ids=[f.get("fixture_id") for f in fixtures]
    if len(ids)!=len(set(ids)): failures.append("duplicate fixture_id")
    reserved=set(corpus.get("claim_ceiling_assertions",{}).get("NO_RESERVED_CODES_EMITTED",[]))
    for f in fixtures:
        fid=f.get("fixture_id","<missing>"); e=f.get("expected",{}); q=f.get("input",{})
        rt=e.get("result_type")
        if rt in ("ClaimEvaluationResult","CompletionEvaluationResult"):
            obj={k:v for k,v in e.items() if k not in ("result_type","canonical_hash")}
            if e.get("canonical_hash")!=sha256_obj(obj): failures.append(f"{fid}: canonical_hash mismatch")
            codes=e.get("reason_codes",[])
            if codes!=sorted(codes): failures.append(f"{fid}: reason_codes not sorted")
            if set(codes)&reserved: failures.append(f"{fid}: reserved reason code emitted")
            dims=e.get("dimensions",{})
            for k in ("claim_support","execution","outcome","currentness","provenance_binding","task_completion"):
                if dims.get(k)=="ESTABLISHED_WITHIN_SCOPE": failures.append(f"{fid}: forbidden positive promotion {k}")
            if dims.get("channel_independence")!="NOT_ESTABLISHED": failures.append(f"{fid}: channel_independence ceiling violated")
        if isinstance(q,dict) and "evidence_pack" in q and rt in ("ClaimEvaluationResult","CompletionEvaluationResult"):
            pack=q["evidence_pack"]
            if pack.get("manifest_sha256")!=manifest_hash(pack.get("references",[])): failures.append(f"{fid}: manifest_sha256 mismatch")
        if rt==ERROR_TYPE:
            if e.get("match_scope")!=["error_code","engine_version"]: failures.append(f"{fid}: error matcher scope invalid")
            if e.get("engine_version")!="0.1.0": failures.append(f"{fid}: error matcher engine_version invalid")
    return failures

def compare_output(fixture, actual):
    expected=fixture["expected"]; rt=expected["result_type"]
    if rt in SUCCESS_TYPES:
        exp={k:v for k,v in expected.items() if k!="result_type"}
        return (actual==exp, None if actual==exp else {"expected":exp,"actual":actual})
    if rt==ERROR_TYPE:
        for key in expected.get("match_scope",[]):
            if actual.get(key)!=expected.get(key):
                return False,{"field":key,"expected":expected.get(key),"actual":actual.get(key)}
        if not isinstance(actual.get("message"),str) or not actual["message"]:
            return False,{"field":"message","expected":"nonempty string","actual":actual.get("message")}
        return True,None
    return False,{"error":f"unknown expected result_type {rt}"}

def invoke_engine(command,fixture,timeout):
    payload={"entry_point":fixture["entry_point"],"input":fixture["input"]}
    p=subprocess.run(shlex.split(command),input=json.dumps(payload),text=True,capture_output=True,timeout=timeout)
    if p.returncode!=0:
        raise RuntimeError(f"engine adapter exited {p.returncode}: {p.stderr.strip()}")
    try: return json.loads(p.stdout)
    except Exception as ex: raise RuntimeError(f"engine adapter returned invalid JSON: {ex}; stdout={p.stdout!r}")

def main():
    ap=argparse.ArgumentParser(prog="veip test",description="VEIP frozen-corpus conformance runner v0.1")
    ap.add_argument("corpus",type=Path)
    ap.add_argument("--validate-only",action="store_true",help="validate corpus integrity without invoking an engine")
    ap.add_argument("--engine-cmd",help="external adapter command; reads one JSON request from stdin and writes one JSON result")
    ap.add_argument("--timeout",type=float,default=10.0)
    ap.add_argument("--json-report",type=Path)
    ap.add_argument("--fixture",action="append",default=[],help="run only selected fixture id; repeatable")
    args=ap.parse_args()
    corpus=json.loads(args.corpus.read_text(encoding="utf-8"))
    integrity=validate_corpus(corpus)
    if integrity:
        for x in integrity: print("CORPUS FAIL:",x,file=sys.stderr)
        return 2
    fixtures=corpus["fixtures"]
    if args.fixture:
        wanted=set(args.fixture); fixtures=[f for f in fixtures if f["fixture_id"] in wanted]
        missing=wanted-{f["fixture_id"] for f in fixtures}
        if missing: print("Unknown fixture(s):",", ".join(sorted(missing)),file=sys.stderr); return 2
    if args.validate_only or not args.engine_cmd:
        report={"status":"PASS","mode":"validate-only","fixture_count":len(fixtures),"corpus_integrity":"PASS","engine_version":corpus["engine_version"]}
        print(f"{len(fixtures)} fixtures\ncorpus integrity PASS\nengine version: {corpus['engine_version']}")
        if args.json_report: args.json_report.write_text(json.dumps(report,indent=2)+"\n")
        return 0
    results=[]; passed=0
    for f in fixtures:
        try:
            actual=invoke_engine(args.engine_cmd,f,args.timeout)
            ok,detail=compare_output(f,actual)
        except Exception as ex:
            ok=False; detail={"exception":str(ex)}
        results.append({"fixture_id":f["fixture_id"],"pass":ok,"detail":detail})
        passed+=int(ok)
        print(("PASS" if ok else "FAIL"),f["fixture_id"])
    failed=len(fixtures)-passed
    report={"status":"PASS" if failed==0 else "FAIL","fixture_count":len(fixtures),"passed":passed,"failed":failed,"engine_version":corpus["engine_version"],"results":results}
    print(f"\n{len(fixtures)} fixtures\n{passed} PASS\n{failed} FAIL\nengine version: {corpus['engine_version']}")
    if args.json_report: args.json_report.write_text(json.dumps(report,indent=2)+"\n")
    return 0 if failed==0 else 1

if __name__=="__main__": raise SystemExit(main())



