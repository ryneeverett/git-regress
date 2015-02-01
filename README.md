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

git regress <cmd>
    (default) Step back one commit at a time.
git regress tag <cmd>
    Step back only through tagged commits.
git regress bisect [--good <sha>] [--bad <sha>] <cmd>
    Binary search through commits between bad and good.

git regress help
    Print this help message.
```

Examples
========

Setup
-----

> Note: this assumes you have already "installed" git regress globally as described above.

The examples can by reproduced by pulling the example submodule:

```sh
git submodule init
git submodule update
```

Now go into `ExampleRepo` and copy in `untracked_test.py`:

```sh
cd Example/ExampleRepo
cp ../untracked_test.py ./
```

You're now ready to try any of the below examples.

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
