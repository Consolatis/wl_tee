#!/usr/bin/env -S python3 -u

import sys
import struct

(
	LOG_LEVEL_DEBUG,
	LOG_LEVEL_INFO,
	LOG_LEVEL_WARNING,
	LOG_LEVEL_ERROR
) = range(4)

LOG_COLORS = {
	LOG_LEVEL_DEBUG: 36,
	LOG_LEVEL_INFO: 37,
	LOG_LEVEL_WARNING: 33,
	LOG_LEVEL_ERROR: 31,
}

LOG_LEVEL_MIN = LOG_LEVEL_INFO

def _log(loglevel, msg):
	if loglevel < LOG_LEVEL_MIN:
		return
	fmt = "\x1b[{}m{}\x1b[m"
	print(fmt.format(LOG_COLORS.get(loglevel, 32), msg))

def log_debug(msg):
	return _log(LOG_LEVEL_DEBUG, msg)

def log_info(msg):
	return _log(LOG_LEVEL_INFO, msg)

def log_warn(msg):
	return _log(LOG_LEVEL_WARNING, msg)

def log_warning(msg):
	return _log(LOG_LEVEL_WARNING, msg)

def log_error(msg):
	return _log(LOG_LEVEL_ERROR, msg)

def wayland_parse(data, conv):
	while len(data) >= 8:
		oid, sizeop = struct.unpack(f'{conv}II', data[:8])
		size = sizeop >> 16
		op = sizeop & 0xffff
		if len(data) < size:
			yield None, None, data
			return
		argdata = data[8:size]
		yield oid, op, argdata
		data = data[size:]
	yield None, None, data

ENDIAN_MAGIC = 0x01020304
IS_CLIENT, IS_SERVER = range(2)

magic = sys.stdin.buffer.read(4)
for conv in ('<', '>'):
	val = struct.unpack(f'{conv}I', magic)[0]
	if val == ENDIAN_MAGIC:
		break
else:
	log_error("File does not start with magic")
	sys.exit(1)

config = sys.stdin.buffer.read(4)
disk_format, SIZE_SHIFT = struct.unpack(f'{conv}HH', config)
if disk_format != 1:
	log_error(f"No idea how to handle on disk format {disk_format}")
	sys.exit(1)
SOURCE_MASK = (1 << SIZE_SHIFT) - 1

last_source = None
leftover = dict()
while True:
	size_src = sys.stdin.buffer.read(4)
	if not size_src:
		log_debug("Got empty read")
		break

	size_src = struct.unpack(f'{conv}I', size_src)[0]
	source = size_src & SOURCE_MASK
	size = size_src >> SIZE_SHIFT
	if source & IS_SERVER:
		src_name = 'Server'
		src_action = 'event'
	else:
		src_name = 'Client'
		src_action = 'request'
	src_name += f'-{source >> 1}'

	if not size:
		if source in leftover:
			del leftover[source]
		log_info(f"[{src_name}] disconnected")
		last_source = None
		continue

	data = sys.stdin.buffer.read(size)
	if not data:
		log_debug("Got empty read")
		break

	if source not in leftover:
		log_info(f"[{src_name}] connected")
		last_source = source
		leftover[source] = b''

	data = leftover[source] + data
	for oid, op_or_ev, argdata in wayland_parse(data, conv):
		if oid is None:
			leftover[source] = argdata
			break
		if source != last_source and sys.stdout.isatty():
			log_info(f"[{src_name}]")
			last_source = source
		log_info(f"{src_name if not sys.stdout.isatty() else ''}  oid {oid:10d} {src_action:>7s} {op_or_ev:2d} args {argdata}")

log_debug("Bye from parser")
