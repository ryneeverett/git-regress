__fail() {
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	echo "REPO EXHAUSTED: Command Never Succeeded."
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	git checkout master --force
	eval $unstash
	exit 1
}

__print_result() {
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	echo "REGRESSION IDENTIFIED:"
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	git log -1 -p --stat --decorate
}

__define_stash() {
	unset -v stash unstash

	# Only stash if there are unstaged changes.
	git diff-files --quiet
	if [[ $? == 1 ]]; then
		stash="git stash"
		unstash="git stash apply"
	else
		stash=""
		unstash=""
	fi
}

__try_command() {
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
	__define_stash

	while true
	do
		# Step back one commit at a time...
		eval $stash
		git checkout HEAD^ || __fail
		eval $unstash

		# ...executing any arguments passed until an exit code 0 is returned.
		__try_command "$@" || break
	done

	eval $stash
	git checkout HEAD@{1}
	__print_result
	git checkout master
	eval $unstash

	unset -v stash unstash
}

git_regress_tag() {
# Identify the tag in which the regression was introduced.
	__define_stash

	local prevline
	local tagpipe

	tagpipe=$(mktemp -u)
	mkfifo "$tagpipe"
	git tag | xargs -I@ git log --format=format:"%ai @%n" -1 @ | sort | awk '{print $4}' | tac > $tagpipe &
	while read -r line; do
		# Step back one tag  at a time...
		eval $stash
		git checkout $line
		eval $unstash

		# ...executing any arguments passed until an exit code 0 is returned.
		__try_command "$@" || break

		prevline=$line
	done < $tagpipe

	"$@" || __fail

	eval $stash
	git checkout $prevline
	__print_result
	git checkout master
	eval $unstash

	unset -v stash unstash
}

git_regress_bisect() {
	local good_commit
	local bad_commit
	local cmd

	__define_stash
	eval $stash

	# PARSE ARGUMENTS (Note: Any argument order is acceptable.)
	while :; do
		case $1 in
			good | "--good")
				good_commit=$2
				shift 2
				continue
				;;
			bad | "--bad")
				bad_commit=$2
				shift 2
				continue
				;;
			*)
				if test $# -le 0; then
					break
				fi

				cmd="$cmd $1"
				shift
		esac
	done

	# ASSIGN DEFAULTS
	if [ -z "$good_commit" ]; then
		# default: first commit
		good_commit=`git log --pretty=oneline | tail -1 | awk  '{print $1;}'`
	fi
	if [ -z "$bad_commit" ]; then
		# default: current commit
		bad_commit=`git log --pretty=oneline -1 | awk '{print $1;}'`
	fi

	# BISECT
	echo "Bisecting bad commit $bad_commit and good commit $good_commit ."
	git bisect start $bad_commit $good_commit

	# HACK Python cache invalidation uses timestamps and we're moving too fast for that.
	cmd="find . -name '*.pyc' -delete && $cmd"

	if [ ! -z "$stash" ]; then
		# If $cmd fails, we still need to $stash before exiting.
		cmd="$unstash && $cmd; exitcode=\$? && $stash && if [ \$exitcode -ne 0 ]; then false; fi"
	fi

	git bisect run eval $cmd

	# Make sure we actually have the culprit checked out.
	git checkout $(git bisect view --format="%H")

	# Make sure previous commit actually succeeds.
	git checkout HEAD^
	eval $cmd || __fail
	git checkout HEAD@{1}

	# REPORT & TEARDOWN
	__print_result
	git bisect reset
	eval $unstash
	unset -v stash unstash
}

usage() {
	read -d '' help <<- EOF
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
	EOF

	echo "$help"
}

case $1 in
	bisect | "-b" | "--bisect")
		shift
		git_regress_bisect "$@"
		;;
	tag | "-t" | "--tag")
		shift
		git_regress_tag "$@"
		;;
	help | "-h")
		usage
		;;
	*)
		if [ $# == 0 ]; then
			usage
		else
			git_regress "$@"
		fi
		;;
esac
