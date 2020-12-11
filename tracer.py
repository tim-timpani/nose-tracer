import os
import logging
import time
import inspect
import json
import types
from functools import wraps
from testtools.testcase import TestSkipped


# Constants for specifying a trigger
TRIGGER_NEVER = "never"
TRIGGER_ALWAYS = "always"
TRIGGER_ON_FAILURE = "on_failure"

# Used for validation
VALID_TRIGGERS = (TRIGGER_NEVER, TRIGGER_ON_FAILURE, TRIGGER_ALWAYS)


def trace_function_call(function=None, **trace_options):
    """
    Function decorator for printing debug and runtime statistics to the log file for each function call

    Can be used in several ways:
    1) As a function decorator with no arguments (uses def
        @trace_function_call
        def my_func():
    2) As a function decorator with arguments
        @trace_function_call(dump_args=tracer.TRIGGER_ALWAYS)
    3) With both function and options in a setattr() (such as class decorators or metaclasses)
        setattr(cls, function_name, trace_function_call(orig_function, dump_args=tracer.TRIGGER_ALWAYS))

    :param function: function being decorated (optional)
    :param trace_options: keyword values to configure the trace options (optional)
    :return: tracer (wraps original function) when function is provided, otherwise trace_decorator
    """
    desc = str(trace_options.get('desc', ""))
    source_class = str(trace_options.get('source_class', ""))
    dump_args = trace_options.get('dump_args', TRIGGER_ON_FAILURE)
    call_stack = bool(trace_options.get('call_stack', False))

    if dump_args not in VALID_TRIGGERS:
        raise ValueError(f"dump_args value '{dump_args}' invalid - must be one of: {VALID_TRIGGERS}")
    logger = logging.getLogger('tracer')

    def trace_decorator(decorated_function):
        """
        When trace_function_call is applied directly to a function without a function, this decorator is returned
        so python can decorate the original function.
        :param decorated_function: original function to be traced
        :return: tracer
        """

        @wraps(decorated_function)
        def tracer(*args, **kwargs):
            """Wraps around the original decorated function to log tracing information after each call"""
            start_time = time.time()
            result = None
            function_name = decorated_function.__name__
            stats = {
                'function_name': function_name,
                'called_by': "",
                'start': int(start_time),
                'duration': 0,
                'traceback': False,
                'skipped': False,
                'msg': "",
                'test': "",
                'source': "",
                'source_class': source_class,
                'desc': desc,
            }
            try:
                # Call the function being decorated
                result = decorated_function(*args, **kwargs)
            except TestSkipped as skip_exception:
                stats['msg'] = str(skip_exception)
                logger.info(f"Skipped {function_name} {skip_exception}")
                stats['skipped'] = True
                # Re-raise the traceback and sully the whelk log just so nose counts it as skipped
                raise
            except Exception as function_exception:
                # Catch any other tracebacks so we can include that information
                stats['traceback'] = True
                stats['msg'] = str(function_exception)
                # Re-raise the traceback
                raise
            finally:
                try:
                    finish_time = time.time()
                    stats['duration'] = int(finish_time - stats['start'])

                    call_strings = []
                    if stats['skipped']:
                        tag = "skipped_test"
                    elif function_name.startswith("test_"):
                        tag = "test"
                    else:
                        tag = "other_function"

                        # Loop through each caller in the stack until we reach testcase or nose runner script.
                        for call_index in range(len(inspect.stack())):

                            caller = inspect.stack()[call_index]

                            # Add the call string for dumping the call stack
                            if call_stack and caller.function != "tracer":
                                call_strings.append(":".join((os.path.basename(caller.filename),
                                                              caller.function,
                                                              str(caller.lineno))))

                            # Index 1 is the immediate caller (0 is tracer)
                            if call_index == 1:
                                stats['called_by'] = caller.function

                            # Called by testcase
                            if caller.function.startswith("test_"):
                                stats['test'] = caller.function
                                stats['source'] = f"{caller.filename} [{caller.lineno}]".partition("whelk/")[2]
                                if call_index == 1:
                                    tag = "test_function"
                                else:
                                    tag = "test_subfunction"
                                break

                            # Called by nose cleanup
                            if caller.function == "_run_cleanups":
                                stats['test'] = "cleanup"
                                if stats['called_by'] == "_run_user":
                                    tag = "cleanup_function"
                                else:
                                    tag = "cleanup_subfunction"
                                break

                            # Called by nose setup
                            if caller.function == "_run_setup":
                                stats['test'] = "setup"
                                if stats['called_by'] == "_run_setup":
                                    tag = "setup_function"
                                else:
                                    tag = "setup_subfunction"
                                break

                    if dump_args == TRIGGER_ALWAYS \
                            or tag == "test" \
                            or (dump_args == TRIGGER_ON_FAILURE and stats['traceback'] and not stats['skipped']):
                        function_args = f" args={args} kwargs={kwargs}"
                    else:
                        function_args = ""
                    if call_stack:
                        stack_string = f" stack={call_strings}"
                    else:
                        stack_string = ""
                    log_message = f"TRACER <{tag}>{json.dumps(stats)}</{tag}>{stack_string}{function_args}"
                    if tag == "test" and stats['traceback']:
                        logger.error(log_message)
                    else:
                        logger.debug(log_message)
                except Exception as trace_exception:
                    logger.warning(f"TRACER Failed to save call trace - {trace_exception}")
            return result
        return tracer

    # If the function was provided, then we can call the trace_decorator with it and return the wrapper
    # function. This allows the metrics_decorator to be used without an outer call.
    if isinstance(function, types.FunctionType):
        return trace_decorator(function)

    # If the function is none, the trace_function_call is being evaluated so return the trace_decorator
    # which will then be called by the @ syntax with the function.
    if function is None:
        return trace_decorator

    raise ValueError("Argument 'function' must be a function or None")


def trace_class_methods(call_stack=True, dump_args=TRIGGER_ON_FAILURE, desc=""):
    """
    This class decorator will walk through each attribute of a class, looking for functions
    that do not start with __ and decorating them with the trace_function_call function decorator.
    Decorating a class with this function call will only decorated the methods in that class
    and not any subclasses.
    """
    def class_decorator(cls):
        # Loop through the name of each attribute defined in the class
        for name, func in cls.__dict__.items():
            # Get the class object from it's name
            # class_object = cls.__getattribute__(cls, name)
            # Check if the object is a function (method) - this will exclude staticmethod
            if isinstance(func, types.FunctionType) and not name.startswith("__"):
                # Call the trace_function_call decorator with the function and set the value of the
                # function to be the return value (equiv to a @ above the function)
                setattr(cls, name, trace_function_call(func,
                                                       source_class=cls.__name__,
                                                       call_stack=call_stack,
                                                       dump_args=dump_args,
                                                       desc=desc
                                                       ))
        return cls

    return class_decorator


def get_tracer_metaclass(*deco_args, **deco_kwargs):
    """
    Get the TracerMetaclass with arguments passed to trace_function_call decorator
    Arguments are transparently passed to the trace_class_methods function to do all
    the work. Use this function to get the TracerMetaclass and set the metaclass
    for the parent class and all subclasses will also be decorated.
    :return: TracerMetaclass object
    """
    class TracerMetaclass(type):
        """
        MetaClass for decorating all methods in a class and it's subclasses
        Calls the trace_class_methods to perform the decoration
        """
        def __new__(mcs, *args, **kwargs):
            new_class = super().__new__(mcs, *args, **kwargs)
            class_decorator = trace_class_methods(*deco_args, **deco_kwargs)
            class_decorator(new_class)
            return new_class
    return TracerMetaclass
