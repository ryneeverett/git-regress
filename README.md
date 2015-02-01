Installation
------------

I just put an alias in my `.gitconfig`:

```ini
[alias]
regress = !sh -c '/path/to/git-regress.sh $@' -
```

Help
----

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
