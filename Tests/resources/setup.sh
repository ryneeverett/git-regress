#!/usr/bin/sh
__trivial_commit() {
        local append verbose
        local "${@}"

        local message='Trivial'
        if [ -n "$verbose" ]; then
                message+=". Implement pointlessness$append."
        fi

        echo 'trivial' >> 'trivial.txt'
        git add 'trivial.txt'
        git commit -m "$message"
}

__git_tag() {
        git tag -a "$1" -m "$1"
        sleep 1  # HACK to ensure correct tag order
}

git init
cp ../resources/gitignore .gitignore
git add .gitignore
cp ../resources/good_application.py application.py
git add application.py
git commit -m 'Initial commit.'

touch 'trivial.txt'
__trivial_commit

__trivial_commit verbose=true
__git_tag 'old_release'

cp ../resources/original_test.py test.py
git add test.py
git commit -m 'Add test file.'

__trivial_commit verbose=true

__trivial_commit

__git_tag 'good_release'

__trivial_commit

__trivial_commit verbose=true

cp ../resources/bad_application.py application.py
git add application.py
git commit -m 'Regression.'

__trivial_commit

__trivial_commit verbose=true append=' after regression'

__trivial_commit
__git_tag 'bad_release'

__trivial_commit verbose=true
