import logging
import functools
import os
import sys

def set_srcfile():
    if hasattr(sys, 'frozen'): #support for py2exe
        _srcfile = "logging%s__init__%s" % (os.sep, __file__[-4:])
    elif (__file__[-4:]).lower() in ['.pyc', '.pyo']:
        _srcfile = __file__[:-4] + '.py'
    else:
        _srcfile = __file__
    _srcfile = os.path.normcase(_srcfile)

    return _srcfile

# http://stackoverflow.com/questions/4957858/ Ugly, ugly hack. I'm
# sorry.
# We have no self here because it seems not to be passed to
# the monkeypatched method
def find_caller_monkeypatch():
    """
    Find the stack frame of the caller so that we can note the source
    file name, line number and function name.
    """
    f = logging.currentframe().f_back
    rv = "(unknown file)", 0, "(unknown function)"
    while hasattr(f, "f_code"):
        co = f.f_code
        filename = os.path.normcase(co.co_filename)
        if filename in (set_srcfile(), logging._srcfile): # This line is modified.
            f = f.f_back
            continue
        rv = (filename, f.f_lineno, co.co_name)
        break
    return rv

class EasyLogger(object):
    # OVERRIDDEN = ['critical', 'error', 'warning', 'info', 'debug']
    # this gets angry in 2.7
    SEP = " "

    def __init__(self, logger=logging.getLogger(__name__)):
        self.logger = logger
        # Ugly, ugly, ugly dirty hack to fix line numbers
        self.logger.findCaller = find_caller_monkeypatch

    def _format_str(self, *args):
        return self.SEP.join([str(a) for a in args])

    def debug(self, *args):
        self.logger.debug(self._format_str(*args))

    def info(self, *args):
        self.logger.info(self._format_str(*args))

    def warning(self, *args):
        self.logger.warning(self._format_str(*args))

    def error(self,  *args):
        self.logger.error(self._format_str(*args))

    def critical(self, *args):
        self.logger.critical(self._format_str(*args))

    def __getattr__(self, name):
        return getattr(self.logger, name)


LOGGING_FMT = "<%(filename)s:%(lineno)s(%(levelname)s) - %(funcName)s() >"\
                        "%(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOGGING_FMT)

# LOG = logging.getLogger(__name__)

LOG = EasyLogger()


def log_at(new_level=logging.ERROR, logger=LOG):
    def wrap(f):
        @functools.wraps(f)
        def wrapped_f(*args, **kwargs):
            old_level = logger.level
            logger.setLevel(new_level)
            to_ret = f(*args, **kwargs)
            logger.setLevel(old_level)
            return to_ret
        return wrapped_f
    return wrap
