import os
import re
import pprint
import shutil
import unittest
import subprocess

import pytest
import scripttest

REPO_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'example-repo')


def setUpModule():
    global DEBUG
    DEBUG = pytest.config.getoption('debug')

    global ENV
    ENV = scripttest.TestFileEnvironment(REPO_PATH)

    ENV.run('../resources/setup.sh')

    global HEAD_SHA
    HEAD_SHA = ENV.run('git', 'rev-parse', 'HEAD').stdout.rstrip('\n')


class RegressTestBase(object):
    @classmethod
    def setUpClass(cls):
        cls.expect_header = {
            'success': 'REGRESSION IDENTIFIED:',
            'all_bad': 'REPO EXHAUSTED: Command Never Succeeded',
            'all_good': 'REPO EXHAUSTED: Command Never Failed'
        }
        cls.expect_body = {
            'commit': 'Regression',
            'tag': 'bad_release',
            'pointless': 'Trivial. Implement pointlessness after regression.'
        }
        cls.test_file_path = os.path.join(ENV.cwd, cls.test_file)

    @classmethod
    def gitClean(cls):
        cls.execute('git', 'reset', '--hard', 'master')

    @classmethod
    def gitStatus(cls):
        return cls.execute(
            'git', 'status', '--porcelain', test=True).stdout.rstrip('\n')

    @staticmethod
    def execute(*args, **kwargs):
        if DEBUG and kwargs.get('stdin', False):
            raise Exception('In debug mode, data cannot be sent to stdin.')

        if kwargs.pop('test', False):
            return ENV.run(*args, **kwargs)
        else:
            stdout = kwargs.pop('stdout', subprocess.DEVNULL)
            stderr = kwargs.pop('stderr', subprocess.DEVNULL)
            p = subprocess.Popen(
                args, stdout=stdout, stderr=stderr, cwd=ENV.cwd, **kwargs)
            p.wait()
            return p

    @staticmethod
    def relPath(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def setUp(self):
        shutil.copyfile(
            self.relPath('./resources/modified.py'), self.test_file_path)

    def tearDown(self):
        try:
            assert hasattr(self, 'result')
        except AssertionError:  # (hopefully) test already failed
            self.gitClean()
        else:
            # Test Repo Working Directory State
            repo_state = {
                'files_created': self.result.files_created,
                'files_deleted': self.result.files_deleted,
                'head_sha': self.execute(
                    'git', 'rev-parse', 'HEAD', test=True).stdout.rstrip('\n'),
                'dirty_cwd': self.gitStatus()}
            try:
                state_changes = (
                    list(repo_state['files_created'].keys()) +
                    list(repo_state['files_deleted'].keys()))
                for f in state_changes:
                    assert '__pycache__' in f

                assert repo_state['head_sha'] == HEAD_SHA

                assert not repo_state['dirty_cwd']
            except AssertionError as error:
                self.gitClean()
                raise Exception('Test changed temp directory state:\n' +
                                pprint.pformat(repo_state)) from error

    def runRegress(self, regress_args, test_result, py_test=True, **kwargs):
        expect_error = bool(test_result != 'success')

        # Run Regress
        if py_test:
            regress_args += [
                'python', self.test_file, 'TestApp.test_' + test_result]
        command = ['/bin/sh', self.relPath('../git-regress.sh')] + regress_args

        if DEBUG in ['sh', 'all']:
            command.insert(1, '-x')
            self.execute(
                *command, stderr=None,
                stdout=subprocess.DEVNULL if DEBUG == 'sh' else None, **kwargs)
        else:
            result = self.execute(
                *command, expect_stderr=True, expect_error=expect_error,
                debug=bool(DEBUG == 'term'), test=True, **kwargs)

        if DEBUG:
            raise Exception('In debug mode, assertions are not tested.')

        # Test Return Code
        if test_result == 'success':
            self.assertEqual(result.returncode, 0)
        else:
            self.assertNotEqual(result.returncode, 0)

        # Test Stdout
        if '--tag' in regress_args:
            result_type = 'tag'
        elif '--commits' in regress_args:
            result_type = 'pointless'
        else:
            result_type = 'commit'

        expected_stdout = re.compile(
            '-+\n{header}\n-+\n.*{body}'.format(
                header=self.expect_header[test_result],
                body='' if expect_error else self.expect_body[result_type]),
            re.DOTALL)
        self.assertRegex(result.stdout, expected_stdout)

        return result

    def test_linear_success(self):
        self.result = self.runRegress([], 'success')

    def test_bisect_success(self):
        self.result = self.runRegress(['--bisect'], 'success')

    def test_tag_success(self):
        self.result = self.runRegress(['--tag'], 'success')

    def test_commits_success(self):
        with self.execute(
                'git', 'rev-list', 'HEAD', '--grep', 'pointlessness',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as commits:
            stdin = commits.stdout.read()
        self.result = self.runRegress(
            ['--commits', '-'], 'success', stdin=stdin)

    def test_linear_failure_all_good(self):
        self.result = self.runRegress([], 'all_good')

    def test_bisect_failure_all_good(self):
        self.result = self.runRegress(['--bisect'], 'all_good')

    def test_tag_failure_all_good(self):
        self.result = self.runRegress(['--tag'], 'all_good')

    def test_commits_failure_all_good(self):
        with self.execute(
                'git', 'rev-list', 'HEAD', '--grep', 'pointlessness',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as commits:
            stdin = commits.stdout.read()
        self.result = self.runRegress(
            ['--commits', '-'], 'all_good', stdin=stdin)

    def test_linear_failure_all_bad(self):
        self.result = self.runRegress([], 'all_bad')

    def test_bisect_failure_all_bad(self):
        self.result = self.runRegress(['--bisect'], 'all_bad')

    def test_tag_failure_all_bad(self):
        self.result = self.runRegress(['--tag'], 'all_bad')

    def test_commits_failure_all_bad(self):
        with self.execute(
                'git', 'rev-list', 'HEAD', '--grep', 'pointlessness',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as commits:
            stdin = commits.stdout.read()
        self.result = self.runRegress(
            ['--commits', '-'], 'all_bad', stdin=stdin)

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


class TestUntracked(RegressTestBase, unittest.TestCase):
    test_file = 'untracked_test.py'

    def tearDown(self):
        os.remove(self.test_file_path)
        super().tearDown()


class TestTracked(RegressTestBase, unittest.TestCase):
    test_file = 'test.py'

    def tearDown(self):
        self.assertIn(self.test_file, self.gitStatus())
        self.execute('git', 'reset', 'HEAD', self.test_file_path)
        self.execute('git', 'checkout', self.test_file_path)
        super().tearDown()