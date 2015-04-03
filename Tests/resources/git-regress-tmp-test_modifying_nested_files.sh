#!/bin/sh
nested_file=$(cat subdir/nested.txt)
return [ "$nested_file" != 'nested file stuff' ]
