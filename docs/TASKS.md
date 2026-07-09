## TASK_ID: FLOW-001

STATUS: done
TYPE: write_file

GOAL:
Create a test file inside workspace

PATH:
projects/flow/workspace/test.txt

CONTENT:
Flow test task executed

VALIDATION:
- file_exists: projects/flow/workspace/test.txt
- contains_text: projects/flow/workspace/test.txt | Flow test task executed

## TASK_ID: FLOW-002

STATUS: done
TYPE: append_file

GOAL:
Append a second line to the test file

PATH:
projects/flow/workspace/test.txt

CONTENT:
Second line added by Ofa Jack

VALIDATION:
- contains_text: projects/flow/workspace/test.txt | Second line added by Ofa Jack

## TASK_ID: FLOW-004

STATUS: done
TYPE: write_file

GOAL:
Create a second log file in files/

PATH:
projects/flow/files/ofa_jack_log_2.txt

CONTENT:
Second safe write by Ofa Jack

VALIDATION:
- file_exists: projects/flow/files/ofa_jack_log_2.txt
- contains_text: projects/flow/files/ofa_jack_log_2.txt | Second safe write by Ofa Jack

## TASK_ID: FLOW-005

STATUS: done
TYPE: write_file

GOAL:
Create a marker file to test task reading layer

PATH:
projects/flow/files/task_reader_probe.txt

CONTENT:
Task reader layer test

VALIDATION:
- file_exists: projects/flow/files/task_reader_probe.txt
- contains_text: projects/flow/files/task_reader_probe.txt | Task reader layer 

## TASK_ID: FLOW-006

STATUS: done
TYPE: write_file

GOAL:
Write another file in workspace/

PATH:
projects/flow/workspace/flow_006.txt

CONTENT:
FLOW-006 executed by Ofa Jack


VALIDATION:
- file_exists: projects/flow/files/task_reader_probe.txt
- contains_text: projects/flow/files/task_reader_probe.txt | Task reader layer test

## TASK_ID: FLOW-007

STATUS: DONE
TYPE: append_file

GOAL:
Append to previous file

PATH:
projects/flow/workspace/flow_006.txt

CONTENT:
FLOW-007 appended by Ofa Jack

VALIDATION:
- contains_text: projects/flow/workspace/flow_006.txt | FLOW-007 appended by Ofa Jack

## TASK_ID: FLOW-008

STATUS: DONE
TYPE: write_file

GOAL:
Create a file in a new folder

PATH:
projects/flow/logs/flow_008.txt

CONTENT:
FLOW-008 created by Ofa Jack

VALIDATION:
- file_exists: projects/flow/logs/flow_008.txt
- contains_text: projects/flow/logs/flow_008.txt | FLOW-008 created by Ofa Jack


## TASK_ID: FLOW-009
STATUS: done
TYPE: write_file

GOAL:
Create another test file

PATH:
projects/flow/workspace/flow_009.txt

CONTENT:
Flow task 009 executed

VALIDATION:
- file_exists: projects/flow/workspace/flow_009.txt
- contains_text: projects/flow/workspace/flow_009.txt | Flow task 009 executed

## TASK_ID: FLOW-010
STATUS: done
TYPE: append_file

GOAL:
Append to flow_009.txt

PATH:
projects/flow/workspace/flow_009.txt

CONTENT:
Second line for 009

VALIDATION:
- file_exists: projects/flow/workspace/flow_009.txt
- contains_text: projects/flow/workspace/flow_009.txt | Flow task 009 executed

## TASK_ID: FLOW-011

STATUS: done
TYPE: write_file

GOAL:
Test auto status update

PATH:
projects/flow/workspace/flow_011.txt

CONTENT:
Auto status test

VALIDATION:
- file_exists: projects/flow/workspace/flow_011.txt
- contains_text: projects/flow/workspace/flow_011.txt | Auto status test

## TASK_ID: FLOW-FAIL-001
STATUS: failed
TYPE: write_file

GOAL:
Force validation failure for state transition testing

PATH:
projects/flow/workspace/fail_test.txt

CONTENT:
hello world

VALIDATION:
- file_exists: projects/flow/workspace/fail_test.txt
- contains_text: projects/flow/workspace/fail_test.txt | definitely_not_in_file


## TASK_ID: FLOW-BLOCK-001
STATUS: blocked
TYPE: write_file

GOAL:
Verify out-of-root write is blocked

PATH:
../escape.txt

CONTENT:
should never be written

VALIDATION:
- file_exists: ../escape.txt

## TASK_ID: FLOW-STAB-001
STATUS: done
TYPE: write_file

GOAL:
Create first stability proof file

PATH:
projects/flow/workspace/stab_001.txt

CONTENT:
stability run 001

VALIDATION:
- file_exists: projects/flow/workspace/stab_001.txt
- contains_text: projects/flow/workspace/stab_001.txt | stability run 001

## TASK_ID: FLOW-STAB-002
STATUS: done
TYPE: append_file

GOAL:
Append to first stability proof file

PATH:
projects/flow/workspace/stab_001.txt

CONTENT:
second line 001

VALIDATION:
- file_exists: projects/flow/workspace/stab_001.txt
- contains_text: projects/flow/workspace/stab_001.txt | second line 001

## TASK_ID: FLOW-STAB-003
STATUS: done
TYPE: write_file

GOAL:
Create second stability proof file

PATH:
projects/flow/workspace/stab_002.txt

CONTENT:
stability run 002

VALIDATION:
- file_exists: projects/flow/workspace/stab_002.txt
- contains_text: projects/flow/workspace/stab_002.txt | stability run 002

## TASK_ID: FLOW-STAB-004
STATUS: done
TYPE: append_file

GOAL:
Append to second stability proof file

PATH:
projects/flow/workspace/stab_002.txt

CONTENT:
second line 002

VALIDATION:
- file_exists: projects/flow/workspace/stab_002.txt
- contains_text: projects/flow/workspace/stab_002.txt | second line 002

## TASK_ID: FLOW-STAB-005
STATUS: done
TYPE: write_file

GOAL:
Create third stability proof file

PATH:
projects/flow/workspace/stab_003.txt

CONTENT:
stability run 003

VALIDATION:
- file_exists: projects/flow/workspace/stab_003.txt
- contains_text: projects/flow/workspace/stab_003.txt | stability run 003

## TASK_ID: FLOW-LOG-001
STATUS: done
TYPE: write_file

GOAL:
Create Flow error log helper for latest runtime failure

PATH:
projects/flow/flow_error_logger.py

CONTENT:
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


LOG_PATH = Path(__file__).resolve().parent / "flow_last_error.json"


def writeFlowErrorLog(area: str, event: str, message: str, details: str = "") -> Path:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "area": area,
        "event": event,
        "message": message,
        "details": details,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(payload, indent=2))
    return LOG_PATH

VALIDATION:
- file_exists: projects/flow/flow_error_logger.py
- contains_text: projects/flow/flow_error_logger.py | def writeFlowErrorLog
