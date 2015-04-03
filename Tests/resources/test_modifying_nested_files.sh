#!/bin/sh
nested_file=$(cat subdir/nested.txt)
[ "$nested_file" != 'nested file stuff' ]
