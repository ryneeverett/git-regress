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
    src_setup = 'resources/setup.sh'
    cache_setup = '.regresscache/setup.sh'
    use_cache = (os.path.exists(cache_setup) and
                 os.path.exists(os.path.join(REPO_PATH, '.git')) and
                 filecmp.cmp(src_setup, cache_setup))

    global WRITE
    WRITE = pytest.config.getoption('write')

    global ENV
    ENV = scripttest.TestFileEnvironment(REPO_PATH, start_clear=not use_cache)

    global SHELL
    SHELL = utils.Shell(ENV, WRITE)

    if use_cache:
        SHELL.git.cleanreset()
    else:  # Only rebuild if the setup script has been modified.
        ENV.run('sh ../' + src_setup)

        if not os.path.exists('.regresscache'):
            os.mkdir('.regresscache')
        shutil.copyfile(SHELL.relpath(src_setup), SHELL.relpath(cache_setup))

    global HEAD_SHA
    HEAD_SHA = ENV.run('git', 'rev-parse', 'HEAD').stdout.rstrip('\n')


@pytest.fixture(params=['success', 'all_good', 'all_bad'])
def test_result(request):
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
        cls.test_file_path = os.path.join(ENV.cwd, cls.test_file)

    def setup_method(self, method):
        shutil.copyfile(
            SHELL.relpath('./resources/modified_test_file.py'),
            self.test_file_path)

    def teardown_method(self, method):
        try:
            assert hasattr(self, 'result')
        except AssertionError:  # (hopefully) test already failed
            SHELL.git.cleanreset()
        else:
            # Test Repo Working Directory State
            repo_state = {
                'files_created': self.result.files_created,
                'files_deleted': self.result.files_deleted,
                'head_sha': SHELL.execute(
                    'git', 'rev-parse', 'HEAD', test=True).stdout.rstrip('\n'),
                'dirty_cwd': SHELL.git.status()}
            try:
                state_changes = (
                    list(repo_state['files_created'].keys()) +
                    list(repo_state['files_deleted'].keys()))
                for f in state_changes:
                    assert '__pycache__' in f

                assert repo_state['head_sha'] == HEAD_SHA

                assert not repo_state['dirty_cwd']
            except AssertionError as error:
                SHELL.git.cleanreset()
                raise Exception('Test changed temp directory state:\n' +
                                pprint.pformat(repo_state)) from error

    def runRegress(self, regress_args, test_result, **kwargs):
        # Run Regress
        result = SHELL.regress(
            regress_args, self.test_file, test_result, **kwargs)

        if test_result != 'success':
            result_type = 'failure'
        elif '--tag' in regress_args:
            result_type = 'tag'
        elif '--commits' in regress_args:
            result_type = 'pointless'
        else:
            result_type = 'commit'

        self.checkResult(result, test_result, result_type)

        return result

    @classmethod
    def checkResult(cls, result, test_result, result_type='failure'):
        if WRITE:
            raise Exception('In debug mode, assertions are not tested.')

        # Test Return Code
        if test_result == 'success':
            assert result.returncode == 0
        else:
            assert result.returncode != 0

        # Test Stdout
        expected_stdout = re.compile(
            '.*-+\n{header}\n-+\n.*{body}'.format(
                header=cls.expect_header[test_result],
                body=cls.expect_body[result_type]),
            re.DOTALL)
        assert expected_stdout.match(result.stdout)


class TestUntracked(RegressTestBase):
    test_file = 'untracked_test.py'

    def teardown_method(self, method):
        os.remove(self.test_file_path)
        super().teardown_method(method)


class TestTracked(RegressTestBase):
    test_file = 'test.py'

    def teardown_method(self, method):
        assert self.test_file in SHELL.git.status()
        SHELL.execute('git', 'reset', 'HEAD', self.test_file_path)
        SHELL.execute('git', 'checkout', self.test_file_path)
        super().teardown_method(method)


@pytest.mark.usefixtures('test_result')
class RegressTestFeatures(RegressTestBase):
    def test_linear(self, test_result):
        self.result = self.runRegress([], test_result)

    def test_bisect(self, test_result):
        self.result = self.runRegress(['--bisect'], test_result)

    def test_tag(self, test_result):
        self.result = self.runRegress(['--tag'], test_result)

    def test_commits(self, test_result):
        with SHELL.execute(
                'git', 'rev-list', 'HEAD', '--grep', 'pointlessness',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as commits:
            stdin = commits.stdout.read()
        self.result = self.runRegress(
            ['--commits', '-'], test_result, stdin=stdin)


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
        why the test_result is 'all_bad'.
        """
        nested_file = os.path.join(REPO_PATH, 'subdir/nested.txt')
        with open(nested_file, 'a') as nested:
            nested.write('nested file stuff')

        self.result = self.runRegress(
            ['../resources/modifying_nested_files.sh', 'subdir/nested.txt'],
            'all_bad', py_test=False)

        open(nested_file, 'w').close()

    def test_reverse_error_code(self):
        """
        issue #19
        """
        self.result = SHELL.regress(['!'], self.test_file, 'all_bad')
        self.checkResult(self.result, 'all_good')
