#!/usr/bin/env -S python3 -u

"""
	Usage: wayland_proxy.py <executable> [arg1] [arg2]..

	wayland_proxy.py creates a new unix socket and points WAYLAND_DISPLAY to it
	before executing <executable> as subprocess. The subprocess will then connect to
	this socket instead of the original wayland socket. Once a client connects to the
	local socket we connect to the real wayland socket and relay data and fds both ways.
	All data (no fds though) is additionally sent to stdout where it can either be
	dumped into a file or directly piped into a parser.

	At the beginning the magic number 0x01020304 is sent as uint32_t so the parser
	can figure out endianess in case of parsing a dump created on another system.

	The second thing sent are two uint16_t containing disk_format (only version 1
	exists yet) and size_shift (which is derived from MAX_PROXY_CONNECTIONS as used
	by the proxy).

	The further output format consists of a single uint32_t containing size of following
	data, connection_id and if the data came from the server or client of that connection.
	If size is 0, given connection_id + client/server identifier disconnected.

	By default wayland_proxy.py supports up to 131072 proxy connections during it's
	*whole lifetime* to not confuse parsers (and humans) by reusing connection ids.
	By default wayland_proxy.py will stop accepting new connections on its socket
	once the proxy connection limit is reached. This may be changed by setting
	REUSE_CONNECTION_IDS = True.

	If the subprocess starts further wayland clients, has dedicated wayland connections
	or reconnectes rapidly the proxy connection limit might be hit eventually.

	Parsing can be done something like

		data = sys.stdin.buffer.read(4)
		for conv in ('<', '>'):
			val = struct.unpack(f'{conv}I', data)[0]
			if val == 0x01020304:
				break
		else:
			raise RuntimeError("Magic endianess marker not found")

		data = sys.stdin.buffer.read(4)
		disk_format, size_shift = struct.unpack(f'{conv}HH', data)
		if disk_format != 1:
			raise RuntimeError(f"No idea how to handle on disk format {disk_format}")
		source_mask = (1 << size_shift) - 1

		leftover = dict()
		while True:
			size_src = struct.unpack(f'{conv}I', sys.stdin.buffer.read(4))[0]
			if not size_src:
				break
			size = size_src >> size_shift
			source = size_src & source_mask
			connection_id = source >> 1
			src_is_server = source & 1
			if not size:
				if source in leftover:
					del leftover[source]
				continue
			data = sys.stdin.buffer.read(size)
			if not data:
				break
			if source not in leftover:
				leftover[source] = b''
			data = leftover[source] + data
			leftover[source] = parse_wayland_data(data, conv)

		For a more complete example see wayland_proxy_parser_basic.py

	All log messages and stdout + stderr of the subprocess are redirected to stderr
	to not be mixed with the output of the parser. In case of live parsing just
	redirect stderr of wayland_proxy.py to /dev/null or some file.

	I quickly hacked this together to aid in debugging wayland protocol
	implementations but a proxy like this could also be used for injecting new
	protocols into clients without the need to deep dive into frameworks like
	QT or GTK (or rely on them not to change/remove private APIs) or to act as a
	firewall for untrusted clients when run using a different user id and strong
	permission checks for connecting clients.
	It could also be used for translating between different variations of the
	same protocol, e.g. from zwlr_foreign_toplevel to (z)ext_foreign_toplevel.


	Advanced:
	---------

	Log protocol binary format default config:

		includes conn_server if used for shifting:
		conn_max       2**17       18 bits


		size_max       2**(32-conn_max)-1    2**14 - 1    14 bits
		conn_max_id    conn_max - 1          2**17 - 1    17 bits
		conn_server                          2**0          1 bit
		----------------------------------------------------------
		                                                  32 bits

	This is not a fixed limit but instead configured by setting MAX_PROXY_CONNECTIONS
	(conn_max in table above) to 2**x where x is <= 17 to leave 14 bits available for
	size and 1 bit for client/server identifier. The setting will be clamped down to
	the nearest 2**x.

	If you want to use more than 131072 connection ids increase MAX_PROXY_CONNECTIONS.
	As the setting will be written into the output dump all conforming parsers will
	just work with the new setting as they calculate the bitshifts based on that value.
	You will need to make sure that the current MAX_RELAY_SIZE setting will fit into
	the remaining bits.

	You can also increase MAX_RELAY_SIZE (how many bytes we try to read/send at once
	from/to a socket). Setting this to a large number may increase latency if there
	is constant and fast traffic between a different server-client proxy connection.
	Do not set this above 16383 ((2**14) - 1) without also decreasing MAX_PROXY_CONNECTIONS.

"""

MAX_RELAY_SIZE = 2048           # 2 ** 11
MAX_PROXY_CONNECTIONS = 131072  # 2 ** 17
REUSE_CONNECTION_IDS = False

import os
import sys
import array
import socket
import struct
import shutil
import traceback
from math import log2
from subprocess import Popen
from select import poll, POLLIN, POLLPRI

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

LOG_LEVEL_MIN = LOG_LEVEL_WARNING

IS_CLIENT, IS_SERVER = range(2)
ENDIAN_MAGIC = 0x01020304
DISK_FORMAT = 1
MAX_PROXY_CONNECTIONS = 2 ** int(log2(MAX_PROXY_CONNECTIONS))

def _log(loglevel, msg):
	if loglevel < LOG_LEVEL_MIN:
		return
	fmt = "\x1b[{}m[WaylandProxy] {}\x1b[m"
	print(fmt.format(LOG_COLORS.get(loglevel, 32), msg), file=sys.stderr)

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

def msg_receive(connection):
	fds = array.array('i')
	data, ancdata, msg_flags, address = connection.recvmsg(
		MAX_RELAY_SIZE, socket.CMSG_SPACE(16 * fds.itemsize)
	)
	for cmsg_level, cmsg_type, cmsg_data in ancdata:
		if (
			cmsg_level == socket.SOL_SOCKET and
			cmsg_type == socket.SCM_RIGHTS
		):
			fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
	return data, fds

def msg_send(data, fds, connection):
	connection.sendmsg([data], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])

SIZE_LEFT_SHIFT = int(log2(MAX_PROXY_CONNECTIONS * 2))
if __name__ == '__main__':
	xdg_runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
	if not xdg_runtime_dir:
		log_warn("XDG_RUNTIME_DIR not set")
		sys.exit(1)
	wayland_display = os.environ.get('WAYLAND_DISPLAY')
	if not wayland_display:
		log_warn("WAYLAND_DISPLAY not set")
		sys.exit(1)
	wayland_server_addr = os.path.join(xdg_runtime_dir, wayland_display)
	log_debug(f"Should connect to {wayland_server_addr}")

	wayland_proxy_addr = 'wayland-proxy-0'
	os.environ['WAYLAND_DISPLAY'] = wayland_proxy_addr
	wayland_proxy_addr = os.path.join(xdg_runtime_dir, wayland_proxy_addr)

	if len(sys.argv) < 2:
		sys.stderr.write(__doc__)
		sys.exit(2)

	proc = shutil.which(sys.argv[1], mode=os.F_OK)
	if not proc:
		sys.stderr.write(__doc__)
		log_error(f"'{sys.argv[1]}' not found")
		sys.exit(2)
	elif not os.access(proc, os.X_OK):
		sys.stderr.write(__doc__)
		log_error(f"'{sys.argv[1]}' exists but is not executable")
		sys.exit(2)
	sys.argv[1] = proc

	child_proc = None
	proxy_connections = dict()
	if REUSE_CONNECTION_IDS:
		connection_ids_active = set()
	try:
		poll = poll()

		wayland_proxy_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
		wayland_proxy_socket.bind(wayland_proxy_addr)
		wayland_proxy_socket.listen()
		poll.register(wayland_proxy_socket, POLLIN | POLLPRI)

		log_debug(f"Starting subprocess {' '.join(sys.argv[1:])}")
		try:
			child_proc = Popen(sys.argv[1:], bufsize=1, stdout=sys.stderr, stderr=sys.stderr)
		except FileNotFoundError as e:
			log_error(f"Failed to start {' '.join(sys.argv[1:])}: {e}")
			exit_status = 2
			raise
		log_info(f"Started subprocess with pid {child_proc.pid}")

		pid_fd = None
		pidfd_open = getattr(os, 'pidfd_open')
		if pidfd_open:
			pid_fd = pidfd_open(child_proc.pid)
			poll.register(pid_fd, POLLIN)

		# Send magic for the parser to detect endianess
		sys.stdout.buffer.write(struct.pack('=I', ENDIAN_MAGIC))

		# Send on disk format config
		sys.stdout.buffer.write(struct.pack('=HH', DISK_FORMAT, SIZE_LEFT_SHIFT))

		global_connection_id = 0
		# Start relaying stuff
		while True:
			for fd, events in poll.poll():
				if fd == pid_fd:
					# Subprocess died
					log_info("Subprocess died")
					log_debug("Subprocess starts to think about human meat")
					poll.unregister(fd)
					os.close(fd)
					if len(proxy_connections) == 0:
						poll.unregister(wayland_proxy_socket)
						wayland_proxy_socket.close()
						break
					continue
				elif fd == wayland_proxy_socket.fileno():
					if global_connection_id == MAX_PROXY_CONNECTIONS:
						log_debug("Ignoring late event for proxy socket")
						continue

					# Accept new proxy client
					wayland_client_connection, wayland_client_addr = wayland_proxy_socket.accept()
					log_info(f"Client-{global_connection_id} connected to proxy socket: {wayland_client_addr}")

					# Connect to wayland server
					wayland_server_connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
					try:
						wayland_server_connection.connect(wayland_server_addr)
					except FileNotFoundError as e:
						log_error(f"Server-{global_connection_id} failed to connect to wayland server socket {wayland_server_addr}")
						raise

					connection_id = global_connection_id
					global_connection_id += 1

					proxy_connections[wayland_client_connection.fileno()] = (IS_CLIENT, connection_id, wayland_server_connection)
					proxy_connections[wayland_server_connection.fileno()] = (IS_SERVER, connection_id, wayland_client_connection)
					poll.register(wayland_client_connection, POLLIN | POLLPRI)
					poll.register(wayland_server_connection, POLLIN | POLLPRI)

					if REUSE_CONNECTION_IDS:
						connection_ids_active.add(connection_id)
						log_debug(f"Current active connections {len(connection_ids_active)}/{MAX_PROXY_CONNECTIONS}")
						if len(connection_ids_active) == MAX_PROXY_CONNECTIONS:
							global_connection_id = MAX_PROXY_CONNECTIONS
							# TODO: eventually reopen wayland_proxy_socket on disconnect
						else:
							global_connection_id %= MAX_PROXY_CONNECTIONS
							while global_connection_id in connection_ids_active:
								global_connection_id += 1
								global_connection_id %= MAX_PROXY_CONNECTIONS
							log_debug(f"Using {global_connection_id} as next connection id")

					if global_connection_id == MAX_PROXY_CONNECTIONS:
						log_warn("Out of connections. Closing proxy socket.")
						poll.unregister(wayland_proxy_socket)
						wayland_proxy_socket.close()

					continue

				remote = proxy_connections.get(fd, None)
				if remote is None:
					log_error(f"Got random event from poll for fd {fd}")
					continue

				local_kind, connection_id, remote_socket = remote
				_, _, local_socket = proxy_connections[remote_socket.fileno()]

				data, fds = msg_receive(local_socket)
				if not data:
					del proxy_connections[local_socket.fileno()]
					del proxy_connections[remote_socket.fileno()]

					for sock, kind in (
						(local_socket, local_kind),
						(remote_socket, IS_CLIENT if local_kind == IS_SERVER else IS_SERVER)
					):
						poll.unregister(sock)
						sock.close()
						who = 'Server' if kind == IS_SERVER else 'Client'
						log_info(f"{who}-{connection_id} disconnected")

						sys.stdout.buffer.write(
							struct.pack('=I', (0 << SIZE_LEFT_SHIFT) | (connection_id << 1) | kind)
						)

					if REUSE_CONNECTION_IDS:
						connection_ids_active.remove(connection_id)

					if  len(proxy_connections) == 0:
						log_info("Last proxy client disconnected")
						break
					else:
						log_debug(f"Still {len(proxy_connections) // 2} connections alive")
						continue

				msg_send(data, fds, remote_socket)
				if fds:
					log_debug(f"Relayed {len(fds)} fd{'s' if len(fds) > 1 else ''}: {', '.join(str(x) for x in fds)}")
					for fd in fds:
						log_debug(f"  closing fd {fd}")
						os.close(fd)

				sys.stdout.buffer.write(
					struct.pack('=I', (len(data) << SIZE_LEFT_SHIFT) | (connection_id << 1) | local_kind) + data
				)
				log_debug(f"[{connection_id}] Server -> Client {len(data):4d} bytes and {len(fds)} fds")
			else:
				continue
			# we had a break before
			break
	except Exception as e:
		log_error(f"Got unhandled exception: {type(e).__name__}: {e}")
		err = traceback.format_exc()
		for line in err.split('\n'):
			log_error(line)
	finally:
		log_debug("Cleaning up")
		sys.stdout.buffer.flush()
		os.unlink(wayland_proxy_addr)
		if child_proc is not None:
			log_debug("Creating zombies")
			child_proc.terminate()

			log_debug("Shooting zombies")
			try:
				exit_status = child_proc.wait(2)
			except TimeoutExpired:
				log_debug("They are too fast. Lets get onto a tree and sniper them.")
				child_proc.kill()
				try:
					exit_status = child_proc.wait(2)
				except TimeoutExpired:
					log_debug("Daym. They know how to climb.")

			if exit_status != 0:
				log_warn(f"Subprocess died with exit status {exit_status}")
		sys.stderr.flush()
		sys.exit(exit_status)
