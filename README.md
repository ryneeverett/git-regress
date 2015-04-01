Installation
============

I just put an alias in my `.gitconfig`:

```ini
[alias]
regress = !sh -c '/path/to/git-regress.sh $@' -
```

Help
====

Note that any changes that are unstaged when `git regress` is invoked will be applied to old commits.

```
$ git regress help
Searches through commits, looking for the most recent in
which <cmd> suceeds (exit code 0).

git regress <cmd> [--commits <sha's>]
    (default) Linear search through commits.
git regress tag <cmd>
    Linear search only through tagged commits.
git regress bisect [--good <sha>] [--bad <sha>] <cmd>
    Binary search through commits between bad and good.

git regress help
    Print this help message.
```

Example Output
==============

The example repo is generated in the /Tests directory by simply running the tests. See [below section](#running-the-tests).

git regress
-----------

This commmand finds the most recent regressive commit.

```sh
git regress python untracked_test.py
```
...

```
--------------------------------------------------------------
REGRESSION IDENTIFIED:
--------------------------------------------------------------
commit d0af11bbcd70e83c4281628ae29c2b35bfb11fb2 (HEAD)
Author: ryneeverett <ryneeverett@gmail.com>
Date:   Sun Feb 1 00:41:05 2015 -0500

    Regression
---
 application.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

diff --git a/application.py b/application.py
index 22bcb1e..3394505 100644
--- a/application.py
+++ b/application.py
@@ -4,4 +4,4 @@ def add(a, b):

     Addition (often signified by the plus symbol "+") is one of the four elementary, mathematical operations of arithmetic
     """
-    return a + b
+    return a + 1
Previous HEAD position was d0af11b... Regression
Switched to branch 'master'
Your branch is up-to-date with 'origin/master'.
```

git regress --commit
--------------------

This is useful in combination with `git rev-list` to limit the commits under test.

```sh
cd Tests/example-repo
cp ../resources/modified_test.py .
git rev-list HEAD --grep pointlessness | git regress --commits - python modified_test.py TestApp.test_success
```

...

```
----------------------------------------------------------------------------------------------------------------------------------
REGRESSION IDENTIFIED:
----------------------------------------------------------------------------------------------------------------------------------
commit 9de5433886b3f70be37dbc9c59e02797f3a365ec (HEAD, tag: bad_release)
Author: ryneeverett <ryneeverett@gmail.com>
Date:   Tue Mar 31 21:37:59 2015 -0400

    Trivial. Implement pointlessness after regression.
---
 trivial.txt | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

diff --git a/trivial.txt b/trivial.txt
index f3b0091..9a34e2e 100644
--- a/trivial.txt
+++ b/trivial.txt
@@ -1 +1 @@
-trivialtrivialtrivialtrivialtrivialtrivialtrivial
\ No newline at end of file
+trivialtrivialtrivialtrivialtrivialtrivialtrivialtrivial
\ No newline at end of file
Previous HEAD position was 9de5433... Trivial. Implement pointlessness after regression.
Switched to branch 'master'
```

git regress bisect
------------------

This command should be significantly faster than regular `git regress` when searching a wide range of commits, but isn't guaranteed to find the most recent commit of regression.

```sh
git regress bisect python untracked_test.py
```

...

```
--------------------------------------------------------------
REGRESSION IDENTIFIED:
--------------------------------------------------------------
commit d0af11bbcd70e83c4281628ae29c2b35bfb11fb2 (HEAD, refs/bisect/bad)
Author: ryneeverett <ryneeverett@gmail.com>
Date:   Sun Feb 1 00:41:05 2015 -0500

    Regression
---
 application.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

diff --git a/application.py b/application.py
index 22bcb1e..3394505 100644
--- a/application.py
+++ b/application.py
@@ -4,4 +4,4 @@ def add(a, b):

     Addition (often signified by the plus symbol "+") is one of the four elementary, mathematical operations of arithmetic
     """
-    return a + b
+    return a + 1
Previous HEAD position was d0af11b... Regression
Switched to branch 'master'
Your branch is up-to-date with 'origin/master'.
```

git regress tag
---------------

This command finds the most recent regressive commit which has been tagged.

```sh
git regress tag python untracked_test.py
```

```
--------------------------------------------------------------
REGRESSION IDENTIFIED:
--------------------------------------------------------------
commit 0c96d6d6871fb9d8f1e18ad0433215382411a207 (HEAD, tag: bad_release)
Author: ryneeverett <ryneeverett@gmail.com>
Date:   Sun Feb 1 00:41:32 2015 -0500

    Trivial
---
 application.py | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)

diff --git a/application.py b/application.py
index 3394505..5a611fd 100644
--- a/application.py
+++ b/application.py
@@ -2,6 +2,7 @@ def add(a, b):
     """
     Adding function.

-    Addition (often signified by the plus symbol "+") is one of the four elementary, mathematical operations of arithmetic
+    Addition (often signified by the plus symbol "+") is one of the four
+    elementary, mathematical operations of arithmetic
     """
     return a + 1
Previous HEAD position was 0c96d6d... Trivial
Switched to branch 'master'
Your branch is up-to-date with 'origin/master'.
```

Running the Tests
=================

```sh
git clone https://github.com/ryneeverett/git-regress.git
cd git-regress/Tests
pip install -r requirements.txt
python3 test.py --help
```
