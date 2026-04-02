import py_compile
import sys

files = [
    "srs_engine/utils/page_index_map.py",
    "srs_engine/utils/srs_rag_index.py",
    "srs_engine/agents/upgrader_agents/section_upgrade_agent/prompt.py",
    "srs_engine/agents/upgrader_agents/section_upgrade_agent/agent.py",
    "srs_engine/core/services/generated_srs_upgrade_service.py",
    "srs_engine/core/routers/generated_srs_upgrade_router.py",
    "srs_engine/core/routers/__init__.py",
    "srs_engine/main.py",
    "srs_engine/core/routers/pages.py",
    "srs_engine/core/services/srs_service.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"FAIL: {f} -> {e}")
        errors.append(f)

if errors:
    print(f"\n{len(errors)} file(s) failed syntax check")
    sys.exit(1)
else:
    print("\nALL 10 FILES PASSED SYNTAX CHECK")
