import re
from buildbot.steps.shell import ShellCommand

class CoverallsCommand(ShellCommand):
    command = ["coveralls", "-E", "'/usr/.*'", "-E", "'./CMakeFiles/.*'", "-e", "deps", "-e", "tests"]

    def createSummary(self, log):
        match = re.search(r"https://coveralls.io/jobs/([0-9]+)", log.getText(), re.MULTILINE)
        if match:
            self.addURL("coverage", match.group())

