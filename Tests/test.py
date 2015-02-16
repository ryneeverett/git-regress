import os
import pprint
import shutil
import unittest

import scripttest


def setUpModule():
    global ENV
    temp_dir = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './test-output')
    ENV = scripttest.TestFileEnvironment(temp_dir)
    ENV.run(
        'git', 'clone',
        'https://ryneeverett@bitbucket.org/ryneeverett/example-repo.git',
        expect_stderr=True)


class TestGitRegressBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expect = {
            'success': {
                'commit': '\ncommit d0af11bbcd70e83c4281628ae29c2b35bfb11fb2',
                'tag': '\ncommit 0c96d6d6871fb9d8f1e18ad0433215382411a207',
                'header': 'REGRESSION IDENTIFIED:'},
            'all_bad': {
                'commit': '',
                'tag': '',
                'header': 'REPO EXHAUSTED: Command Never Succeeded.'}
        }
        cls.example_repo_path = os.path.join(ENV.cwd, './example-repo')
        cls.test_file_path = os.path.join(cls.example_repo_path, cls.test_file)

    @classmethod
    def execute(cls, *args, **kwargs):
        return ENV.run(*args, cwd=cls.example_repo_path, **kwargs)

    @classmethod
    def gitClean(cls):
        cls.execute('git', 'reset', '--hard', 'origin/master')

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

                assert (repo_state['head_sha'] ==
                        'ba49464222c8c8a3a3ea7a3421b6b4e6e63c8dbf')

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
        expected_stdout = '-+\n{header}\n-+{commit}'.format(
            header=self.expect[test_result]['header'],
            commit=self.expect[test_result][result_type])
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

    @unittest.skip('This edge case is not yet handled.')
    def test_consecutive_failure_all_good(self):
        assert False

    @unittest.skip('This edge case is not yet handled.')
    def test_bisect_failure_all_good(self):
        assert False

    @unittest.skip('This edge case is not yet handled.')
    def test_tag_failure_all_good(self):
        assert False

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

    @unittest.skip('This edge case is not yet handled.')
    def test_consecutive_failure_all_good(self):
        assert False

    @unittest.skip('This edge case is not yet handled.')
    def test_bisect_failure_all_good(self):
        assert False

    @unittest.skip('This edge case is not yet handled.')
    def test_tag_failure_all_good(self):
        assert False

    def test_consecutive_failure_all_bad(self):
        self.result = self.runRegress([], 'all_bad')

    def test_bisect_failure_all_bad(self):
        self.result = self.runRegress(['--bisect'], 'all_bad')

    def test_tag_failure_all_bad(self):
        self.result = self.runRegress(['--tag'], 'all_bad')


if __name__ == '__main__':
    unittest.main()
