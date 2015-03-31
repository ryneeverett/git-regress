__setup() {
	trap __teardown EXIT

	args=()
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
                                        local tmp_path="$(dirname $1)/git-regress-tmp-$(basename $1)"
                                        cp "$1" "$tmp_path"
                                        args+=("$tmp_path")
                                else
                                        args+=("$1")
                                fi
				shift
                                ;;
		esac
	done

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
	unset -v args commits unstash
	find . -name 'git-regress-tmp-*' -delete
	$unstash
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
	git log -1 -p --stat --decorate
}

__assert_command_fails() {
		# HACK Python cache invalidation uses timestamps and we're moving too fast for that.
		find . -name '*.pyc' -delete

		"$@"

		if [[ $? == 0 ]]; then
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
        read -r commit < "$commits"
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

	local tagpipe=$(mktemp --dry-run)
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
	__assert_command_fails "$@" || __exhausted_no_fail

	# PARSE ARGUMENTS (Note: Any argument order is acceptable.)
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

				local cmd="$cmd $1"
				shift
		esac
	done

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
	cmd="find . -name '*.pyc' -delete && $cmd"

	git bisect run eval "$cmd"

	# Make sure we actually have the culprit checked out.
	git checkout "$(git bisect view --format="%H")"

	# Make sure previous commit actually succeeds.
	git checkout HEAD^
	eval "$cmd" || __exhausted_no_success
	git checkout 'HEAD@{1}'

	# REPORT & TEARDOWN
	__print_result
	git bisect reset
}

usage() {
	read -d '' help <<- EOF
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
