import struct

from python_wayland.wayland import protocol as wayland
from python_wayland.wayland.protocol import DuplicateInterfaceName

class WaylandInterface(wayland.Interface):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.requests_by_name = self.requests;
		self.requests_by_number = list()
		for item in self.requests_by_name.values():
			self.requests_by_number.append(item)

class Arg_new_id(wayland.Arg_new_id):
	def __init__(self, parent, arg):
		wayland.Arg.__init__(self, parent, arg)
		self.interface = arg.get('interface', None)
		if isinstance(parent, wayland.Event):
			assert self.interface
			parent.creates = self.interface

	def unmarshal(self, argdata, fd_source):
		if self.interface:
			# interface specified in xml
			return struct.unpack('I', argdata.read(4))[0]
		# interface specified by caller
		interface = wayland.Arg_string.unmarshal(None, argdata, fd_source)
		version, new_id = struct.unpack('II', argdata.read(8))
		return interface, version, new_id

class Arg_object(wayland.Arg_object):
	def unmarshal(self, argdata, fd_source):
		oid = struct.unpack('I', argdata.read(4))[0]
		return oid


class Entry(wayland.Entry):
	def __init__(self, enum, entry):
		val = entry.get('value')
		args = val.split()
		if len(args) == 3:
			ops = {
				'<<': '__lshift__',
				'>>': '__rshift__',
				 '&': '__and__',
				 '|': '__or__'
			}
			conv = ops.get(args[1])
			func = getattr(int, conv)
			if func:
				calc_val = func(int(args[0], base=0), int(args[2], base=0))
				entry.set('value', str(calc_val))
		super().__init__(enum, entry)

wayland.Arg_new_id = Arg_new_id
wayland.Arg_object = Arg_object
wayland.Entry = Entry
wayland.Interface = WaylandInterface

class WaylandProtocol(wayland.Protocol):
	pass

if __name__ == '__main__':
	wp_base = wayland.Protocol("/usr/share/wayland/wayland.xml")
	print(wp_base)
	for interface in wp_base.interfaces.values():
		print(interface.requests)
