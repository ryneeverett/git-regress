#!/bin/sh
nested_file=$(cat "$1")
[ "$nested_file" != 'nested file stuff' ]
