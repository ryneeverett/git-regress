import os
import re
import time
import pprint
import shutil
import unittest

import git
import scripttest


def setUpModule():
    this_path = os.path.dirname(os.path.realpath(__file__))
    resource_path = lambda x: os.path.join(this_path, 'resources', x)
    repo_path = lambda *args: os.path.join(this_path, 'example-repo', *args)
    app_path = repo_path('application.py')

    global ENV
    ENV = scripttest.TestFileEnvironment(repo_path())
    repo = git.Repo.init(repo_path())

    shutil.copyfile(resource_path('gitignore'), repo_path('.gitignore'))
    repo.index.add([repo_path('.gitignore')])

    def trivial_commit():
        with open(repo_path('trivial.txt'), 'a') as trivial_file:
            trivial_file.write('trivial')
        repo.index.add([repo_path('trivial.txt')])
        repo.index.commit('Trivial')

    shutil.copyfile(resource_path('good_application.py'), app_path)
    repo.index.add([app_path])
    repo.index.commit('Initial commit.')

    open(repo_path('trivial.txt'), 'w').close()
    trivial_commit()
    repo.create_tag('old_release')
    time.sleep(1)  # HACK to ensure correct tag order

    shutil.copyfile(resource_path('original_test.py'), repo_path('test.py'))
    repo.index.add([repo_path('test.py')])
    repo.index.commit('Add test file.')

    trivial_commit()
    repo.create_tag('good_release')
    time.sleep(1)  # HACK to ensure correct tag order

    trivial_commit()

    shutil.copyfile(resource_path('bad_application.py'), app_path)
    repo.index.add([app_path])
    repo.index.commit('Regression')

    trivial_commit()
    repo.create_tag('bad_release')
    time.sleep(1)  # HACK to ensure correct tag order

    trivial_commit()

    global HEAD_SHA
    HEAD_SHA = repo.heads[0].commit.hexsha


class TestGitRegressBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expect_header = {
            'success': 'REGRESSION IDENTIFIED:',
            'all_bad': 'REPO EXHAUSTED: Command Never Succeeded',
            'all_good': 'REPO EXHAUSTED: Command Never Failed'
        }
        cls.expect_body = {
            'commit': 'Regression',
            'tag': 'bad_release'
        }
        cls.test_file_path = os.path.join(ENV.cwd, cls.test_file)

    @classmethod
    def execute(cls, *args, **kwargs):
        return ENV.run(*args, cwd=ENV.cwd, **kwargs)

    @classmethod
    def gitClean(cls):
        cls.execute('git', 'reset', '--hard', 'master')

    @staticmethod
    def relPath(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def setUp(self):
        shutil.copyfile(
            self.relPath('./resources/modified_test.py'), self.test_file_path)

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
                    'git', 'rev-parse', 'HEAD').stdout.rstrip('\n'),
                'dirty_cwd': self.execute(
                    'git', 'status', '--porcelain').stdout.rstrip('\n')}
            try:
                for f in repo_state['files_created']:
                    assert '__pycache__' in f

                assert not repo_state['files_deleted']

                assert repo_state['head_sha'] == HEAD_SHA

                assert not repo_state['dirty_cwd']
            except AssertionError as error:
                self.gitClean()
                raise Exception('Test changed temp directory state:\n' +
                                pprint.pformat(repo_state)) from error

    def runRegress(self, regress_args, test_result):
        # Run Regress
        expect_error = bool(test_result != 'success')
        regress_args = (
            regress_args +
            ['python', self.test_file, 'TestApp.test_' + test_result])
        result = self.execute(
            'sh', self.relPath('../git-regress.sh'), *regress_args,
            expect_stderr=True, expect_error=expect_error)

        # Test Return Code
        if test_result =='success':
            self.assertEqual(result.returncode, 0)
        else:
            self.assertNotEqual(result.returncode, 0)

        # Test Stdout
        result_type = 'tag' if '--tag' in regress_args else 'commit'
        expected_stdout = re.compile(
            '-+\n{header}\n-+\n.*{body}'.format(
                header=self.expect_header[test_result],
                body='' if expect_error else self.expect_body[result_type]),
            re.DOTALL)
        self.assertRegex(result.stdout, expected_stdout)

        return result


class TestUntracked(TestGitRegressBase):
    @classmethod
    def setUpClass(cls):
        cls.test_file = 'untracked_test.py'
        super().setUpClass()

    def tearDown(self):
        os.remove(self.test_file_path)
        super().tearDown()

    def test_consecutive_success(self):
        self.result = self.runRegress([], 'success')

    def test_bisect_success(self):
        self.result = self.runRegress(['--bisect'], 'success')

    def test_tag_success(self):
        self.result = self.runRegress(['--tag'], 'success')

    def test_consecutive_failure_all_good(self):
        self.result = self.runRegress([], 'all_good')

    def test_bisect_failure_all_good(self):
        self.result = self.runRegress(['--bisect'], 'success')

    def test_tag_failure_all_good(self):
        self.result = self.runRegress(['--tag'], 'all_good')

    def test_consecutive_failure_all_bad(self):
        self.result = self.runRegress([], 'all_bad')

    def test_bisect_failure_all_bad(self):
        self.result = self.runRegress(['--bisect'], 'all_bad')

    def test_tag_failure_all_bad(self):
        self.result = self.runRegress(['--tag'], 'all_bad')

class TestTracked(TestGitRegressBase):
    @classmethod
    def setUpClass(cls):
        cls.test_file = 'test.py'
        super().setUpClass()

    def tearDown(self):
        self.execute('git', 'reset', 'HEAD', self.test_file_path)
        self.execute('git', 'checkout', self.test_file_path)
        super().tearDown()

    def test_consecutive_success(self):
        self.result = self.runRegress([], 'success')

    def test_bisect_success(self):
        self.result = self.runRegress(['--bisect'], 'success')

    def test_tag_success(self):
        self.result = self.runRegress(['--tag'], 'success')

    def test_consecutive_failure_all_good(self):
        self.result = self.runRegress([], 'all_good')

    def test_bisect_failure_all_good(self):
        self.result = self.runRegress(['--bisect'], 'success')

    def test_tag_failure_all_good(self):
        self.result = self.runRegress(['--tag'], 'all_good')

    def test_consecutive_failure_all_bad(self):
        self.result = self.runRegress([], 'all_bad')

    def test_bisect_failure_all_bad(self):
        self.result = self.runRegress(['--bisect'], 'all_bad')

    def test_tag_failure_all_bad(self):
        self.result = self.runRegress(['--tag'], 'all_bad')


if __name__ == '__main__':
    unittest.main()
