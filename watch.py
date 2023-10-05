# Modules supporting structured logging
import logging
import logging.config
import structlog
import yaml
from datetime import datetime

import os
import psutil
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.events import EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED, EVENT_TYPE_DELETED
from watchdog.observers import Observer

from settings import LOGGER


def has_handle(fpath):
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if fpath == item.path:
                    return True
        except Exception:
            pass
    return False


class FileTrigger:
    def __init__(self, watch_dir, patterns, FlowRunner=None):
        self.observer = Observer()
        self.watch_dir = watch_dir
        self.patterns = patterns
        self.FlowRunner = FlowRunner

    def run(self):
        LOGGER.info("Watcher Started")

        if not self.FlowRunner:
            LOGGER.info("No callback function defined for events.")
            LOGGER.info("Using system print()")
            self.FlowRunner = print

        if not os.path.isdir(self.watch_dir):
            LOGGER.info("Watch directory does not exist.")
            os.mkdir(self.watch_dir)
            LOGGER.info("Directory " + self.watch_dir + " was created")

        os.chdir(self.watch_dir)
        LOGGER.info(f"Monitoring: {self.watch_dir}")

        event_handler = Handler(self.FlowRunner, self.patterns)
        self.observer.schedule(event_handler, self.watch_dir, recursive=True)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
            LOGGER.info("Watcher stopped.")

        self.observer.join()


class Handler(FileSystemEventHandler):
    def __init__(self, FlowRunner, patterns):
        super(FileSystemEventHandler).__init__()
        self.logic_function = FlowRunner
        self.patterns = patterns

    # This is the callback function for file events.
    # You can edit it to trigger at file creation, modification or deletion,
    # and have different behaviors for each.
    def on_any_event(self, event):
        if (evt := event).is_directory:
            return None
        else:
            if evt.event_type == EVENT_TYPE_CREATED:
                source = evt.src_path
                LOGGER.info(f"File created: {os.path.basename(source)}")
                for pattern in self.patterns:
                    if source.endswith(pattern):
                        LOGGER.info(f"File ends with {pattern}")
                        while has_handle(source):
                            # Block action until file is closed
                            LOGGER.info(f"Waiting for file {os.path.basename(source)}")
                            time.sleep(5)
                        LOGGER.info("Starting flow...")
                        self.logic_function(source)
                return None
            elif evt.event_type == EVENT_TYPE_MODIFIED:
                LOGGER.debug("Event type not implemented")
                return None
            elif evt.event_type == EVENT_TYPE_DELETED:
                LOGGER.debug("Event type not implemented")
                return None
            else:
                LOGGER.debug("Event type not implemented")
                return None


def translate_local_path_to_globus_path(local_path: str) -> str:
    r"""Translate a local path to a Globus-compatible path.

    On Windows, the local directory will be something like `C:\path\to\watch`.
    This must be converted to /c/path/to/watch/ when referenced as a Globus path.
    """

    if not sys.platform.lower().startswith("win"):
        return local_path

    drive, _, path = local_path.partition(":")
    drive = drive.lower()
    path = path.replace("\\", "/").strip("/")
    return f"/{drive}/{path}/"
