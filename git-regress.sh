#!/bin/bash

__setup() {
	trap __teardown EXIT

	args=()
        tmp_files=()
        while [ "${1+defined}" ]; do
		case $1 in
			"-c" | "--commits")
                                if [ "$2" == '-' ]; then
                                        commits=$(</dev/stdin)
                                else
                                        commits=$2
                                fi
				shift 2
				continue
				;;
			*)
                                if [ -f "$1" ]; then
                                        # Copy files passed as arguments.
                                        local tmp_path
                                        tmp_path="$(dirname "$1")/git-regress-tmp-$(basename "$1")"
                                        cp "$1" "$tmp_path"
                                        args+=("$tmp_path")
                                        tmp_files+=("$tmp_path")
                                else
                                        args+=("$1")
                                fi
				shift
                                ;;
		esac
	done

        # Handle negative assertion.
        if [ "${args[0]}" == "!" ]; then
                good_exit_code=1
                unset args[0]
        else
                good_exit_code=0
        fi

	# Stash if there are unstaged changes.
	git diff-files --quiet
	if [[ $? == 1 ]]; then
		git stash
		unstash="git stash apply"
	else
		unstash=""
	fi

}
__teardown() {
	$unstash
        rm "${tmp_files[@]}"
	unset -v args commits negate unstash tmp_files
}

__exhausted() {
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	echo "REPO EXHAUSTED: $1"
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	git checkout master --force
	exit 1
}
__exhausted_no_success() {
	__exhausted "Command Never Succeeded"
}
__exhausted_no_fail() {
	__exhausted "Command Never Failed"
}

__print_result() {
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	echo "REGRESSION IDENTIFIED:"
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	git --no-pager log -1 -p --stat --decorate
}

__assert_command_fails() {
        # HACK Python cache invalidation uses timestamps and we're moving too fast for that.
        find . -name '.git' -prune -o -name '*.pyc' -exec rm {} \;

        "$@"

        if [[ $? == "$good_exit_code" ]]; then
                # Return a bad exit code if the command succeeds.
                return 1
        else
                # Return a good exit code if the command fails.
                return 0
        fi
}

git_regress() {
	__assert_command_fails "$@" || __exhausted_no_fail

	while true
	do
		# Step back one commit at a time...
		git checkout HEAD^ || __exhausted_no_success

		# ...executing any arguments passed until an exit code 0 is returned.
		__assert_command_fails "$@" || break
	done

	git checkout 'HEAD@{1}'
	__print_result
	git checkout master
}

git_regress_commits() {
        local commit prevline

        # Check out first commit
        commit=$(echo "$commits" | awk '{print $1; exit}')
        git checkout "$commit"

	__assert_command_fails "$@" || __exhausted_no_fail


        while read -r commit;  do
		# Step back one commit at a time...
		git checkout "$commit"

		# ...executing any arguments passed until an exit code 0 is returned.
		__assert_command_fails "$@" || break

                prevline=$commit
        done <<< "$commits"

	"$@" || __exhausted_no_success

	git checkout "$prevline"
	__print_result
	git checkout master
}

git_regress_tag() {
        # Identify the tag in which the regression was introduced.
	local prevline

	__assert_command_fails "$@" || __exhausted_no_fail

        local tagpipe
	tagpipe=$(mktemp --dry-run)
	mkfifo "$tagpipe"
	git tag | xargs -I@ git log --format=format:"%ai @%n" -1 @ | sort | awk '{print $4}' | tac > "$tagpipe" &
	while read -r tagged_commit; do
		# Step back one tag  at a time...
		git checkout "$tagged_commit"

		# ...executing any arguments passed until an exit code 0 is returned.
		__assert_command_fails "$@" || break

		prevline=$tagged_commit
	done < "$tagpipe"

	"$@" || __exhausted_no_success

	git checkout "$prevline"
	__print_result
	git checkout master
}

git_regress_bisect() {
	# PARSE ARGUMENTS (Note: Any argument order is acceptable.)
        local cmd=()
	while :; do
		case $1 in
			good | "--good")
				local good_commit=$2
				shift 2
				continue
				;;
			bad | "--bad")
				local bad_commit=$2
				shift 2
				continue
				;;
			*)
				if test $# -le 0; then
					break
				fi

                                cmd+=("$1")
				shift
		esac
	done

	__assert_command_fails "${cmd[@]}" || __exhausted_no_fail

	# ASSIGN DEFAULTS
	if [ -z "$good_commit" ]; then
		# default: first commit
		good_commit=$(git log --pretty=oneline | tail -1 | awk  '{print $1;}')
	fi
	if [ -z "$bad_commit" ]; then
		# default: current commit
		bad_commit=$(git log --pretty=oneline -1 | awk '{print $1;}')
	fi

	# BISECT
	echo "Bisecting bad commit $bad_commit and good commit $good_commit ."
	git bisect start "$bad_commit" "$good_commit"

        # HACK Python cache invalidation uses timestamps and we're moving too fast for that.
	git bisect run sh -c "find . -name '.git' -prune -o -name '*.pyc' -exec rm {} \; && ${cmd[*]}"

	# Make sure we actually have the culprit checked out.
	git checkout "$(git bisect view --format="%H")"

        # HACK Python cache invalidation uses timestamps and we're moving too fast for that.
        find . -name '.git' -prune -o -name '*.pyc' -exec rm {} \;

	# Make sure previous commit actually succeeds.
	git checkout HEAD^
	"${cmd[@]}" || __exhausted_no_success
	git checkout 'HEAD@{1}'

	# REPORT & TEARDOWN
	__print_result
	git bisect reset
}

usage() {
	read -r -d '' help <<- EOF
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
	EOF

	echo "$help"
	exit 0
}

# Print Help
if [ $# == 0 ]; then
	usage
fi
case $1 in
	help | "-h" | "--help")
		usage
		;;
esac

# Initialize $args and stash modified files.
__setup "$@"

# Execute Command
case ${args:0} in
	bisect | "-b" | "--bisect")
		git_regress_bisect "${args[@]:1}"
		;;
	tag | "-t" | "--tag")
		git_regress_tag "${args[@]:1}"
		;;
	*)
                # if [[ " ${args[@]} " == *" --commits "* ]]; then
                if [ -n "$commits" ]; then
                        git_regress_commits "${args[@]}"
                else
                        git_regress "${args[@]}"
                fi
		;;
esac
