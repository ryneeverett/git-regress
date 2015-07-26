import os
import subprocess


class Shell(object):
    def __init__(self, env, write):
        self.env = env
        self.write = write
        self.git = Git(self)

    @staticmethod
    def relpath(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def execute(self, *args, **kwargs):
        kwargs['cwd'] = self.env.cwd

        if self.write and kwargs.get('stdin', False):
            raise Exception('In debug mode, data cannot be sent to stdin.')

        if kwargs.pop('test', False):
            return self.env.run(*args, **kwargs)
        else:
            stdout = kwargs.pop('stdout', subprocess.DEVNULL)
            stderr = kwargs.pop('stderr', subprocess.DEVNULL)
            p = subprocess.Popen(args, stdout=stdout, stderr=stderr, **kwargs)
            p.wait()
            return p

    def regress(self, regressargs, testfile, testresult, **kwargs):
        if kwargs.pop('py_test', True):
            regressargs += ['python', testfile, 'TestApp.test_' + testresult]
        command = ['/bin/sh', self.relpath('../git-regress.sh')] + regressargs

        if self.write in ['sh', 'all']:
            command.insert(1, '-x')
            self.execute(
                *command, stderr=None,
                stdout=subprocess.DEVNULL if self.write == 'sh' else None,
                **kwargs)
        else:
            return self.execute(
                *command, expect_stderr=True,
                expect_error=bool(testresult != 'success'),
                debug=bool(self.write == 'std'), test=True, **kwargs)


class Git(object):
    def __init__(self, shell):
        self.shell = shell

    def cleanreset(self):
        self.shell.execute('git', 'clean', '-df')
        self.shell.execute('git', 'reset', 'master')

    def status(self):
        return self.shell.execute(
            'git', 'status', '--porcelain', test=True).stdout.rstrip('\n')
