import importlib.util, pathlib
P=pathlib.Path(__file__).parents[1]/'veip_test.py'
spec=importlib.util.spec_from_file_location('veip_test',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_sha_stable():
    assert m.sha256_obj({'b':2,'a':1})==m.sha256_obj({'a':1,'b':2})

def test_error_matcher():
    fixture={'expected':{'result_type':'EngineError','error_code':'SCHEMA_INVALID','engine_version':'0.1.0','match_scope':['error_code','engine_version']}}
    ok,_=m.compare_output(fixture,{'error_code':'SCHEMA_INVALID','engine_version':'0.1.0','message':'bad request'})
    assert ok



