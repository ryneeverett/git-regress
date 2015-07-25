import os
import re
import pprint
import shutil
import filecmp
import subprocess

import pytest
import scripttest

import utils

REPO_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'example-repo')


def setup_module():
    global WRITE
    WRITE = pytest.config.getoption('write')

    global ENV
    ENV = scripttest.TestFileEnvironment(REPO_PATH)

    global SHELL
    SHELL = utils.Shell(ENV, WRITE)

    global GIT
    GIT = utils.Git(SHELL)

    srcfile = 'resources/setup.sh'
    cachefile = '__regresscache__/setup.sh'

    if filecmp.cmp(srcfile, cachefile):
        GIT.cleanreset()
    else:  # Only rebuild if the setup script has been modified.
        ENV.run('../' + srcfile)
        shutil.copyfile(SHELL.relpath(srcfile), SHELL.relpath(cachefile))

    global HEAD_SHA
    HEAD_SHA = ENV.run('git', 'rev-parse', 'HEAD').stdout.rstrip('\n')


@pytest.fixture(params=['success', 'all_good', 'all_bad'])
def testresult(request):
    return request.param


class RegressTestBase(object):
    @classmethod
    def setup_class(cls):
        cls.expect_header = {
            'success': 'REGRESSION IDENTIFIED:',
            'all_bad': 'REPO EXHAUSTED: Command Never Succeeded',
            'all_good': 'REPO EXHAUSTED: Command Never Failed'
        }
        cls.expect_body = {
            'commit': 'Regression',
            'tag': 'bad_release',
            'pointless': 'Trivial. Implement pointlessness after regression.',
            'failure': ''
        }
        cls.testfile_path = os.path.join(ENV.cwd, cls.testfile)

    def setup_method(self, method):
        shutil.copyfile(
            SHELL.relpath(
                './resources/modified_test_file.py'), self.testfile_path)

    def teardown_method(self, method):
        try:
            assert hasattr(self, 'result')
        except AssertionError:  # (hopefully) test already failed
            GIT.cleanreset()
        else:
            # Test Repo Working Directory State
            repo_state = {
                'files_created': self.result.files_created,
                'files_deleted': self.result.files_deleted,
                'head_sha': SHELL.execute(
                    'git', 'rev-parse', 'HEAD', test=True).stdout.rstrip('\n'),
                'dirty_cwd': GIT.status()}
            try:
                state_changes = (
                    list(repo_state['files_created'].keys()) +
                    list(repo_state['files_deleted'].keys()))
                for f in state_changes:
                    assert '__pycache__' in f

                assert repo_state['head_sha'] == HEAD_SHA

                assert not repo_state['dirty_cwd']
            except AssertionError as error:
                GIT.cleanreset()
                raise Exception('Test changed temp directory state:\n' +
                                pprint.pformat(repo_state)) from error

    def runRegress(self, regressargs, testresult, **kwargs):
        # Run Regress
        result = SHELL.regress(
            regressargs, self.testfile, testresult, **kwargs)

        if testresult != 'success':
            result_type = 'failure'
        elif '--tag' in regressargs:
            result_type = 'tag'
        elif '--commits' in regressargs:
            result_type = 'pointless'
        else:
            result_type = 'commit'

        self.checkResult(result, testresult, result_type)

        return result

    @classmethod
    def checkResult(cls, result, testresult, result_type='failure'):
        if WRITE:
            raise Exception('In debug mode, assertions are not tested.')

        # Test Return Code
        if testresult == 'success':
            assert result.returncode == 0
        else:
            assert result.returncode != 0

        # Test Stdout
        expected_stdout = re.compile(
            '.*-+\n{header}\n-+\n.*{body}'.format(
                header=cls.expect_header[testresult],
                body=cls.expect_body[result_type]),
            re.DOTALL)
        assert expected_stdout.match(result.stdout)


class TestUntracked(RegressTestBase):
    testfile = 'untracked_test.py'

    def teardown_method(self, method):
        os.remove(self.testfile_path)
        super().teardown_method(method)


class TestTracked(RegressTestBase):
    testfile = 'test.py'

    def teardown_method(self, method):
        assert self.testfile in GIT.status()
        SHELL.execute('git', 'reset', 'HEAD', self.testfile_path)
        SHELL.execute('git', 'checkout', self.testfile_path)
        super().teardown_method(method)


@pytest.mark.usefixtures('testresult')
class RegressTestFeatures(RegressTestBase):
    def test_linear(self, testresult):
        self.result = self.runRegress([], testresult)

    def test_bisect(self, testresult):
        self.result = self.runRegress(['--bisect'], testresult)

    def test_tag(self, testresult):
        self.result = self.runRegress(['--tag'], testresult)

    def test_commits(self, testresult):
        with SHELL.execute(
                'git', 'rev-list', 'HEAD', '--grep', 'pointlessness',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as commits:
            stdin = commits.stdout.read()
        self.result = self.runRegress(
            ['--commits', '-'], testresult, stdin=stdin)


class TestFeaturesTracked(RegressTestFeatures, TestTracked):
    pass


class TestFeaturesUntracked(RegressTestFeatures, TestUntracked):
    pass


class TestRegressions(TestUntracked):
    def test_modifying_nested_files(self):
        """
        issue #16

        The script asserts that nested.txt, which was previously an empty file,
        does not contain the text we just added to it. If regress is working
        properly it should contain that text because it was copied to a temp
        file. Therefore the script will return 1 through all commits, which is
        why the testresult is 'all_bad'.
        """
        nested_file = os.path.join(REPO_PATH, 'subdir/nested.txt')
        with open(nested_file, 'a') as nested:
            nested.write('nested file stuff')

        self.result = self.runRegress(
            ['../resources/modifying_nested_files.sh', 'subdir/nested.txt'],
            'all_bad', pytest=False)

        open(nested_file, 'w').close()

    def test_reverse_error_code(self):
        """
        issue #19
        """
        self.result = SHELL.regress(['!'], self.testfile, 'all_bad')
        self.checkResult(self.result, 'all_good')
