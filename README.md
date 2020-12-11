# Nose Tracer
Nose tracer is a method decorator used for nose testcases to log
function calls in complex testing environments to aid in debugging and root
cause analysis of test failures.

### Key Features And Behavior
* Each decorated method/function will generate a log entry
    * how the function was called
    * whether it was part of setup, test, or cleanup
    * a collapsed stack trace back to the testcase or setup/cleanup method
    * how long the function took
    * if traceback or skiptest was raised (and message)
    * arguments passed to the testcase (helpful for ddt test variations)
    * data printed in an easily parsed json format for historical analysis
* Efficient code re-use with metaclass functions and class decorators 
   to eliminate having to decorate every method
* Negligible time increase to test execution
* Customizable parameters that add descriptions, dump passed arguments, etc.
* Single line log entry per function call
* Functions are logged as they return not as they are called

### Function Classification
Each function trace has a classification in HTML tags `TRACER <test> ... </test> ...` 
* `<test>` - the function call is the testcase
* `<test_function>` called directly by the testcase
* `<test_subfunction>` indirectly called by a testcase (one or more levels)
* `<cleanup_function>` called directly by nose cleanup
* `<cleanup_subfunction>` indirectly called nose cleanup (one or more levels)
* `<setup_function>` called directly by nose setup
* `<setup_subfunction>` indirectly called by nose setup (one or more levels)

### JSON Data
Each function trace generates JSON fields

`<...>{"function_name": "get_storage_class", "called_by": "wait_for_storage_class_to_create", "start": 1607022538, 
"duration": 0, "traceback": false, "skipped": false, "msg": "",
"test": "test_selecting_pools_from_multiple_backends_excluding_all_pools_from_one",
"source": "tests/trident/functional/test_backends.py [598]", "source_class": "TridentCTL", "desc": "trident_cli"}</...>`

* function_name: the function being traced
* called_by: the calling function name
* start: date/time the function was called (seconds from epoch)
* duration: duration of the function in seconds
* traceback: boolean indicating if an exception was raised in the function
* skipped: boolean indicating if skiptest was raised in the function
* msg: traceback message if applicable
* test: the name of the testcase
* source: file and line number for the testcase
* source_class: the traced function's class
* desc: text description set by the method decorator (optional)

### Collapsed Stack Trace
Enabled by default, but optional, a one-line stack trace showing how the function was called (file:function:lineno)

`stack=['base.py:wait_for_storage_class_to_create:275', 'retrying.py:call:200', 'retrying.py:wrapped_f:49',
'base.py:create_storage_class:265',
'test_backends.py:test_selecting_pools_from_multiple_backends_excluding_all_pools_from_one:598']`

# Use

### Decorate a method/function
Here only the test_some_feature will be logged

`from tracer import trace_function_call, TRIGGER_NEVER`

`...`

`(call_stack=False, dump_args=TRIGGER_NEVER, desc="Important Test")`

`def test_some_feature():`

`...`
### Decorate all methods in a class (non-inherited)
Here only the methods in the SomeTest class are
logged. Methods of any subclasses will not be logged.

`from tracer import trace_class_methods, TRIGGER_ALWAYS`

`...`

`@trace_class_methods(call_stack=True, dump_args=TRIGGER_ALWAYS, desc="My Favorite Tests")`

`class SomeTest(testtools.TestCase):`

`...`

### Decorate all methods in a class (inherited)
Here the methods in ParentTest and ChildTest (and any
other subclasses) will be logged

`from tracer import get_tracer_metaclass, TRIGGER_ON_FAILURE`

`...`

`class ParentTest(testtools.TestCase, metaclass=get_tracer_metaclass()):`

`...`

`class ChildTest(ParentTest):`

`...`

# Log Examples
### Testcase
An example of a trace on a nose testcase.  This testcase has a ddt decorator
to pass iteration variables as arguments shown in the 

`2020-12-10 23:11:53.796 DEBUG    (EXTERNAL RESOURCE) = MainThread => TRACER <test>{"function_name":
"test_fake_virtual_pools_invalid_format", "called_by": "", "start": 1607641912, "duration": 1, "traceback": false,
"skipped": false, "msg": "", "test": "", "source": "", "source_class": "TestStorageClasses", "desc": ""}</test>
stack=[] args=(<whelk.tests.trident.functional.test_storage_classes.TestStorageClasses.test_fake_virtual_pools_invalid_format_2
id=0x7f8b9e8fc3c8>,) kwargs={'sc_parameters': {'selector': 'cost=1, cloud=aws, performance=gold'}}`

### Test Sub-function
`2020-12-10 23:11:33.826 DEBUG    (EXTERNAL RESOURCE) = MainThread => TRACER <test_subfunction>{"function_name": "_get_resource",
"called_by": "get_storage_class", "start": 1607641892, "duration": 1 , "traceback": false, "skipped": false, "msg": "",
"test": "test_default_storage_class_support_no_default_specified", "source": "tests/trident/functional/test_storage_classes.py [82]",
"source_class": "TridentCTL", "desc": "trident_cli"}</test_subfunction> stack=['cli.py:get_storage_class:66',
'base.py:wait_for_storage_class_to_create:275', 'retrying.py:call:200', 'retrying.py:wrapped_f:49', '
base.py:create_storage_class:265', 'test_storage_classes.py:test_default_storage_class_support_no_default_specified:82']`

### Cleanup Sub-function
`2020-12-10 23:08:02.481 DEBUG    (EXTERNAL RESOURCE) = MainThread => TRACER <cleanup_subfunction>{"function_name":
"delete_pvc", "called_by": "delete_pvc", "start": 1607641682, "duration": 0, "traceback": false, "skipped": false,
"msg": "", "test": "cleanup", "source": "", "source_class": "KubeCTL", "desc": "k8s_cli"}</cleanup_subfunction>
stack=['base.py:delete_pvc:303', 'runtest.py:_run_user:191', 'runtest.py:_run_cleanups:176']`

# Notes
* Currently, all test cases will always dump args (hard-coded)

