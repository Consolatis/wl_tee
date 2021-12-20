#!/usr/bin/env -S python3 -u

"""
	Usage: wayland_proxy_parse_xml.py [regex_filter] [regex_ignore] < wayland_proxy.dump

	All arguments are optional. If called without arguments everything is logged.

	To do some live debugging use something like
		./wayland_proxy.py some_app with_some args 2>/dev/null | ./wayland_proxy_parse_xml.py

	To only debug wlr_foreign_toplevel and wlr_layer_shell you could use something like
		./wayland_proxy_parse_xml.py 'foreign_toplevel|layer_(shell|surface)'

	And to debug all non base protocols do something like
		./wayland_proxy_parse_xml.py '' ' (wl_|xdg_)'
		(pay attention to the space in front of the ignore so it doesn't match zwl_, zxdg_, ..)
"""

import os
import re
import sys
import struct
from io import BytesIO

from wayland_protocol import (
	WaylandProtocol,
	DuplicateInterfaceName
)

(
	LOG_LEVEL_DEBUG,
	LOG_LEVEL_INFO,
	LOG_LEVEL_WARNING,
	LOG_LEVEL_ERROR
) = range(4)

LOG_LEVEL_MIN = LOG_LEVEL_INFO

LOG_COLORS = {
	LOG_LEVEL_DEBUG: 36,
	LOG_LEVEL_INFO: 37,
	LOG_LEVEL_WARNING: 33,
	LOG_LEVEL_ERROR: 31,
}

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

class NewObj:
	def __init__(self, args):
		if isinstance(args, tuple):
			self.interface, self.version, self.oid = args
		else:
			self.interface = None
			self.version = None
			self.oid = args

	def __str__(self):
		if self.interface:
			return f"<new_obj id {self.oid} [{self.interface} v{self.version}]>"
		return f"<new_obj id {self.oid}>"

class UnknownOpOrEvent:
	def __init__(self, item):
		self.name = str(item)
	def __str__(self):
		return self.name
	def __repr__(self):
		return self.name

class _RawReturn:
	def __getitem__(self, item):
		return UnknownOpOrEvent(item)

raw_return = _RawReturn()

class UnknownInterface:
	def __init__(self, oid=None, name=None, version=0):
		if name is not None:
			self.name = name
		elif oid is not None:
			self.name = str(oid)
		self.version = version
		self.requests_by_name = raw_return
		self.requests_by_number = raw_return
		self.events_by_name = raw_return
		self.events_by_number = raw_return
	def __str__(self):
		return self.name

class InterfaceInstance:
	def __init__(self, oid, interface, version=None):
		self.oid = oid
		self.interface = interface
		if version is None:
			self.version = interface.version
		else:
			self.version = version

	def __getattr__(self, key):
		return getattr(self.interface, key)

	def __str__(self):
		if self.oid == 0:
			return f"<obj NULL>"
		return f"<obj id {self.oid} [{self.interface} v{self.version}]>"

class LookUps:
	def __init__(self):
		self.interfaces = dict()
		self.globals = dict()
		self.objects = dict()

	def add_global(self, global_id, interface_name, interface_version):
		interface = self.interfaces.get(interface_name)
		if interface is None:
			interface = UnknownInterface(name=interface_name)
			self.interfaces[interface_name] = interface
		interface.version = interface_version
		self.globals[global_id] = interface
		log_debug(f"Adding interface {interface} {repr(interface)} to globals")

	def get_global(self, global_id):
		return self.globals.get(global_id)

	def add_object(self, oid, interface, version=None):
		log_debug(f"Creating instance of {interface} with oid {oid}")
		self.objects[oid] = InterfaceInstance(oid, interface, version)

	def remove_object(self, oid):
		del self.objects[oid]

	def get_object(self, oid):
		object = self.objects.get(oid)
		if object is None:
			object = InterfaceInstance(oid, UnknownInterface(oid=oid))
			self.objects[oid] = object
		return object

def init_lookups():
	lookups = LookUps()
	for protocol_path in (
		'protocols/wayland/protocol',
		'protocols/wayland-protocols',
		'protocols/wlr-protocols',
		'protocols/plasma-wayland-protocols'
	):
		for root, dirs, files in os.walk(protocol_path):
			for file in files:
				if file.endswith('.xml'):
					log_debug(f"Parsing {os.path.join(root, file)}")
					try:
						WaylandProtocol(os.path.join(root, file), parent=lookups)
					except DuplicateInterfaceName as e:
						# FIXME: use tmp parent and in case like this don't merge with real parent
						log_debug(f"Duplicate interface found in {file}: {e}")

	lookups.add_object(0, UnknownInterface(0, "NULL", 0))
	lookups.add_object(1, lookups.interfaces['wl_display'])
	return lookups

def wayland_parse(data, conv):
	while len(data) >= 8:
		oid, sizeop = struct.unpack(f'{conv}II', data[:8])
		# Read II instead of IHH because wayland seems
		# to always write 4 bytes at once and thus
		# args could be switched on endian differences.
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

if len(sys.argv) > 1:
	re_filter = re.compile(sys.argv[1])
else:
	re_filter = None

if len(sys.argv) > 2:
	re_ignore = re.compile(sys.argv[2])
else:
	re_ignore = None

connections = dict()
last_source = None
leftover = dict()
while True:
	size_src = sys.stdin.buffer.read(4)
	if not size_src:
		log_debug("Got empty read")
		break

	size_src = struct.unpack(f'{conv}I', size_src)[0]
	source = size_src & SOURCE_MASK
	connection_id = source >> 1
	size = size_src >> SIZE_SHIFT
	if source & IS_SERVER:
		src_name = 'Server'
		src_action = 'event'
	else:
		src_name = 'Client'
		src_action = 'request'
	src_name += f'-{connection_id}'

	if not size:
		if source in leftover:
			del leftover[source]
		if connection_id in connections:
			del connections[connection_id]
		log_info(f"[{src_name}] disconnected")
		last_source = None
		continue

	if connection_id not in connections:
		connections[connection_id] = init_lookups()
	lookups = connections[connection_id]

	data = sys.stdin.buffer.read(size)
	if len(data) == 0:
		log_debug("Got empty read")
		break

	if source not in leftover:
		log_info(f"[{src_name}] connected")
		leftover[source] = b''
		last_source = source

	data = leftover[source] + data
	for oid, op_or_ev, argdata in wayland_parse(data, conv):
		if oid is None:
			leftover[source] = argdata
			break
		log_debug(f"  oid {oid:10d} {src_action:>7s} {op_or_ev:2d} args {argdata}")
		obj = lookups.get_object(oid)
		if source & IS_SERVER:
			op_or_ev_by_number = obj.events_by_number
		else:
			op_or_ev_by_number = obj.requests_by_number
		op_or_event = op_or_ev_by_number[op_or_ev]

		args = list()
		args_plain = list()
		new_obj = None
		if isinstance(op_or_event, UnknownOpOrEvent):
			log_debug(f"Unknown {src_action}")
			args_plain.append(argdata)
		else:
			argdata_stream = BytesIO(argdata)
			args = op_or_event.args.copy()
			for arg in args:
				log_debug(f"Got arg {arg} with name {arg.__class__.__name__}")
				try:
					arg_plain = arg.unmarshal(argdata_stream, list(range(5)))
					log_debug(f"Got arg plain {arg_plain}")
					if arg.__class__.__name__ == 'Arg_new_id':
						new_obj = NewObj(arg_plain)
						args_plain.append(new_obj)
					elif arg.__class__.__name__ == 'Arg_object':
						args_plain.append(lookups.get_object(arg_plain))
					else:
						args_plain.append(arg_plain)
				except RuntimeError:
					log_warn(f"Can't unmarshal arg type {arg.__class__.__name__}")
					args_plain.append(arg)

			if obj.name == 'wl_registry':
				if op_or_event.name == 'global':
					global_id, interface, version = args_plain
					lookups.add_global(global_id, interface, version)
				elif op_or_event.name == 'bind':
					log_debug("Detected wl_registry.bind() event")
					global_id, new_obj = args_plain
					op_or_event.creates = new_obj.interface
			elif obj.name == 'wl_display':
				if op_or_event.name == 'delete_id':
					log_debug(f"Deleting object with id {args_plain[0]}")
					delete_oid = args_plain[0]
					args_plain[0] = lookups.get_object(delete_oid)
					lookups.remove_object(delete_oid)

		creates = getattr(op_or_event, 'creates', None)
		if creates is not None:
			log_debug(f"This request will create a new object based on interface {creates}")
			if new_obj is not None:
				interface = lookups.interfaces.get(creates)
				if not new_obj.interface:
					new_obj.interface = interface
					new_obj.version = interface.version
				lookups.add_object(new_obj.oid, interface, new_obj.version)
				log_debug(f"New object is of type {lookups.get_object(new_obj.oid)}")

		line = "{}  {:^10d} {}.{}({})".format(
			src_name if not sys.stdout.isatty() else '',
			oid, obj.name, op_or_event.name,
			", ".join(
				(f"'{x}'" if isinstance(x, str) and not x.startswith('<oid ') else str(x))
				for x in args_plain
			)
		)
		if not re_filter or (
			re_filter.search(line) and not (
				re_ignore and re_ignore.search(line)
			)
		):
			if source != last_source and sys.stdout.isatty():
				log_info(f"[{src_name}]")
				last_source = source
			log_info(line)


log_debug("Bye from parser")
