#!/usr/bin/bash

print_usage() {
	printf "Usage: %s <application> [arg1] [arg2] ..\n" "$(basename "$0")"
	printf "\n"
	printf "Creates a Wayland proxy and executes <application> with its WAYLAND_DISPLAY set to the proxy.\n"
	printf "All Wayland traffic is additionally parsed and shown on stdout.\n"
	printf "\n"
	printf "stdout and stderr of <application> are routed to stderr and thus mixed with Wayland debug output.\n"
	printf "You can filter it out by redirecting stderr to /dev/null like 2>/dev/null\n"
	printf "\n"
	printf "You may additionally set environment variables containing (Python) regex to filter events:\n"
	printf "\n"
	printf "  WL_DEBUG_FILTER\n"
	printf "    Only show events matching this filter.\n"
	printf "    Example: \"foreign_toplevel|layer_(shell|surface)\"\n"
	printf "\n"
	printf "  WL_DEBUG_IGNORE\n"
	printf "    Only show events NOT matching this filter.\n"
	printf "    Example: \" (wl_|xdg)\"\n"
	printf "\n"
}

if test $# -eq 0; then
	print_usage;
	exit 1
fi

# We are changing the directory so we have to resolve
# relative path names before executing wayland_proxy.py
app=$1
app_expanded=$(which "$app")
shift

if ! test -x "$app_expanded"; then
	print_usage;
	printf "\x1b[31mFailed to find executable file '%s'\x1b[m\n" "$app"
	exit 2
fi

app_expanded=$(readlink -f "$app_expanded")
args=( "$app_expanded" "$@" )

filter_args=()
if test -n "$WL_DEBUG_IGNORE"; then
	filter_args+=(
		"$WL_DEBUG_FILTER"
		"$WL_DEBUG_IGNORE"
	)
elif test -n "$WL_DEBUG_FILTER"; then
	filter_args+=(
		"$WL_DEBUG_FILTER"
	)
fi

base=$(readlink -f "$0")
base=$(dirname "$base")
cd "$base"

#./wayland_proxy.py "${args[@]}@" 2>/dev/null | ./wayland_proxy_parser_xml.py "${filter_args[@]}"
./wayland_proxy.py "${args[@]}" | ./wayland_proxy_parser_xml.py "${filter_args[@]}"
