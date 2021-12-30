#### About
wl_tee provides a small framework for debugging Wayland applications.

#### Executables
* [wayland_proxy.py](wayland_proxy.py)  
Spawns a new process given as argument and proxies all Wayland traffic.  
The traffic is additionally written to stdout where it can be redirected into a file or piped directly into a parser.

* [wayland_proxy_parser_basic.py](wayland_proxy_parser_basic.py)  
Reads Wayland traffic from stdin and writes oid, opcode/event and argdata to stdout.

* [wayland_proxy_parser_xml.py](wayland_proxy_parser_xml.py)  
Additionally translates oid, opcode/event and argdata based on {wayland,wlroots,plasma} protocol XML files.  
Unknown protocols will be shown like interface.1(b'binary_data') or 23.5(b'binary_data').  
Provides regex filter to log specific events only.

* [wl_debug.sh](wl_debug.sh)  
A convinient wrapper for live debugging and parsing of Wayland protocol data.  

#### Thanks
Thanks a bunch [@sde1000](https://github.com/sde1000) for writing [python-wayland](https://github.com/sde1000/python-wayland) which gave a lot of inspiration and a quick codified overview of the Wayland protocol itself.

#### Dependencies for wayland_proxy_parser_xml.py
* [python-wayland](https://github.com/sde1000/python-wayland)
* [wayland](https://gitlab.freedesktop.org/wayland/wayland.git/) (Protocol XML files only)
* [wayland-protocols](https://gitlab.freedesktop.org/wayland/wayland-protocols.git/) (Protocol XML files only)
* [wlr-protocols](https://gitlab.freedesktop.org/wlroots/wlr-protocols.git/) (Protocol XML files only)
* [plasma-wayland-protocols](https://github.com/KDE/plasma-wayland-protocols.git) (Protocol XML files only)

#### Dependencies for everything else
* Python 3

#### Cloning
All dependencies are defined as submodules:
```
git clone --recurse-submodules https://github.com/Consolatis/wl_tee
git pull --recurse-submodules https://github.com/Consolatis/wl_tee
```

#### Usage
```
$ ./wl_debug.sh some_wayland_application --with_some args
$ WL_DEBUG_FILTER="layer_(shell|surface)" ./wl_debug.sh some_wayland_application
$ WL_DEBUG_IGNORE=" (wl_|xdg_)" ./wl_debug.sh some_wayland_application
```

#### Example session
(wl_debug.sh linked to ~/.local/bin/wl_debug)
```
$ wl_debug ./tasklist.py 2>/dev/null
[Client-0] connected
      1      wl_display.get_registry(<new_obj id 2 [wl_registry v1]>)
[Server-0] connected
      2      wl_registry.global(1, 'wl_shm', 1)
      2      wl_registry.global(2, 'wl_compositor', 4)
      2      wl_registry.global(3, 'wl_subcompositor', 1)
      2      wl_registry.global(4, 'wl_data_device_manager', 3)
      2      wl_registry.global(5, 'zwlr_gamma_control_manager_v1', 1)
      2      wl_registry.global(6, 'zxdg_output_manager_v1', 3)
      2      wl_registry.global(7, 'org_kde_kwin_idle', 1)
      2      wl_registry.global(8, 'zwp_idle_inhibit_manager_v1', 1)
      2      wl_registry.global(9, 'zwlr_layer_shell_v1', 4)
      2      wl_registry.global(10, 'xdg_wm_base', 2)
      2      wl_registry.global(11, 'zwp_tablet_manager_v2', 1)
      2      wl_registry.global(12, 'org_kde_kwin_server_decoration_manager', 1)
      2      wl_registry.global(13, 'zxdg_decoration_manager_v1', 1)
      2      wl_registry.global(14, 'zwp_relative_pointer_manager_v1', 1)
      2      wl_registry.global(15, 'zwp_pointer_constraints_v1', 1)
      2      wl_registry.global(16, 'wp_presentation', 1)
      2      wl_registry.global(17, 'zwlr_output_manager_v1', 2)
      2      wl_registry.global(18, 'zwlr_output_power_manager_v1', 1)
      2      wl_registry.global(19, 'zwp_input_method_manager_v2', 1)
      2      wl_registry.global(20, 'zwp_text_input_manager_v3', 1)
      2      wl_registry.global(21, 'zwlr_foreign_toplevel_manager_v1', 3)
      2      wl_registry.global(22, 'zwlr_export_dmabuf_manager_v1', 1)
      2      wl_registry.global(23, 'zwlr_screencopy_manager_v1', 3)
      2      wl_registry.global(24, 'zwlr_data_control_manager_v1', 2)
      2      wl_registry.global(25, 'zwp_primary_selection_device_manager_v1', 1)
      2      wl_registry.global(26, 'wp_viewporter', 1)
      2      wl_registry.global(27, 'zxdg_exporter_v1', 1)
      2      wl_registry.global(28, 'zxdg_importer_v1', 1)
      2      wl_registry.global(29, 'zxdg_exporter_v2', 1)
      2      wl_registry.global(30, 'zxdg_importer_v2', 1)
      2      wl_registry.global(31, 'xdg_activation_v1', 1)
      2      wl_registry.global(32, 'zwp_virtual_keyboard_manager_v1', 1)
      2      wl_registry.global(33, 'zwlr_virtual_pointer_manager_v1', 2)
      2      wl_registry.global(34, 'zwlr_input_inhibit_manager_v1', 1)
      2      wl_registry.global(35, 'zwp_keyboard_shortcuts_inhibit_manager_v1', 1)
      2      wl_registry.global(36, 'wl_seat', 7)
      2      wl_registry.global(37, 'zwp_pointer_gestures_v1', 3)
      2      wl_registry.global(38, 'wl_output', 3)
[Client-0]
      2      wl_registry.bind(21, <new_obj id 3 [zwlr_foreign_toplevel_manager_v1 v3]>)
[Server-0]
      3      zwlr_foreign_toplevel_manager_v1.toplevel(<new_obj id 4278190080 [zwlr_foreign_toplevel_handle_v1 v3]>)
  4278190080 zwlr_foreign_toplevel_handle_v1.title('foot')
  4278190080 zwlr_foreign_toplevel_handle_v1.app_id('foot')
  4278190080 zwlr_foreign_toplevel_handle_v1.state(b'\x02\x00\x00\x00')
  4278190080 zwlr_foreign_toplevel_handle_v1.parent(<obj NULL>)
  4278190080 zwlr_foreign_toplevel_handle_v1.done()
[Client-0]
      2      wl_registry.bind(36, <new_obj id 4 [wl_seat v7]>)
      2      wl_registry.bind(38, <new_obj id 5 [wl_output v3]>)
[Server-0]
      4      wl_seat.name('seat0')
      4      wl_seat.capabilities(7)
      5      wl_output.geometry(0, 0, 0, 0, 0, 'The X.Org Foundation', '11.0', 0)
      5      wl_output.mode(1, 1024, 768, 0)
      5      wl_output.scale(1)
      5      wl_output.done()
^C
```

Same for wayland_proxy_parser_basic.py (Doesn't requires any dependencies other than a Python 3 interpreter):
```
$ ./wayland_proxy.py tasklist 2>/dev/null | ./wayland_proxy_parser_basic.py
[Client-0] connected
  oid          1 request  1 args b'\x02\x00\x00\x00'
[Server-0] connected
  oid          2   event  0 args b'\x01\x00\x00\x00\x07\x00\x00\x00wl_shm\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x02\x00\x00\x00\x0e\x00\x00\x00wl_compositor\x00\x00\x00\x04\x00\x00\x00'
  oid          2   event  0 args b'\x03\x00\x00\x00\x11\x00\x00\x00wl_subcompositor\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x04\x00\x00\x00\x17\x00\x00\x00wl_data_device_manager\x00\x00\x03\x00\x00\x00'
  oid          2   event  0 args b'\x05\x00\x00\x00\x1e\x00\x00\x00zwlr_gamma_control_manager_v1\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x06\x00\x00\x00\x17\x00\x00\x00zxdg_output_manager_v1\x00\x00\x03\x00\x00\x00'
  oid          2   event  0 args b'\x07\x00\x00\x00\x12\x00\x00\x00org_kde_kwin_idle\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x08\x00\x00\x00\x1c\x00\x00\x00zwp_idle_inhibit_manager_v1\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\t\x00\x00\x00\x14\x00\x00\x00zwlr_layer_shell_v1\x00\x04\x00\x00\x00'
  oid          2   event  0 args b'\n\x00\x00\x00\x0c\x00\x00\x00xdg_wm_base\x00\x02\x00\x00\x00'
  oid          2   event  0 args b'\x0b\x00\x00\x00\x16\x00\x00\x00zwp_tablet_manager_v2\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b"\x0c\x00\x00\x00'\x00\x00\x00org_kde_kwin_server_decoration_manager\x00\x00\x01\x00\x00\x00"
  oid          2   event  0 args b'\r\x00\x00\x00\x1b\x00\x00\x00zxdg_decoration_manager_v1\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x0e\x00\x00\x00 \x00\x00\x00zwp_relative_pointer_manager_v1\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x0f\x00\x00\x00\x1b\x00\x00\x00zwp_pointer_constraints_v1\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x10\x00\x00\x00\x10\x00\x00\x00wp_presentation\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x11\x00\x00\x00\x17\x00\x00\x00zwlr_output_manager_v1\x00\x00\x02\x00\x00\x00'
  oid          2   event  0 args b'\x12\x00\x00\x00\x1d\x00\x00\x00zwlr_output_power_manager_v1\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x13\x00\x00\x00\x1c\x00\x00\x00zwp_input_method_manager_v2\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x14\x00\x00\x00\x1a\x00\x00\x00zwp_text_input_manager_v3\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x15\x00\x00\x00!\x00\x00\x00zwlr_foreign_toplevel_manager_v1\x00\x00\x00\x00\x03\x00\x00\x00'
  oid          2   event  0 args b'\x16\x00\x00\x00\x1e\x00\x00\x00zwlr_export_dmabuf_manager_v1\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x17\x00\x00\x00\x1b\x00\x00\x00zwlr_screencopy_manager_v1\x00\x00\x03\x00\x00\x00'
  oid          2   event  0 args b'\x18\x00\x00\x00\x1d\x00\x00\x00zwlr_data_control_manager_v1\x00\x00\x00\x00\x02\x00\x00\x00'
  oid          2   event  0 args b'\x19\x00\x00\x00(\x00\x00\x00zwp_primary_selection_device_manager_v1\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1a\x00\x00\x00\x0e\x00\x00\x00wp_viewporter\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1b\x00\x00\x00\x11\x00\x00\x00zxdg_exporter_v1\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1c\x00\x00\x00\x11\x00\x00\x00zxdg_importer_v1\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1d\x00\x00\x00\x11\x00\x00\x00zxdg_exporter_v2\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1e\x00\x00\x00\x11\x00\x00\x00zxdg_importer_v2\x00\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'\x1f\x00\x00\x00\x12\x00\x00\x00xdg_activation_v1\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b' \x00\x00\x00 \x00\x00\x00zwp_virtual_keyboard_manager_v1\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'!\x00\x00\x00 \x00\x00\x00zwlr_virtual_pointer_manager_v1\x00\x02\x00\x00\x00'
  oid          2   event  0 args b'"\x00\x00\x00\x1e\x00\x00\x00zwlr_input_inhibit_manager_v1\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'#\x00\x00\x00*\x00\x00\x00zwp_keyboard_shortcuts_inhibit_manager_v1\x00\x00\x00\x01\x00\x00\x00'
  oid          2   event  0 args b'$\x00\x00\x00\x08\x00\x00\x00wl_seat\x00\x07\x00\x00\x00'
  oid          2   event  0 args b'%\x00\x00\x00\x18\x00\x00\x00zwp_pointer_gestures_v1\x00\x03\x00\x00\x00'
  oid          2   event  0 args b'&\x00\x00\x00\n\x00\x00\x00wl_output\x00\x00\x00\x03\x00\x00\x00'
[Client-0]
  oid          2 request  0 args b'\x15\x00\x00\x00!\x00\x00\x00zwlr_foreign_toplevel_manager_v1\x00\x00\x00\x00\x03\x00\x00\x00\x03\x00\x00\x00'
[Server-0]
  oid          3   event  0 args b'\x00\x00\x00\xff'
  oid 4278190080   event  0 args b'\x05\x00\x00\x00foot\x00\x00\x00\x00'
  oid 4278190080   event  1 args b'\x05\x00\x00\x00foot\x00\x00\x00\x00'
  oid 4278190080   event  4 args b'\x04\x00\x00\x00\x02\x00\x00\x00'
  oid 4278190080   event  7 args b'\x00\x00\x00\x00'
  oid 4278190080   event  5 args b''
[Client-0]
  oid          2 request  0 args b'$\x00\x00\x00\x08\x00\x00\x00wl_seat\x00\x07\x00\x00\x00\x04\x00\x00\x00'
  oid          2 request  0 args b'&\x00\x00\x00\n\x00\x00\x00wl_output\x00\x00\x00\x03\x00\x00\x00\x05\x00\x00\x00'
[Server-0]
  oid          4   event  1 args b'\x06\x00\x00\x00seat0\x00\x00\x00'
  oid          4   event  0 args b'\x07\x00\x00\x00'
  oid          5   event  0 args b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x15\x00\x00\x00The X.Org Foundation\x00\x00\x00\x00\x05\x00\x00\x0011.0\x00\x00\x00\x00\x00\x00\x00\x00'
  oid          5   event  1 args b'\x01\x00\x00\x00\x00\x04\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00'
  oid          5   event  3 args b'\x01\x00\x00\x00'
  oid          5   event  2 args b''
^C
```

This repository has two homes:
- https://github.com/Consolatis/wl_tee
- https://codeberg.org/Consolatis/wl_tee
