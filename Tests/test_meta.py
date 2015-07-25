import os
import subprocess


class TestWriteOptions(object):
    @classmethod
    def setup_class(cls):
        cls.expected_std = b'REPO EXHAUSTED: Command Never Failed\n'
        cls.expected_sh = b"+ echo 'REPO EXHAUSTED: Command Never Failed'\n"

    @classmethod
    def execute(cls, write_arg, std=False, sh=False):
        p = subprocess.Popen(
            ['py.test', '--write', write_arg, 'test_regress.py',
             '-k', 'test_reverse_error_code'],
            env=os.environ.copy(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

        stdout = p.stdout.readlines()
        stderr = p.stderr.readlines()

        if std:
            assert cls.expected_std in stdout
        else:
            assert cls.expected_std not in stdout

        if sh:
            assert cls.expected_sh in stderr
        else:
            assert cls.expected_sh not in stderr

    def test_write_stdout(self):
        self.execute('std', std=True)

    def test_write_shell_debug(self):
        self.execute('sh', sh=True)

    def test_write_all(self):
        self.execute('all', std=True, sh=True)
