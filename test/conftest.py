import os
import threading

import pytest
from spiderfoot import SpiderFootHelpers
from spiderfoot.threadpool import ThreadPoolWorker


def _test_database_path() -> str:
    """Return a test database path that is unique per pytest-xdist worker.

    Workers share SPIDERFOOT_DATA, and concurrently creating the schema in a
    single fresh database file races, so each worker gets its own file.

    Returns:
        str: path to the test database file
    """
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    name = f"spiderfoot.test.{worker}.db" if worker else "spiderfoot.test.db"
    return f"{SpiderFootHelpers.dataPath()}/{name}"


@pytest.fixture(scope="session", autouse=True)
def stop_leaked_threadpool_workers():
    """Stop thread pool workers left running by tests once the session ends.

    ThreadPoolWorker threads are non-daemon, so any pool that a test starts
    but never shuts down keeps the interpreter alive after pytest finishes.

    Yields:
        None: control returns here when the test session ends
    """
    yield
    for t in threading.enumerate():
        if isinstance(t, ThreadPoolWorker):
            t.stop = True


@pytest.fixture(autouse=True)
def default_options(request):
    request.cls.default_options = {
        '_debug': False,
        '__logging': True,  # Logging in general
        '__outputfilter': None,  # Event types to filter from modules' output
        '_useragent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',  # User-Agent to use for HTTP requests
        '_dnsserver': '',  # Override the default resolver
        '_fetchtimeout': 5,  # number of seconds before giving up on a fetch
        '_internettlds': 'https://publicsuffix.org/list/effective_tld_names.dat',
        '_internettlds_cache': 72,
        '_genericusers': ",".join(SpiderFootHelpers.usernamesFromWordlists(['generic-usernames'])),
        '__database': _test_database_path(),  # note: test database file
        '__modules__': None,  # List of modules. Will be set after start-up.
        '__correlationrules__': None,  # List of correlation rules. Will be set after start-up.
        '_socks1type': '',
        '_socks2addr': '',
        '_socks3port': '',
        '_socks4user': '',
        '_socks5pwd': '',
        '__logstdout': False
    }

    request.cls.web_default_options = {
        'root': '/'
    }

    request.cls.cli_default_options = {
        "cli.debug": False,
        "cli.silent": False,
        "cli.color": True,
        "cli.output": "pretty",
        "cli.history": True,
        "cli.history_file": "",
        "cli.spool": False,
        "cli.spool_file": "",
        "cli.ssl_verify": True,
        "cli.username": "",
        "cli.password": "",
        "cli.server_baseurl": "http://127.0.0.1:5001"
    }
